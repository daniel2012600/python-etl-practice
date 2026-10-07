from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen


def main() -> None:
    url = "https://jsonplaceholder.typicode.com/posts"

    # 設定網路操作逾時，避免連線一直等待。
    with urlopen(url, timeout=30) as response:
        status = response.status
        raw_bytes = response.read()

    # 每次使用不同的 UTC 時間檔名，保留各次取得的內容。
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output_dir = Path(__file__).parent / "output" / "raw"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"posts_{timestamp}.json"

    # 直接保存回應本文的位元組，不先解析再重新組成 JSON。
    # xb 表示建立新檔；若檔案已存在就報錯，避免覆蓋。
    with output_file.open("xb") as file:
        file.write(raw_bytes)

    print(f"HTTP 狀態碼：{status}")
    print(f"已保存：{output_file}")
    print(f"回應大小：{len(raw_bytes)} bytes（位元組）")


if __name__ == "__main__":
    main()