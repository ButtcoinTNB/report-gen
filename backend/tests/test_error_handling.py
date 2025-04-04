"""
Test error handling functionality
"""

# ruff: noqa: E402

import os
import shutil
import sys
import tempfile
import unittest
import uuid
from os.path import abspath, dirname
from typing import Dict, Any, TypedDict

# Add backend directory to the path so imports work correctly
backend_dir = dirname(dirname(abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from utils.exceptions import (
    FileProcessingException,
    NotFoundException,
    ValidationException,
)
from utils.file_processor import FileProcessor


class ExceptionDetail(TypedDict):
    code: str
    message: str
    details: Dict[str, Any]


class TestFileProcessorErrorHandling(unittest.TestCase):
    """Test the enhanced error handling in the FileProcessor class"""

    def setUp(self):
        """Set up temporary test directory"""
        self.test_dir = tempfile.mkdtemp()
        self.upload_id = str(uuid.uuid4())
        self.test_file_path = os.path.join(self.test_dir, "test_file.txt")

        # Create a test file
        with open(self.test_file_path, "w") as f:
            f.write("Test content")

    def tearDown(self):
        """Clean up after tests"""
        shutil.rmtree(self.test_dir)

        # Clean up any uploads that might have been created
        if (
            hasattr(self, "upload_id")
            and self.upload_id in FileProcessor._chunked_uploads
        ):
            FileProcessor.cleanup_chunked_upload(self.upload_id)

    def test_save_chunk_not_found_exception(self):
        """Test that save_chunk raises NotFoundException for invalid upload_id"""
        invalid_upload_id = "invalid-id"

        with self.assertRaises(NotFoundException) as context:
            with open(self.test_file_path, "rb") as f:
                FileProcessor.save_chunk(invalid_upload_id, 0, f)

        # Verify exception details
        exception_detail: ExceptionDetail = context.exception.detail
        self.assertIn("not found", str(exception_detail["message"]))
        self.assertEqual(exception_detail["code"], "NOT_FOUND")
        self.assertEqual(exception_detail["details"]["upload_id"], invalid_upload_id)

    def test_save_chunk_validation_exception(self):
        """Test that save_chunk raises ValidationException for invalid chunk index"""
        # Initialize a chunked upload
        FileProcessor.init_chunked_upload(
            upload_id=self.upload_id,
            filename="test.txt",
            total_chunks=2,
            file_size=100,
            mime_type="text/plain",
            directory=self.test_dir,
        )

        # Try to save a chunk with an out-of-range index
        with self.assertRaises(ValidationException) as context:
            with open(self.test_file_path, "rb") as f:
                FileProcessor.save_chunk(self.upload_id, 5, f)

        # Verify exception details
        self.assertIn("out of range", str(context.exception.detail["message"]))
        self.assertEqual(context.exception.detail["code"], "VALIDATION_ERROR")
        self.assertEqual(context.exception.detail["details"]["chunk_index"], 5)
        self.assertEqual(context.exception.detail["details"]["total_chunks"], 2)

    def test_complete_upload_validation_exception(self):
        """Test that complete_chunked_upload raises ValidationException when not all chunks received"""
        # Initialize a chunked upload
        FileProcessor.init_chunked_upload(
            upload_id=self.upload_id,
            filename="test.txt",
            total_chunks=2,
            file_size=100,
            mime_type="text/plain",
            directory=self.test_dir,
        )

        # Try to complete the upload without uploading all chunks
        with self.assertRaises(ValidationException) as context:
            FileProcessor.complete_chunked_upload(
                upload_id=self.upload_id, target_directory=self.test_dir
            )

        # Verify exception details
        self.assertIn("Upload not complete", str(context.exception.detail["message"]))
        self.assertEqual(context.exception.detail["code"], "VALIDATION_ERROR")
        self.assertEqual(
            context.exception.detail["details"]["upload_id"], self.upload_id
        )
        self.assertEqual(context.exception.detail["details"]["received_chunks"], 0)
        self.assertEqual(context.exception.detail["details"]["total_chunks"], 2)

    def test_file_processing_exception_when_directory_not_writable(self):
        """Test that FileProcessingException is raised when target directory is not writable"""
        # Create a directory with no write permissions
        readonly_dir = os.path.join(self.test_dir, "readonly")
        os.makedirs(readonly_dir)
        try:
            # Make directory read-only (this works on Unix-like systems)
            os.chmod(readonly_dir, 0o555)

            # Initialize chunked upload
            FileProcessor.init_chunked_upload(
                upload_id=self.upload_id,
                filename="test.txt",
                total_chunks=1,
                file_size=100,
                mime_type="text/plain",
                directory=self.test_dir,
            )

            # Upload a chunk
            with open(self.test_file_path, "rb") as f:
                FileProcessor.save_chunk(self.upload_id, 0, f)

            # Try to complete the upload with a read-only target directory
            with self.assertRaises(FileProcessingException) as context:
                FileProcessor.complete_chunked_upload(
                    upload_id=self.upload_id, target_directory=readonly_dir
                )

            # Verify exception details
            self.assertIn(
                "Failed to combine chunks", str(context.exception.detail["message"])
            )
            self.assertEqual(context.exception.detail["code"], "file_processing_error")
            self.assertEqual(
                context.exception.detail["details"]["upload_id"], self.upload_id
            )

        finally:
            # Restore permissions to allow cleanup
            os.chmod(readonly_dir, 0o755)


if __name__ == "__main__":
    unittest.main()
