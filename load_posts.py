import json
from pathlib import Path
from parser import validate_post
import os
from storage import upsert_post
import mysql.connector
import sys

def main() -> None:
    # 可從命令列指定輸入檔；目前 checkpoint 任務仍寫死為 posts_100_v1，
    # 續跑演練只使用內容與順序固定的 posts_100.json，尚未支援任意來源切換。
    filename = sys.argv[1] if len(sys.argv) > 1 else "posts.json"
    source = Path(__file__).with_name(filename)  
    posts = json.loads(source.read_text(encoding="utf-8"))
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
                "SELECT last_row_number FROM etl_checkpoints WHERE job_name = %s",
                ("posts_100_v1",),
            )
            checkpoint = cursor.fetchone()
            if checkpoint is None:
                raise RuntimeError("找不到任務的 checkpoint")

            last_row_number = checkpoint[0]
            print(f"已提交的來源進度：{last_row_number}")
            # 已完成就跳過；目前也會跳過下方報告匯出，補產生報告的能力尚未加入。
            if last_row_number == len(posts):
                print("此來源已處理完成，跳過本次執行")
                return
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
                            "posts_100_v1",
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
                        (index, "posts_100_v1"),
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
                ("posts_100_v1",),
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

            print(f"已提交：{valid_count} 筆有效資料")
            print(f"驗證未通過：{invalid_count} 筆")
        except Exception:
            # 6. 只回滾目前尚未提交的交易；之前成功提交的批次與進度不會被撤銷。
            connection.rollback()
            print("交易已回滾")
            # 將錯誤傳給呼叫端，避免入庫或報告失敗卻以成功狀態結束。
            raise
        finally:
            # 關閉游標是釋放資源，本身不代表回滾。
            cursor.close()
    finally:
        connection.close()


if __name__ == "__main__":
    main()
