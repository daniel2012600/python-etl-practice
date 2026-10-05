import json
from pathlib import Path
from parser import validate_post
import os
from storage import upsert_post
import mysql.connector
import sys
import hashlib
import time


def main() -> None:
    # 未指定時沿用原任務；測試時可透過環境變數切換。
    job_name = os.environ.get("ETL_JOB_NAME", "posts_100_v1")
    print(f"執行任務：{job_name}")
    # 在讀檔與連線前檢查來源，避免其他檔案誤用既有任務的進度。
    # 此處先檢查檔名；下方讀取任務後，再比對來源內容指紋。
    filename = sys.argv[1] if len(sys.argv) > 1 else "posts_100.json"
    if filename != "posts_100.json":
        raise ValueError(f"任務 {job_name} 只允許來源 posts_100.json")
    source = Path(__file__).with_name(filename)
    # 只讀一次，確保指紋與解析使用的是同一份內容。
    source_bytes = source.read_bytes()
    source_sha256 = hashlib.sha256(source_bytes).hexdigest()
    posts = json.loads(source_bytes.decode("utf-8"))
    # 每次任務嘗試建立新連線；重試次數由外層統一控制。
    connection = mysql.connector.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ["DB_PORT"]),
        database=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        connection_timeout=5,
    )
    try:
        cursor = connection.cursor()
        try:
            # 1. 讀取「已成功提交的來源列號」，不是上次讀到的位置或入庫筆數。
            cursor.execute(
                "SELECT last_row_number, source_sha256 FROM etl_checkpoints WHERE job_name = %s",
                (job_name,),
            )
            checkpoint = cursor.fetchone()
            if checkpoint is None:
                raise RuntimeError("找不到任務的 checkpoint")
            last_row_number, saved_sha256 = checkpoint

            # 必須先確認來源版本，才能使用進度或判定已完成。
            if saved_sha256 is None:
                raise RuntimeError("任務尚未綁定來源指紋，拒絕執行")
            if source_sha256 != saved_sha256:
                raise RuntimeError("來源指紋不一致，拒絕沿用既有進度")

            print("來源指紋驗證通過")


            print(f"已提交的來源進度：{last_row_number}")
            # 入庫完成仍需匯出報告；下方迴圈會略過已提交的來源列。
            if last_row_number == len(posts):
                print("此來源已完成入庫，本次僅重新匯出報告")
            # 計數只涵蓋本次處理的資料，不包含 checkpoint 之前已完成的部分。
            valid_count = 0
            invalid_count = 0
            failed_posts = []

            for index, post in enumerate(posts, start=1):
                # 2. 續跑時略過已提交的列；例如 checkpoint=40，就從第 41 列開始。
                if index <= last_row_number:
                    continue

                reasons = validate_post(post)
                if reasons:
                    invalid_count += 1
                    # 暫存本次失敗資料；下方匯出前會改用資料庫的完整紀錄取代此清單。
                    failed_posts.append({
                        "row_number": index,
                        "raw_data": post,
                        "reasons": reasons,
                    })
                    # 3. 壞資料不進 posts，改存失敗原因，與本批資料共用同一交易。
                    # 複合主鍵讓同一任務、同一來源列重跑時更新紀錄，不重複新增。
                    cursor.execute(
                        """
                        INSERT INTO etl_rejections
                            (job_name, source_row_number, raw_data, reasons)
                        VALUES (%s, %s, %s, %s) AS incoming
                        ON DUPLICATE KEY UPDATE
                            raw_data = incoming.raw_data,
                            reasons = incoming.reasons
                        """,
                        (
                            job_name,
                            index,
                            json.dumps(post, ensure_ascii=False),
                            json.dumps(reasons, ensure_ascii=False),
                        ),
                    )


                else:
                    # 有效資料執行 upsert，但此處尚未提交。
                    upsert_post(cursor, post)
                    valid_count += 1
                # 4. 每到 20 的倍數或最後一列，將資料、失敗紀錄與 checkpoint 一起提交。
                # 判斷放在 if/else 外：即使本列無效，也必須推進已處理的來源進度。
                if index % 20 == 0 or index == len(posts):
                    cursor.execute(
                        """
                        UPDATE etl_checkpoints
                        SET last_row_number = %s
                        WHERE job_name = %s
                        """,
                        (index, job_name),
                    )
                    connection.commit()
                    print(f"已提交至來源第 {index} 列")

            # 5. 分批處理結束後，讀取整個任務的失敗紀錄，包含先前執行已提交的部分。
            # 避免續跑時，只用本次的 failed_posts 覆蓋報告而遺失前面批次的紀錄。
            cursor.execute(
                """
                SELECT source_row_number, raw_data, reasons
                FROM etl_rejections
                WHERE job_name = %s
                ORDER BY source_row_number
                """,
                (job_name,),
            )
            # JSON 欄位查回為文字，用 json.loads 還原，避免匯出時重複編碼。
            failed_posts = [
                {
                    "row_number": row[0],
                    "raw_data": json.loads(row[1]),
                    "reasons": json.loads(row[2]),
                }
                for row in cursor.fetchall()
            ]

            output_dir = Path(__file__).parent / "output"
            output_dir.mkdir(parents=True, exist_ok=True)

            # JSON 是資料庫紀錄的匯出報告，不在 MySQL 交易內。
            # 若寫檔失敗，前面已提交的批次仍保留，rollback 無法撤銷它們。
            output_file = output_dir / "failed_posts.json"

            output_file.write_text(
                json.dumps(failed_posts, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            print(f"本次處理：有效 {valid_count} 筆，無效 {invalid_count} 筆")
            print(f"已匯出任務完整失敗報告：{len(failed_posts)} 筆")
        except Exception:
            # 連線可能已失效；回滾失敗不能蓋掉最初的錯誤。
            try:
                connection.rollback()
            except Exception as rollback_error:
                # 清理階段也可能拋出底層驅動錯誤，不能覆蓋原始例外。
                print(
                    f"回滾未成功，例外類型：{type(rollback_error).__name__}；"
                    "保留原始錯誤"
                )
            else:
                print("已回滾目前未提交的交易；先前已提交的資料與進度仍保留")

            # 重新拋出進入外層 except 時的原始錯誤。
            raise
        finally:
            # 關閉游標是釋放資源，本身不代表回滾。
            cursor.close()
    finally:
        connection.close()


def run_with_retry() -> None:
    # 最多執行 3 次；每次重新連線、驗證來源並讀取已提交進度。
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        try:
            main()
            return  # 任務成功，停止重試。
        except mysql.connector.Error as exc:
            # 目前只處理連不上伺服器，以及執行期間連線中斷。
            if exc.errno not in (2003, 2013):
                raise

            print(f"任務失敗：第 {attempt}/{max_attempts} 次，錯誤碼 {exc.errno}")
            if attempt == max_attempts:
                raise

            print("等待 2 秒後，重新連線並讀取已提交進度")
            time.sleep(2)


if __name__ == "__main__":
    run_with_retry()