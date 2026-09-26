import json
from pathlib import Path
from parser import validate_post
import os
from storage import upsert_post
import mysql.connector


def main() -> None:
    source = Path(__file__).with_name("posts.json")
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
            valid_count = 0
            invalid_count = 0
            failed_posts = []

            for index, post in enumerate(posts, start=1):
                reasons = validate_post(post)

                if reasons:
                    invalid_count += 1
                    failed_posts.append({
                        "row_number": index,
                        "raw_data": post,
                        "reasons": reasons,
                    })
                    continue

                upsert_post(cursor, post)
                valid_count += 1

            output_dir = Path(__file__).parent / "output"
            output_dir.mkdir(parents=True, exist_ok=True)

            output_file = output_dir / "failed_posts.json"
            output_file.write_text(
                json.dumps(failed_posts, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            connection.commit()
            print(f"已提交：{valid_count} 筆有效資料")
            print(f"驗證未通過：{invalid_count} 筆")
        finally:
            cursor.close()
    finally:
        connection.close()


if __name__ == "__main__":
    main()