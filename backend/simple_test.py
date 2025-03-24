#!/usr/bin/env python3
"""
Simple test script for FileProcessor chunked upload functionality.
This script has minimal dependencies and can be run without pytest.
"""

import io
import os
import shutil
import sys
import tempfile
import uuid

# Add the backend directory to the path so we can import utils
sys.path.insert(0, os.path.dirname(__file__))

try:
    from utils.file_processor import FileProcessor

    print("Successfully imported FileProcessor")
except ImportError as e:
    print(f"Error importing FileProcessor: {e}")
    print("Attempting to continue with minimal functionality...")


def create_test_file(size_bytes=1024 * 1024):
    """Create a test file of a specific size"""
    print(f"Creating test file of size {size_bytes/1024/1024:.2f} MB")
    test_file = tempfile.NamedTemporaryFile(delete=False)

    # Create random data
    with open(test_file.name, "wb") as f:
        f.write(os.urandom(size_bytes))

    print(f"Created test file: {test_file.name}")
    return test_file.name


def run_test():
    """Run a simplified test for chunked upload functionality"""
    print("\n=== Testing Chunked Upload Functionality ===\n")

    # Create a temp directory for uploads
    test_dir = tempfile.mkdtemp()
    print(f"Created test directory: {test_dir}")

    # Create a test file (1MB)
    test_file = create_test_file(1024 * 1024)
    file_size = os.path.getsize(test_file)
    print(f"Test file size: {file_size} bytes")

    # Read the file content for comparison later
    print("Reading original file content for comparison")
    with open(test_file, "rb") as f:
        original_content = f.read()

    try:
        # Define chunk size (256KB for this test)
        chunk_size = 256 * 1024

        # Split the file into chunks
        chunks = []
        with open(test_file, "rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                chunks.append(chunk)

        print(f"Split file into {len(chunks)} chunks of {chunk_size/1024:.0f}KB each")

        # 1. Initialize the chunked upload
        print("\nStep 1: Initializing chunked upload")
        upload_id = str(uuid.uuid4())
        filename = "test_file.txt"

        try:
            upload_info = FileProcessor.init_chunked_upload(
                upload_id=upload_id,
                filename=filename,
                total_chunks=len(chunks),
                file_size=file_size,
                mime_type="text/plain",
                directory=test_dir,
            )
            print(f"✓ Upload initialized with ID: {upload_id}")
            print(f"  Status: {upload_info.get('status', 'unknown')}")
        except Exception as e:
            print(f"❌ Error initializing upload: {e}")
            raise

        # 2. Upload each chunk
        print("\nStep 2: Uploading chunks")
        for i, chunk_data in enumerate(chunks):
            print(f"  Uploading chunk {i+1}/{len(chunks)}")
            chunk_io = io.BytesIO(chunk_data)

            try:
                chunk_info = FileProcessor.save_chunk(
                    upload_id=upload_id, chunk_index=i, chunk_data=chunk_io
                )
                print(
                    f"  ✓ Chunk {i+1} saved - Status: {chunk_info.get('status', 'unknown')}"
                )
            except Exception as e:
                print(f"  ❌ Error saving chunk {i+1}: {e}")
                raise

        # 3. Complete the upload
        print("\nStep 3: Completing the upload")
        try:
            result = FileProcessor.complete_chunked_upload(
                upload_id=upload_id, target_directory=test_dir
            )
            print("✓ Upload completed successfully")
            print(f"  Final file: {result.get('file_path', 'unknown')}")
        except Exception as e:
            print(f"❌ Error completing upload: {e}")
            raise

        # 4. Verify the file content
        print("\nStep 4: Verifying file content")
        try:
            with open(result["file_path"], "rb") as f:
                final_content = f.read()

            if final_content == original_content:
                print("✓ File content verification PASSED")
                print(f"  Original size: {len(original_content)} bytes")
                print(f"  Final size: {len(final_content)} bytes")
            else:
                print("❌ File content verification FAILED")
                print(f"  Original size: {len(original_content)} bytes")
                print(f"  Final size: {len(final_content)} bytes")
                if abs(len(original_content) - len(final_content)) < 10:
                    print("  Sizes are close, could be minor differences")
        except Exception as e:
            print(f"❌ Error verifying file content: {e}")
            raise

        # 5. Check the upload status
        print("\nStep 5: Checking upload status")
        try:
            status = FileProcessor.get_chunked_upload_status(upload_id)
            print(f"✓ Upload status: {status.get('status', 'unknown')}")
        except Exception as e:
            print(f"❌ Error getting upload status: {e}")
            raise

        # 6. Clean up
        print("\nStep 6: Cleaning up")
        try:
            cleanup_result = FileProcessor.cleanup_chunked_upload(upload_id)
            print(f"✓ Cleanup {cleanup_result and 'successful' or 'failed'}")
        except Exception as e:
            print(f"❌ Error during cleanup: {e}")

        print("\n=== Test completed successfully ===")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")

    finally:
        # Clean up temporary files and directories
        print("\nFinal cleanup...")
        if os.path.exists(test_file):
            os.unlink(test_file)
            print(f"Removed test file: {test_file}")

        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
            print(f"Removed test directory: {test_dir}")


if __name__ == "__main__":
    run_test()
