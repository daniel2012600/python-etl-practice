import unittest

from parser import validate_post


class TestValidatePost(unittest.TestCase):
    def test_valid_post(self):
        post = {"id": "p001", "content": "測試內容"}

        self.assertEqual(validate_post(post), [])

    def test_missing_content(self):
        post = {"id": "p003"}

        self.assertEqual(
            validate_post(post),
            ["content 缺漏、型別錯誤或空白"],
        )

    def test_both_fields_invalid(self):
        post = {"id": "", "content": None}

        self.assertEqual(
            validate_post(post),
            [
                "id 缺漏、型別錯誤或空白",
                "content 缺漏、型別錯誤或空白",
            ],
        )

    def test_numeric_content(self):
        post = {"id": "p004", "content": 123}
        self.assertEqual(
            validate_post(post),
            ["content 缺漏、型別錯誤或空白"],
        )


    def test_null_post(self):
        self.assertEqual(
            validate_post(None),
            ["資料必須是物件（dict）"],
        )