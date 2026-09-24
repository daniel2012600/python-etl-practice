import json
from pathlib import Path

source = Path(__file__).with_name("posts.json")
posts = json.loads(source.read_text(encoding="utf-8"))

success_count = 0
failure_count = 0

for index, post in enumerate(posts, start=1):
    post_id = post.get("id")
    content = post.get("content")
    is_valid_id = isinstance(post_id, str) and post_id.strip() != ""
    is_valid_content = isinstance(content, str) and content.strip() != ""
    if is_valid_id and  is_valid_content:
        success_count += 1
    else:
        reasons = []

        if not is_valid_id:
            reasons.append("id 缺漏、型別錯誤或空白")

        if not is_valid_content:
            reasons.append("content 缺漏、型別錯誤或空白")

        print(f"第 {index} 筆失敗，id={post_id!r}：{'；'.join(reasons)}")
        failure_count += 1

        
print(f"成功：{success_count}")
print(f"失敗：{failure_count}")