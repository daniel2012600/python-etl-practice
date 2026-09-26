import os

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
            cursor.execute(
                "SELECT id, note FROM persistence_check ORDER BY id"
            )
            for row in cursor.fetchall():
                print(row)
        finally:
            cursor.close()
    finally:
        connection.close()


if __name__ == "__main__":
    main()