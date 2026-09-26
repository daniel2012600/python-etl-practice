def upsert_post(cursor, post: dict) -> None:
    sql = """
        INSERT INTO posts (id, content)
        VALUES (%s, %s) AS incoming
        ON DUPLICATE KEY UPDATE
            content = incoming.content
    """
    cursor.execute(sql, (post["id"], post["content"]))