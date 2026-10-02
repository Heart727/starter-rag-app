import unittest
import asyncio
import tempfile
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from starlette.datastructures import UploadFile

import main
from main import safe_upload_filename


class UploadFilenameTests(unittest.TestCase):
    def test_upload_filename_strips_windows_and_unix_paths(self):
        self.assertEqual(safe_upload_filename("..\\..\\客户资料.txt"), "客户资料.txt")
        self.assertEqual(safe_upload_filename("../../notes.md"), "notes.md")

    def test_upload_filename_rejects_empty_or_unusable_names(self):
        self.assertEqual(safe_upload_filename("../../"), "document")
        self.assertNotEqual(safe_upload_filename("nul.txt"), "nul.txt")

    def test_upload_stores_path_traversal_names_inside_upload_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir, patch.object(main, "UPLOAD_DIR", temp_dir):
            result = asyncio.run(main.upload_files([
                UploadFile(filename="..\\..\\private.txt", file=BytesIO(b"demo")),
            ]))

            saved = list(Path(temp_dir).iterdir())
            self.assertEqual(result["files"], ["private.txt"])
            self.assertEqual(len(saved), 1)
            self.assertEqual(saved[0].parent, Path(temp_dir))
            self.assertTrue(saved[0].read_bytes() == b"demo")

    def test_upload_rejects_oversize_before_saving_any_file(self):
        with tempfile.TemporaryDirectory() as temp_dir, patch.object(main, "UPLOAD_DIR", temp_dir):
            with self.assertRaises(HTTPException) as raised:
                asyncio.run(main.upload_files([
                    UploadFile(filename="large.txt", file=BytesIO(b"x" * (main.MAX_FILE_BYTES + 1))),
                ]))

            self.assertEqual(raised.exception.status_code, 413)
            self.assertEqual(list(Path(temp_dir).iterdir()), [])

    def test_upload_rejects_empty_files_with_a_clear_error(self):
        with tempfile.TemporaryDirectory() as temp_dir, patch.object(main, "UPLOAD_DIR", temp_dir):
            with self.assertRaises(HTTPException) as raised:
                asyncio.run(main.upload_files([
                    UploadFile(filename="empty.txt", file=BytesIO(b"")),
                ]))

            self.assertEqual(raised.exception.status_code, 400)
            self.assertIn("文件内容为空", raised.exception.detail)
            self.assertEqual(list(Path(temp_dir).iterdir()), [])
