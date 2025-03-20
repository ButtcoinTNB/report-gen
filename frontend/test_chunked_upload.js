/**
 * Test script for chunked file uploads
 * This script simulates a frontend chunked upload by:
 * 1. Creating a large test file
 * 2. Using the UploadService to upload it
 * 3. Tracking progress and verifying the upload
 * 
 * Run with: node test_chunked_upload.js
 */

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const axios = require('axios');
const FormData = require('form-data');

// Configuration
const TEST_FILE_SIZE = 100 * 1024 * 1024; // 100 MB
const CHUNK_SIZE = 5 * 1024 * 1024; // 5 MB chunks
const API_BASE_URL = 'http://localhost:8000/api';
const TEST_FILE_PATH = path.join(__dirname, 'test_large_file.bin');

/**
 * Creates a test file of specified size filled with random data
 */
function createTestFile(filePath, sizeInBytes) {
  console.log(`Creating test file (${sizeInBytes / (1024 * 1024)} MB) at ${filePath}...`);
  
  // Create buffer with random data
  const chunkSize = 1024 * 1024; // Write in 1MB chunks to avoid memory issues
  const fd = fs.openSync(filePath, 'w');
  
  let bytesWritten = 0;
  while (bytesWritten < sizeInBytes) {
    const writeSize = Math.min(chunkSize, sizeInBytes - bytesWritten);
    const buffer = crypto.randomBytes(writeSize);
    fs.writeSync(fd, buffer, 0, buffer.length);
    bytesWritten += writeSize;
    
    // Log progress every 10MB
    if (bytesWritten % (10 * 1024 * 1024) === 0) {
      console.log(`  ${bytesWritten / (1024 * 1024)} MB written...`);
    }
  }
  
  fs.closeSync(fd);
  console.log(`Test file created: ${filePath} (${bytesWritten / (1024 * 1024)} MB)`);
}

/**
 * Simulates a chunked file upload using the same API the frontend uses
 */
async function uploadFileInChunks(filePath) {
  const fileName = path.basename(filePath);
  const fileSize = fs.statSync(filePath).size;
  const totalChunks = Math.ceil(fileSize / CHUNK_SIZE);
  
  console.log(`Starting chunked upload of ${fileName} (${fileSize / (1024 * 1024)} MB) in ${totalChunks} chunks`);
  
  try {
    // Step 1: Initialize the chunked upload
    console.log('\nInitializing chunked upload...');
    const initResponse = await axios.post(`${API_BASE_URL}/upload/chunked/init`, {
      file_name: fileName,
      file_size: fileSize,
      total_chunks: totalChunks,
      mime_type: 'application/octet-stream'
    });
    
    const uploadId = initResponse.data.data.uploadId;
    console.log(`Upload initialized with ID: ${uploadId}`);
    
    // Step 2: Upload each chunk
    const fileBuffer = fs.readFileSync(filePath);
    let uploadedBytes = 0;
    
    for (let chunkIndex = 0; chunkIndex < totalChunks; chunkIndex++) {
      const start = chunkIndex * CHUNK_SIZE;
      const end = Math.min(start + CHUNK_SIZE, fileSize);
      const chunkData = fileBuffer.slice(start, end);
      const chunkSize = end - start;
      
      console.log(`\nUploading chunk ${chunkIndex + 1}/${totalChunks} (${chunkSize / 1024} KB)...`);
      
      const formData = new FormData();
      // Create a Buffer from chunk data for Node.js FormData compatibility
      const buffer = Buffer.from(chunkData);
      formData.append('file', buffer, {
        filename: `${fileName}.part${chunkIndex}`,
        contentType: 'application/octet-stream',
        knownLength: buffer.length
      });
      
      // Log upload attempt
      console.log(`  Sending ${buffer.length} bytes to ${API_BASE_URL}/upload/chunked/chunk/${uploadId}/${chunkIndex}`);
      
      const chunkResponse = await axios.post(
        `${API_BASE_URL}/upload/chunked/chunk/${uploadId}/${chunkIndex}`,
        formData,
        {
          headers: {
            ...formData.getHeaders(),
          },
          maxContentLength: Infinity,
          maxBodyLength: Infinity
        }
      );
      
      uploadedBytes += chunkSize;
      const progress = Math.round((uploadedBytes / fileSize) * 100);
      console.log(`Chunk ${chunkIndex + 1} uploaded successfully. Total progress: ${progress}%`);
    }
    
    // Step 3: Complete the upload
    console.log('\nFinalizing upload...');
    const completeResponse = await axios.post(`${API_BASE_URL}/upload/chunked/complete`, {
      upload_id: uploadId
    });
    
    console.log('\nUpload completed successfully!');
    console.log('File details:');
    console.log(`  File ID: ${completeResponse.data.data.fileId}`);
    console.log(`  Filename: ${completeResponse.data.data.filename}`);
    console.log(`  Path: ${completeResponse.data.data.filePath}`);
    console.log(`  Size: ${completeResponse.data.data.fileSize / (1024 * 1024)} MB`);
    console.log(`  MIME Type: ${completeResponse.data.data.mimeType}`);
    
    return completeResponse.data;
  } catch (error) {
    console.error('Upload failed:', error.message);
    if (error.response) {
      console.error('Response data:', error.response.data);
      console.error('Response status:', error.response.status);
    }
    throw error;
  }
}

/**
 * Clean up test files
 */
function cleanupTestFiles() {
  if (fs.existsSync(TEST_FILE_PATH)) {
    fs.unlinkSync(TEST_FILE_PATH);
    console.log(`Removed test file: ${TEST_FILE_PATH}`);
  }
}

/**
 * Main test function
 */
async function runTest() {
  console.log('===== CHUNKED UPLOAD TEST =====');
  
  try {
    // Create test file if it doesn't exist
    if (!fs.existsSync(TEST_FILE_PATH)) {
      createTestFile(TEST_FILE_PATH, TEST_FILE_SIZE);
    } else {
      console.log(`Using existing test file: ${TEST_FILE_PATH}`);
    }
    
    // Upload the file
    const startTime = Date.now();
    await uploadFileInChunks(TEST_FILE_PATH);
    const duration = (Date.now() - startTime) / 1000;
    
    console.log(`\nTest completed in ${duration.toFixed(2)} seconds`);
    
    // Clean up test files (optional - comment out to keep the file)
    // cleanupTestFiles();
    
  } catch (error) {
    console.error('Test failed:', error);
  }
}

// Run the test
runTest(); 