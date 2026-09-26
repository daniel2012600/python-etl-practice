import os
from storage import upsert_post
import mysql.connector


def main() -> None:
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
            post = {"id": "p001", "content": "內容已更新"}
            upsert_post(cursor, post)
            connection.commit()

            print("已提交：1 筆輸入資料")
        finally:
            cursor.close()
    finally:
        connection.close()


if __name__ == "__main__":
    main()