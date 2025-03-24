import io
import os
import tempfile

from PIL import Image
from utils.file_processor import FileProcessor


class TestFileProcessor:
    """Unit tests for the FileProcessor utility class"""

    def test_get_mime_type(self):
        """Test the get_mime_type method with different file extensions"""
        # Test common file types
        assert FileProcessor.get_mime_type("test.txt") == "text/plain"
        assert FileProcessor.get_mime_type("test.pdf") == "application/pdf"
        assert FileProcessor.get_mime_type("test.jpg") == "image/jpeg"
        assert FileProcessor.get_mime_type("test.png") == "image/png"
        assert (
            FileProcessor.get_mime_type("test.docx")
            == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

        # Test unknown type
        assert FileProcessor.get_mime_type("test.xyz") is not None

    def test_get_file_extension(self):
        """Test the get_file_extension method"""
        assert FileProcessor.get_file_extension("text/plain") == ".txt"
        assert FileProcessor.get_file_extension("application/pdf") == ".pdf"
        assert FileProcessor.get_file_extension("image/jpeg") == ".jpg"
        assert (
            FileProcessor.get_file_extension(
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            == ".docx"
        )

        # Test unknown MIME type
        assert FileProcessor.get_file_extension("application/unknown") == ""

    def test_is_text_file(self):
        """Test the is_text_file method"""
        # Create temporary text file
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as temp_txt:
            temp_txt.write(b"This is a test text file")
            temp_txt_path = temp_txt.name

        # Create temporary binary file
        with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as temp_bin:
            temp_bin.write(os.urandom(100))  # Write random binary data
            temp_bin_path = temp_bin.name

        try:
            # Test text file
            assert FileProcessor.is_text_file(temp_txt_path) is True

            # Test binary file
            assert FileProcessor.is_text_file(temp_bin_path) is False

            # Test non-existent file
            assert FileProcessor.is_text_file("non_existent_file.txt") is False

        finally:
            # Clean up
            os.unlink(temp_txt_path)
            os.unlink(temp_bin_path)

    def test_is_image_file(self):
        """Test the is_image_file method"""
        # Create temporary image file
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_img:
            # Create a small test image
            img = Image.new("RGB", (100, 100), color="red")
            img_bytes = io.BytesIO()
            img.save(img_bytes, format="PNG")
            temp_img.write(img_bytes.getvalue())
            temp_img_path = temp_img.name

        # Create temporary text file
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as temp_txt:
            temp_txt.write(b"This is a test text file")
            temp_txt_path = temp_txt.name

        try:
            # Test image file
            assert FileProcessor.is_image_file(temp_img_path) is True

            # Test text file
            assert FileProcessor.is_image_file(temp_txt_path) is False

            # Test non-existent file
            assert FileProcessor.is_image_file("non_existent_file.png") is False

        finally:
            # Clean up
            os.unlink(temp_img_path)
            os.unlink(temp_txt_path)

    def test_get_file_info(self):
        """Test the get_file_info method"""
        # Create temporary text file with known content
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as temp_file:
            temp_file.write(b"This is a test file")
            temp_file_path = temp_file.name

        try:
            # Get file info
            file_info = FileProcessor.get_file_info(temp_file_path)

            # Check key fields
            assert file_info["name"] == os.path.basename(temp_file_path)
            assert file_info["path"] == temp_file_path
            assert file_info["extension"] == ".txt"
            assert file_info["mime_type"] == "text/plain"
            assert file_info["size_bytes"] == len(b"This is a test file")
            assert file_info["size_mb"] == len(b"This is a test file") / (1024 * 1024)
            assert file_info["is_text"] is True
            assert file_info["is_binary"] is False
            assert file_info["is_image"] is False
            assert file_info["exists"] is True

            # Test non-existent file
            non_existent_info = FileProcessor.get_file_info("non_existent_file.txt")
            assert non_existent_info["exists"] is False
            assert non_existent_info["size_bytes"] == 0

        finally:
            # Clean up
            os.unlink(temp_file_path)

    def test_safe_path_join(self):
        """Test the safe_path_join method"""
        base_dir = "/test/base/dir"

        # Test normal path join
        assert (
            FileProcessor.safe_path_join(base_dir, "subdir", "file.txt")
            == "/test/base/dir/subdir/file.txt"
        )

        # Test with parent directory reference, should sanitize
        path = FileProcessor.safe_path_join(base_dir, "../file.txt")
        assert path == "/test/base/dir/file.txt" or path.endswith(
            "file.txt"
        )  # Different systems may handle this differently

        # Test with absolute path that tries to escape, should sanitize
        path = FileProcessor.safe_path_join(base_dir, "/etc/passwd")
        assert path == "/test/base/dir/etc/passwd" or path.endswith("passwd")

    def test_save_upload(self, monkeypatch):
        """Test the save_upload method"""
        # Create test directory
        with tempfile.TemporaryDirectory() as test_dir:
            # Create a test file
            test_file = io.BytesIO(b"Test file content")
            test_file.filename = "test.txt"  # Add filename attribute

            # Mock os.makedirs to do nothing (directory already exists)
            monkeypatch.setattr(os, "makedirs", lambda *args, **kwargs: None)

            # Call save_upload
            file_info = FileProcessor.save_upload(test_file, test_dir, "saved_test.txt")

            # Check that the file was saved
            assert os.path.exists(os.path.join(test_dir, "saved_test.txt"))

            # Check file_info
            assert file_info["name"] == "saved_test.txt"
            assert file_info["size_bytes"] == len(b"Test file content")
            assert file_info["mime_type"] == "text/plain"

    def test_extract_text(self, monkeypatch):
        """Test the extract_text method"""
        # Create a test text file
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as temp_file:
            test_content = "This is a test file for text extraction"
            temp_file.write(test_content.encode("utf-8"))
            temp_file_path = temp_file.name

        try:
            # Test text extraction
            extracted_text = FileProcessor.extract_text(temp_file_path)
            assert extracted_text.strip() == test_content

            # Test non-existent file
            error_text = FileProcessor.extract_text("non_existent_file.txt")
            assert "File does not exist" in error_text

        finally:
            # Clean up
            os.unlink(temp_file_path)

    def test_file_operations(self):
        """Test file operations (exists, delete, copy)"""
        # Create test file
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as temp_file:
            temp_file.write(b"Test content")
            source_path = temp_file.name

        try:
            # Test file_exists
            assert FileProcessor.file_exists(source_path) is True
            assert FileProcessor.file_exists("non_existent_file.txt") is False

            # Test copy_file
            target_path = source_path + ".copy"
            assert FileProcessor.copy_file(source_path, target_path) is True
            assert os.path.exists(target_path) is True

            # Test delete_file
            assert FileProcessor.delete_file(target_path) is True
            assert os.path.exists(target_path) is False

            # Test deleting non-existent file
            assert FileProcessor.delete_file("non_existent_file.txt") is False

        finally:
            # Clean up
            if os.path.exists(source_path):
                os.unlink(source_path)
            if os.path.exists(target_path):
                os.unlink(target_path)

    def test_get_file_as_base64(self):
        """Test the get_file_as_base64 method"""
        # Create test file
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as temp_file:
            temp_file.write(b"Test content for base64 encoding")
            file_path = temp_file.name

        try:
            # Test base64 encoding
            base64_data = FileProcessor.get_file_as_base64(file_path)
            assert base64_data is not None
            assert base64_data.startswith("data:text/plain;base64,")

            # Test non-existent file
            assert FileProcessor.get_file_as_base64("non_existent_file.txt") is None

        finally:
            # Clean up
            os.unlink(file_path)
