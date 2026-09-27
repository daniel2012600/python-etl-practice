import json
from pathlib import Path

posts = [
    {"id": f"batch_{i:03d}", "content": f"批次測試第 {i} 筆"}
    for i in range(1, 101)
]

posts.extend([
    {"id": "bad_001"},
    {"id": "", "content": "ID 空白"},
    {"id": "bad_003", "content": ""},
    {"id": "bad_004", "content": 123},
    None,
])

target = Path(__file__).with_name("posts_100.json")
target.write_text(
    json.dumps(posts, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

print(f"已產生：{len(posts)} 筆")