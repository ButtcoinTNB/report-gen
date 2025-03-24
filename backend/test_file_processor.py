import io
import os
import shutil
import tempfile
import uuid

from utils.file_processor import FileProcessor


def create_test_file(size_bytes=1024):
    """Create a test file of a specific size"""
    test_file = tempfile.NamedTemporaryFile(delete=False)

    # Create random data
    with open(test_file.name, "wb") as f:
        f.write(os.urandom(size_bytes))

    return test_file.name


def run_test():
    """Run the test for FileProcessor chunked upload"""
    print("Testing FileProcessor chunked upload functionality...")

    # Create a temp directory for uploads
    test_dir = tempfile.mkdtemp()
    print(f"Created test directory: {test_dir}")

    # Create a test file
    test_file = create_test_file(1024 * 1024)  # 1MB file
    file_size = os.path.getsize(test_file)
    print(f"Created test file: {test_file} ({file_size} bytes)")

    # Read file content for later comparison
    with open(test_file, "rb") as f:
        original_content = f.read()

    # Split into chunks
    chunk_size = 256 * 1024  # 256KB chunks
    chunks = []
    with open(test_file, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            chunks.append(chunk)

    print(f"Split file into {len(chunks)} chunks")

    try:
        # 1. Initialize chunked upload
        upload_id = str(uuid.uuid4())
        filename = "test_file.txt"
        total_chunks = len(chunks)

        print(f"Initializing chunked upload with ID: {upload_id}")
        upload_info = FileProcessor.init_chunked_upload(
            upload_id=upload_id,
            filename=filename,
            total_chunks=total_chunks,
            file_size=file_size,
            mime_type="text/plain",
            directory=test_dir,
        )

        print(f"Chunked upload initialized: {upload_info['status']}")
        chunks_dir = upload_info["chunks_dir"]
        print(f"Chunks directory: {chunks_dir}")

        # 2. Upload chunks
        for i, chunk_data in enumerate(chunks):
            print(f"Uploading chunk {i+1}/{total_chunks}")
            chunk_io = io.BytesIO(chunk_data)

            chunk_info = FileProcessor.save_chunk(
                upload_id=upload_id, chunk_index=i, chunk_data=chunk_io
            )

            print(f"  - Status: {chunk_info['status']}")
            print(
                f"  - Received chunks: {chunk_info['received_chunks']}/{chunk_info['total_chunks']}"
            )

        # 3. Complete the upload
        print("Completing chunked upload...")
        result = FileProcessor.complete_chunked_upload(
            upload_id=upload_id, target_directory=test_dir
        )

        final_path = result["file_path"]
        print(f"Upload completed. Final file: {final_path}")

        # 4. Verify file content
        with open(final_path, "rb") as f:
            final_content = f.read()

        if final_content == original_content:
            print("TEST PASSED: Final file content matches original")
        else:
            print("TEST FAILED: Final file content does not match original")
            print(
                f"Original size: {len(original_content)}, Final size: {len(final_content)}"
            )

        # 5. Test status
        status = FileProcessor.get_chunked_upload_status(upload_id)
        print(f"Upload status: {status['status']}")

        # 6. Cleanup
        print("Cleaning up...")
        FileProcessor.cleanup_chunked_upload(upload_id)
        print("Cleanup complete")

        print("All tests completed successfully")

    except Exception as e:
        print(f"ERROR: {str(e)}")

    finally:
        # Cleanup
        print("Final cleanup...")
        if os.path.exists(test_file):
            os.unlink(test_file)
            print(f"Removed test file: {test_file}")

        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
            print(f"Removed test directory: {test_dir}")


if __name__ == "__main__":
    run_test()
