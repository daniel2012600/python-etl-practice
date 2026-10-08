import json
from pathlib import Path
from parser import validate_post

def transform_post(post: object, row_number: int) -> dict:
    # 只負責單筆轉換與驗證，不讀寫檔案或資料庫。
    if not isinstance(post, dict):
        raise ValueError(f"來源第 {row_number} 列必須是物件")

    source_id = post.get("id")
    if type(source_id) is not int or source_id <= 0:
        raise ValueError(f"來源第 {row_number} 列 id 必須是正整數")

    transformed = {
        "id": f"jsonplaceholder_{source_id}",
        "content": post.get("body"),
    }

    reasons = validate_post(transformed)
    if reasons:
        raise ValueError(
            f"來源第 {row_number} 列轉換後不合格：{reasons}"
        )

    return transformed

def transform_batch(posts: object) -> list[dict]:
    # 整批驗證與轉換，不讀寫檔案。
    if not isinstance(posts, list):
        raise ValueError("來源根層必須是串列")

    transformed_posts = []
    seen_ids = set()

    for row_number, post in enumerate(posts, start=1):
        transformed = transform_post(post, row_number)
        post_id = transformed["id"]

        if post_id in seen_ids:
            raise ValueError(
                f"來源第 {row_number} 列 ID 重複：{post_id}"
            )

        seen_ids.add(post_id)
        transformed_posts.append(transformed)

    return transformed_posts

def main() -> None:
    # 讀取已保存的來源，不重新呼叫 API。
    source = (
        Path(__file__).parent
        / "output"
        / "raw"
        / "posts_20261006T125500440782Z.json"
    )
    posts = json.loads(source.read_bytes())
    transformed_posts = transform_batch(posts)

    print(f"來源筆數：{len(posts)}")
    print(
        f"整批驗證通過：{len(transformed_posts)} 筆；"
        "欄位合格且 ID 無重複"
    )
    # 全批驗證通過後才輸出；使用原始檔名，方便追溯來源。
    output_dir = Path(__file__).parent / "output" / "transformed"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / source.name

    # x 表示只建立新檔，檔案已存在時拒絕覆寫。
    with output_file.open("x", encoding="utf-8") as file:
        json.dump(transformed_posts, file, ensure_ascii=False, indent=2)

    # 從磁碟讀回，比對內容，確認保存結果。
    saved_posts = json.loads(output_file.read_bytes())
    if saved_posts != transformed_posts:
        raise RuntimeError("存檔內容與轉換結果不一致")

    print(f"已保存：{output_file}")
    print(f"讀回比對通過：{len(saved_posts)} 筆；尚未入庫")


if __name__ == "__main__":
    main()
