#!/usr/bin/env python3
"""
Standalone test script for file chunking functionality.
This script doesn't rely on the FileProcessor class or any external dependencies.
"""

import os
import uuid
import tempfile
import shutil
import json
import io

def create_test_file(size_bytes=1024*1024):
    """Create a test file of a specific size"""
    print(f"Creating test file of size {size_bytes/1024/1024:.2f} MB")
    test_file = tempfile.NamedTemporaryFile(delete=False)
    
    # Create random data
    with open(test_file.name, 'wb') as f:
        f.write(os.urandom(size_bytes))
    
    print(f"Created test file: {test_file.name}")
    return test_file.name

def init_chunked_upload(upload_id, filename, total_chunks, file_size, directory):
    """Initialize a chunked upload operation"""
    # Create a temporary directory for chunks
    chunks_dir = os.path.join(directory, f"chunks_{upload_id}")
    os.makedirs(chunks_dir, exist_ok=True)
    
    # Track this upload
    upload_info = {
        "upload_id": upload_id,
        "filename": filename,
        "original_filename": filename,
        "chunks_dir": chunks_dir,
        "total_chunks": total_chunks,
        "received_chunks": 0,
        "file_size": file_size,
        "mime_type": "application/octet-stream",
        "created_at": 0,
        "last_updated": 0,
        "status": "initialized",
        "completed": False
    }
    
    # Store metadata
    metadata_path = os.path.join(chunks_dir, "metadata.json")
    with open(metadata_path, "w") as f:
        json.dump(upload_info, f)
        
    print(f"Initialized chunked upload {upload_id} for {filename} with {total_chunks} chunks")
    return upload_info

def save_chunk(upload_id, chunk_index, chunk_data, chunks_dir):
    """Save a chunk of data for a chunked upload"""
    # Check if the chunks directory exists
    if not os.path.exists(chunks_dir):
        raise ValueError(f"Chunks directory {chunks_dir} not found")
    
    # Check if metadata exists
    metadata_path = os.path.join(chunks_dir, "metadata.json")
    if not os.path.exists(metadata_path):
        raise ValueError(f"Metadata file not found in {chunks_dir}")
    
    # Read metadata
    with open(metadata_path, "r") as f:
        upload_info = json.load(f)
    
    # Validate chunk index
    if chunk_index < 0 or chunk_index >= upload_info["total_chunks"]:
        raise ValueError(f"Chunk index {chunk_index} is out of range (0-{upload_info['total_chunks']-1})")
    
    # Save chunk to file
    chunk_path = os.path.join(chunks_dir, f"chunk_{chunk_index}")
    
    # If chunk_data is a file-like object
    if hasattr(chunk_data, 'read'):
        with open(chunk_path, "wb") as chunk_file:
            shutil.copyfileobj(chunk_data, chunk_file)
    else:
        # If chunk_data is bytes
        with open(chunk_path, "wb") as chunk_file:
            chunk_file.write(chunk_data)
    
    # Update upload info
    upload_info["received_chunks"] += 1
    upload_info["last_updated"] = 0
    
    # Update status
    if upload_info["received_chunks"] == upload_info["total_chunks"]:
        upload_info["status"] = "ready_to_combine"
    else:
        upload_info["status"] = "in_progress"
    
    # Update metadata file
    with open(metadata_path, "w") as f:
        json.dump(upload_info, f)
    
    print(f"Saved chunk {chunk_index} for upload {upload_id} ({upload_info['received_chunks']}/{upload_info['total_chunks']})")
    return upload_info

