"""
Test chunked upload functionality
"""
# ruff: noqa: E402

import io
import os
import shutil
import sys
import tempfile
import uuid
from os.path import abspath, dirname
from typing import TypedDict, Optional

import pytest

# Add backend directory to the path so imports work correctly
backend_dir = dirname(dirname(abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Now we can import from utils
from utils.exceptions import (
    NotFoundException,
    ValidationException,
)
from utils.file_processor import FileProcessor


class UploadStatus(TypedDict):
    upload_id: str
    filename: str
    total_chunks: int
    file_size: int
    status: str
    received_chunks: int


# Create a test file of a specific size
def create_test_file(size_bytes=1024 * 1024):
    """Create a test file of a specific size for testing chunked uploads"""
    test_file = tempfile.NamedTemporaryFile(delete=False)

    # Create random data
    with open(test_file.name, "wb") as f:
        f.write(os.urandom(size_bytes))

    return test_file.name


def split_file_into_chunks(file_path, chunk_size=1024 * 256):
    """Split a file into chunks for testing"""
    chunks = []
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            chunks.append(chunk)
    return chunks


class TestFileProcessorChunkedUpload:
    """Test cases for the FileProcessor chunked upload functionality"""

    def setup_method(self):
        """Setup for each test case"""
        # Create a temp directory for uploads
        self.test_dir = tempfile.mkdtemp()

        # Create a test file
        self.test_file = create_test_file(1024 * 1024 * 2)  # 2MB file
        self.file_size = os.path.getsize(self.test_file)
        self.chunks = split_file_into_chunks(self.test_file, 1024 * 512)  # 512KB chunks

    def teardown_method(self):
        """Cleanup after each test case"""
        # Clean up temp files
        if os.path.exists(self.test_file):
            os.unlink(self.test_file)

        # Clean up temp directory
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_chunked_upload_flow(self):
        """Test the complete chunked upload flow"""
        # 1. Initialize the chunked upload
        upload_id = str(uuid.uuid4())
        filename = "test_file.txt"
        total_chunks = len(self.chunks)

        upload_info = FileProcessor.init_chunked_upload(
            upload_id=upload_id,
            filename=filename,
            total_chunks=total_chunks,
            file_size=self.file_size,
            mime_type="text/plain",
            directory=self.test_dir,
        )

        # Verify the upload info
        assert upload_info["upload_id"] == upload_id
        assert upload_info["filename"] == filename
        assert upload_info["total_chunks"] == total_chunks
        assert upload_info["file_size"] == self.file_size
        assert upload_info["status"] == "initialized"
        assert upload_info["received_chunks"] == 0

        # Verify that the chunks directory was created
        chunks_dir = upload_info["chunks_dir"]
        assert os.path.exists(chunks_dir)

        # 2. Upload each chunk
        for i, chunk_data in enumerate(self.chunks):
            # Create a file-like object for the chunk
            chunk_io = io.BytesIO(chunk_data)

            # Save the chunk
            chunk_info = FileProcessor.save_chunk(
                upload_id=upload_id, chunk_index=i, chunk_data=chunk_io
            )

            # Verify that the chunk was saved
            chunk_path = os.path.join(chunks_dir, f"chunk_{i}")
            assert os.path.exists(chunk_path)

            # Verify the updated info
            assert chunk_info["received_chunks"] == i + 1

            # Check status
            if i + 1 == total_chunks:
                assert chunk_info["status"] == "ready_to_combine"
            else:
                assert chunk_info["status"] == "in_progress"

        # 3. Complete the upload
        result = FileProcessor.complete_chunked_upload(
            upload_id=upload_id, target_directory=self.test_dir
        )

        # Verify the result
        assert "file_path" in result
        assert "file_info" in result
        assert result["upload_id"] == upload_id
        assert result["original_filename"] == filename
        assert result["mime_type"] == "text/plain"
        assert result["size_bytes"] == self.file_size

        # Verify the file was created
        assert os.path.exists(result["file_path"])
        assert os.path.getsize(result["file_path"]) == self.file_size

        # Check file contents match the original
        with open(self.test_file, "rb") as f1, open(result["file_path"], "rb") as f2:
            assert f1.read() == f2.read()

    def test_get_upload_status(self):
        """Test getting the status of a chunked upload"""
        # Initialize upload
        upload_id = str(uuid.uuid4())
        filename = "test_file.txt"
        total_chunks = len(self.chunks)

        FileProcessor.init_chunked_upload(
            upload_id=upload_id,
            filename=filename,
            total_chunks=total_chunks,
            file_size=self.file_size,
            mime_type="text/plain",
            directory=self.test_dir,
        )

        # Get status
        status: Optional[UploadStatus] = FileProcessor.get_chunked_upload_status(upload_id)
        assert status is not None

        # Verify status
        assert status["upload_id"] == upload_id
        assert status["filename"] == filename
        assert status["total_chunks"] == total_chunks
        assert status["file_size"] == self.file_size
        assert status["status"] == "initialized"
        assert status["received_chunks"] == 0

    def test_cleanup_chunked_upload(self):
        """Test cleaning up a chunked upload"""
        # Initialize upload
        upload_id = str(uuid.uuid4())
        filename = "test_file.txt"
        total_chunks = len(self.chunks)

        upload_info = FileProcessor.init_chunked_upload(
            upload_id=upload_id,
            filename=filename,
            total_chunks=total_chunks,
            file_size=self.file_size,
            mime_type="text/plain",
            directory=self.test_dir,
        )

        chunks_dir = upload_info["chunks_dir"]
        assert os.path.exists(chunks_dir)

        # Clean up
        result = FileProcessor.cleanup_chunked_upload(upload_id)

        # Verify clean up was successful
        assert result is True
        assert not os.path.exists(chunks_dir)

        # Verify status is removed
        assert FileProcessor.get_chunked_upload_status(upload_id) is None

    def test_error_handling(self):
        """Test error handling in chunked uploads"""
        # Test non-existent upload
        with pytest.raises(NotFoundException):
            FileProcessor.save_chunk(
                upload_id="nonexistent", chunk_index=0, chunk_data=io.BytesIO(b"test")
            )

        # Test invalid chunk index
        upload_id = str(uuid.uuid4())
        FileProcessor.init_chunked_upload(
            upload_id=upload_id,
            filename="test.txt",
            total_chunks=3,
            file_size=1024,
            mime_type="text/plain",
            directory=self.test_dir,
        )

        with pytest.raises(ValidationException):
            FileProcessor.save_chunk(
                upload_id=upload_id,
                chunk_index=10,  # Out of range
                chunk_data=io.BytesIO(b"test"),
            )

        # Test completing upload before all chunks received
        with pytest.raises(ValidationException):
            FileProcessor.complete_chunked_upload(
                upload_id=upload_id, target_directory=self.test_dir
            )


# Integration tests with FastAPI endpoints could be added here
# These would use TestClient to call the actual API endpoints
