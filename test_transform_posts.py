import unittest
import json
from pathlib import Path
from transform_posts import transform_post, transform_batch

class TestTransformPost(unittest.TestCase):
    def test_valid_post(self):
        result = transform_post({"id": 1, "body": "測試內容"}, 1)

        self.assertEqual(
            result,
            {"id": "jsonplaceholder_1", "content": "測試內容"},
        )

    def test_string_id_rejected(self):
        # 字串 "1" 不符合來源必須提供正整數 ID 的規則。
        with self.assertRaisesRegex(ValueError, "來源第 2 列"):
            transform_post({"id": "1", "body": "測試內容"}, 2)

    def test_missing_body_rejected(self):
        # 缺少 body，不應產生可以入庫的資料。
        with self.assertRaisesRegex(ValueError, "來源第 3 列"):
            transform_post({"id": 3}, 3)

class TestTransformBatch(unittest.TestCase):
    def test_valid_batch(self):
        posts = [
            {"id": 1, "body": "甲"},
            {"id": 2, "body": "乙"},
        ]

        result = transform_batch(posts)

        self.assertEqual(
            result,
            [
                {"id": "jsonplaceholder_1", "content": "甲"},
                {"id": "jsonplaceholder_2", "content": "乙"},
            ],
        )

    def test_duplicate_id_rejected(self):
        # 同 ID、不同內容：避免後一筆入庫時覆蓋前一筆。
        posts = [
            {"id": 1, "body": "原本內容"},
            {"id": 1, "body": "另一份內容"},
        ]

        with self.assertRaisesRegex(
            ValueError,
            "來源第 2 列 ID 重複：jsonplaceholder_1",
        ):
            transform_batch(posts)

class TestSavedSnapshot(unittest.TestCase):
    def test_saved_source_matches_previous_output(self):
        # 固定樣本隨 Git 保存，不依賴下載結果或本機 output。
        fixture_dir = Path(__file__).parent / "tests" / "fixtures"

        posts = json.loads(
            (fixture_dir / "posts_raw.json").read_bytes()
        )
        expected = json.loads(
            (fixture_dir / "posts_expected.json").read_bytes()
        )

        result = transform_batch(posts)

        self.assertEqual(len(result), 100)
        self.assertEqual(result, expected)