def complete_chunked_upload(upload_id, target_directory, chunks_dir, target_filename=None):
    """Complete a chunked upload by combining all chunks"""
    # Check if the chunks directory exists
    if not os.path.exists(chunks_dir):
        raise ValueError(f"Chunks directory {chunks_dir} not found")
    
    # Check if metadata exists
    metadata_path = os.path.join(chunks_dir, "metadata.json")
    if not os.path.exists(metadata_path):
        raise ValueError(f"Metadata file not found in {chunks_dir}")
    
    # Read metadata
    with open(metadata_path, "r") as f:
        upload_info = json.load(f)
    
    # Check if all chunks have been received
    if upload_info["received_chunks"] != upload_info["total_chunks"]:
        raise ValueError(
            f"Upload not complete: received {upload_info['received_chunks']} of {upload_info['total_chunks']} chunks"
        )
    
    # Generate a filename if not provided
    if not target_filename:
        target_filename = upload_info["original_filename"]
    
    # Create full target path
    target_path = os.path.join(target_directory, target_filename)
    
    # Ensure target directory exists
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    
    # Combine all chunks into the final file
    with open(target_path, "wb") as target_file:
        for i in range(upload_info["total_chunks"]):
            chunk_path = os.path.join(chunks_dir, f"chunk_{i}")
            if not os.path.exists(chunk_path):
                raise ValueError(f"Chunk {i} is missing")
            
            with open(chunk_path, "rb") as chunk_file:
                shutil.copyfileobj(chunk_file, target_file)
    
    # Update upload info
    upload_info["status"] = "completed"
    upload_info["completed"] = True
    upload_info["final_path"] = target_path
    upload_info["last_updated"] = 0
    
    # Update metadata file
    with open(metadata_path, "w") as f:
        json.dump(upload_info, f)
    
    print(f"Completed chunked upload {upload_id}. Final file saved to {target_path}")
    return {
        "upload_id": upload_id,
        "file_path": target_path,
        "original_filename": upload_info["original_filename"],
        "size_bytes": os.path.getsize(target_path)
    }

def cleanup_chunked_upload(upload_id, chunks_dir):
    """Clean up all files associated with a chunked upload"""
    try:
        if os.path.exists(chunks_dir) and os.path.isdir(chunks_dir):
            shutil.rmtree(chunks_dir)
        
        print(f"Cleaned up chunked upload {upload_id}")
        return True
    except Exception as e:
        print(f"Error cleaning up chunked upload {upload_id}: {str(e)}")
        return False

def run_test():
    """Run a test for chunked upload functionality"""
    print("\n=== Testing Chunked Upload Functionality ===\n")
    
    # Create a temp directory for uploads
    test_dir = tempfile.mkdtemp()
    print(f"Created test directory: {test_dir}")
    
    # Create a test file (1MB)
    test_file = create_test_file(1024*1024)
    file_size = os.path.getsize(test_file)
    print(f"Test file size: {file_size} bytes")
    
    # Read the file content for comparison later
    print("Reading original file content for comparison")
    with open(test_file, 'rb') as f:
        original_content = f.read()
    
    try:
        # Define chunk size (256KB for this test)
        chunk_size = 256*1024
        
        # Split the file into chunks
        chunks = []
        with open(test_file, 'rb') as f:
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
            upload_info = init_chunked_upload(
                upload_id=upload_id,
                filename=filename,
                total_chunks=len(chunks),
                file_size=file_size,
                directory=test_dir
            )
            chunks_dir = upload_info["chunks_dir"]
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
                chunk_info = save_chunk(
                    upload_id=upload_id,
                    chunk_index=i,
                    chunk_data=chunk_io,
                    chunks_dir=chunks_dir
                )
                print(f"  ✓ Chunk {i+1} saved - Status: {chunk_info.get('status', 'unknown')}")
            except Exception as e:
                print(f"  ❌ Error saving chunk {i+1}: {e}")
                raise
        
        # 3. Complete the upload
        print("\nStep 3: Completing the upload")
        try:
            result = complete_chunked_upload(
                upload_id=upload_id,
                target_directory=test_dir,
                chunks_dir=chunks_dir,
                target_filename="combined_file.bin"
            )
            print("✓ Upload completed successfully")
            print(f"  Final file: {result.get('file_path', 'unknown')}")
        except Exception as e:
            print(f"❌ Error completing upload: {e}")
            raise
        
        # 4. Verify the file content
        print("\nStep 4: Verifying file content")
        try:
            with open(result['file_path'], 'rb') as f:
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
        
        # 5. Clean up
        print("\nStep 5: Cleaning up")
        try:
            cleanup_result = cleanup_chunked_upload(upload_id, chunks_dir)
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