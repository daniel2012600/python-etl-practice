##  入職前的練習，具體目標

1.盤點 Python、Git、Docker 環境與可沿用程式 : 能在獨立環境執行

2.Python 基礎融入小專案：型別註解、模組、例外、logging : 看得懂並能自己修改

3.單一來源 → 保存原始回應 → 解析驗證 → MySQL : 固定 100 筆跑通

4.unittest、冪等、checkpoint、有限重試 : 重跑 3 次不重複；中斷可恢復；壞資料可追蹤

5.Docker、非同步抓取與 Git 協作 : 能重建環境、限制並發、完成修改與回復


## 執行前提

需啟動 Docker Desktop，並在專案根目錄準備未納入 Git 的 `.env`，設定 `MYSQL_PASSWORD` 與 `MYSQL_ROOT_PASSWORD`。新環境需先執行 `docker compose build parser` 建立本機映像；建置映像不會建立 MySQL 資料表或補回 `output/` 的來源檔案。

## 資料庫初始化

全新 MySQL 資料卷不會自動建立 ETL 資料表。需執行 `checkpoint_schema.sql`，建立 `posts`、`etl_checkpoints`、`etl_rejections`。腳本建立的 `posts_100_v1` 起始進度為 0，但來源指紋為 NULL。

在要執行 ETL 的專案目錄，以 PowerShell 計算該份來源檔實際位元組的指紋：

```powershell
(Get-FileHash -LiteralPath .\posts_100.json -Algorithm SHA256).Hash.ToLowerInvariant()
```

確認 `posts_100_v1` 的 `last_row_number = 0` 且 `source_sha256 IS NULL` 後，才將該值綁定到任務；不要拿另一個工作目錄的指紋代用。
在已確認是全新隔離資料庫時，登入 MySQL，將下列 `@sha` 的值換成上一步取得的 64 字元指紋：

```sql
SET @sha = '<填入剛計算的64字元指紋>';
UPDATE etl_checkpoints
SET source_sha256 = @sha
WHERE job_name = 'posts_100_v1'
  AND last_row_number = 0
  AND source_sha256 IS NULL
  AND CHAR_LENGTH(@sha) = 64;
```

預期更新 1 筆；若為 0 筆，先查原因，不要移除 `WHERE` 條件或重設進度。


## 目前可驗收的流程

在專案目錄執行 `docker compose run --rm parser python -m unittest -v test_parser test_transform_posts`，可執行 11 個不依賴 API 或資料庫的單元測試。外部 API 原始檔、轉換檔及 MySQL 資料不隨 Git 保存；目前不能把全新 checkout 視為可直接完成入庫的環境。