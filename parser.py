import json
from pathlib import Path



# 輸入post
def validate_post(post: object) -> list[str]:
    # 用一個容器來接原因
    reasons = []
    # 判斷資料必須是物件
    if  isinstance(post, dict):
        # 提出post id , content
        post_id = post.get("id")
        content = post.get("content")
        # 判斷id, content 有沒有問題 有效回傳空清單，無效回傳原因清單
        if not (isinstance(post_id, str) and post_id.strip() != ""):
            reasons.append("id 缺漏、型別錯誤或空白")

        if not (isinstance(content, str) and content.strip() != ""):
            reasons.append("content 缺漏、型別錯誤或空白")
    else:
        reasons.append("資料必須是物件（dict）")
    return reasons


def main() -> None:
    source = Path(__file__).with_name("posts.json")
    posts = json.loads(source.read_text(encoding="utf-8"))

    success_count = 0
    failure_count = 0
    failed_posts = []
    for index, post in enumerate(posts, start=1):
        reasons = validate_post(post)
        if not reasons:
            success_count += 1
        else:
            post_id = post.get("id") if isinstance(post, dict) else None
            print(f"第 {index} 筆失敗，id={post_id!r}：{'；'.join(reasons)}")
            failure_count += 1
            failed_posts.append({
                "row_number": index,
                "raw_data": post,
                "reasons": reasons,
            })

            output_dir = Path(__file__).parent / "output"
            output_dir.mkdir(parents=True, exist_ok=True)

            output_file = output_dir / "failed_posts.json"
            output_file.write_text(
                json.dumps(failed_posts, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )


    print(f"成功：{success_count}")
    print(f"失敗：{failure_count}")
    print(f"失敗資料已保存：{output_file}")
if __name__ == "__main__":
    main()