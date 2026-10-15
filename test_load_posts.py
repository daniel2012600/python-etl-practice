import hashlib
import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import load_posts


class TestCheckpointBounds(unittest.TestCase):
    def test_rejects_checkpoint_beyond_source(self):
        raw = (Path(load_posts.__file__).parent / "posts_100.json").read_bytes()
        row_count = len(json.loads(raw.decode("utf-8")))
        connection = MagicMock()
        connection.cursor.return_value.fetchone.return_value = (
            row_count + 1,
            hashlib.sha256(raw).hexdigest(),
        )
        env = {
            "ETL_JOB_NAME": "posts_100_v1",
            "DB_HOST": "db",
            "DB_PORT": "3306",
            "DB_NAME": "etl_practice",
            "DB_USER": "etl",
            "DB_PASSWORD": "unused",
        }

        with (
            patch.dict(load_posts.os.environ, env),
            patch.object(load_posts.sys, "argv", ["load_posts.py"]),
            patch.object(load_posts.mysql.connector, "connect", return_value=connection),
        ):
            with self.assertRaisesRegex(RuntimeError, "超過來源筆數"):
                load_posts.main()

        connection.commit.assert_not_called()