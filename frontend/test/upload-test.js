/**
 * Test script for testing the chunked upload functionality.
 * Run this with: node test/upload-test.js
 */

const fs = require('fs');
const path = require('path');
const axios = require('axios');
const FormData = require('form-data');

// Configuration
const API_BASE_URL = 'http://localhost:3000/api/upload'; // Adjust to your API endpoint
const CHUNK_SIZE = 5 * 1024 * 1024; // 5MB chunks
const TEST_FILES_DIR = path.resolve(__dirname, 'test-files');

// Ensure test files directory exists
if (!fs.existsSync(TEST_FILES_DIR)) {
  fs.mkdirSync(TEST_FILES_DIR, { recursive: true });
}

// Create sample test files if they don't exist
const SMALL_FILE_PATH = path.join(TEST_FILES_DIR, 'small-file.txt');
const LARGE_FILE_PATH = path.join(TEST_FILES_DIR, 'large-file.bin');

if (!fs.existsSync(SMALL_FILE_PATH)) {
  console.log('Creating small test file...');
  fs.writeFileSync(SMALL_FILE_PATH, 'A'.repeat(1024 * 1024)); // 1MB file
}

if (!fs.existsSync(LARGE_FILE_PATH)) {
  console.log('Creating large test file...');
  // Create a 60MB file
  const writeStream = fs.createWriteStream(LARGE_FILE_PATH);
  for (let i = 0; i < 60; i++) {
    writeStream.write(Buffer.alloc(1024 * 1024, `chunk${i}`));
  }
  writeStream.end();
  console.log('Large test file created');
}

/**
 * Test the standard upload endpoint for small files
 */
async function testStandardUpload() {
  console.log('\n--- Testing Standard Upload ---');
  try {
    const formData = new FormData();
    formData.append('files', fs.createReadStream(SMALL_FILE_PATH));
    
    console.log(`Uploading ${SMALL_FILE_PATH}...`);
    const startTime = Date.now();
    
    const response = await axios.post(`${API_BASE_URL}/documents`, formData, {
      headers: {
        ...formData.getHeaders(),
      },
      maxContentLength: Infinity,
      maxBodyLength: Infinity
    });
    
    const endTime = Date.now();
    console.log(`Standard upload completed in ${(endTime - startTime) / 1000} seconds`);
    console.log('Response:', JSON.stringify(response.data, null, 2));
    return true;
  } catch (error) {
    console.error('Error in standard upload:', error.response?.data || error.message);
    return false;
  }
}

/**
 * Test the chunked upload process for large files
 */
async function testChunkedUpload() {
  console.log('\n--- Testing Chunked Upload ---');
  const fileName = path.basename(LARGE_FILE_PATH);
  const fileSize = fs.statSync(LARGE_FILE_PATH).size;
  const totalChunks = Math.ceil(fileSize / CHUNK_SIZE);
  
  console.log(`Starting chunked upload of ${fileName} (${fileSize / (1024 * 1024)} MB) in ${totalChunks} chunks`);
  const startTime = Date.now();
  
  try {
    // Step 1: Initialize the chunked upload
    console.log('\nInitializing chunked upload...');
    const initResponse = await axios.post(`${API_BASE_URL}/chunked/init`, {
      filename: fileName,
      fileSize: fileSize,
      totalChunks: totalChunks,
      fileType: 'application/octet-stream'
    });
    
    const uploadId = initResponse.data.data.uploadId;
    console.log(`Upload initialized with ID: ${uploadId}`);
    
    // Step 2: Upload each chunk
    const fileBuffer = fs.readFileSync(LARGE_FILE_PATH);
    let uploadedBytes = 0;
    
    for (let chunkIndex = 0; chunkIndex < totalChunks; chunkIndex++) {
      const start = chunkIndex * CHUNK_SIZE;
      const end = Math.min(start + CHUNK_SIZE, fileSize);
      const chunkData = fileBuffer.slice(start, end);
      const chunkSize = end - start;
      
      console.log(`\nUploading chunk ${chunkIndex + 1}/${totalChunks} (${chunkSize / 1024} KB)...`);
      
      const formData = new FormData();
      // Create a Buffer from chunk data
      const buffer = Buffer.from(chunkData);
      formData.append('file', buffer, {
        filename: `${fileName}.part${chunkIndex}`,
        contentType: 'application/octet-stream',
        knownLength: buffer.length
      });
      
      const chunkResponse = await axios.post(
        `${API_BASE_URL}/chunked/chunk/${uploadId}/${chunkIndex}`,
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
    const completeResponse = await axios.post(`${API_BASE_URL}/chunked/complete`, {
      uploadId: uploadId
    });
    
    const endTime = Date.now();
    console.log('\nUpload completed successfully!');
    console.log(`Total time: ${(endTime - startTime) / 1000} seconds`);
    console.log('File details:');
    console.log(`  File ID: ${completeResponse.data.data.fileId}`);
    console.log(`  Filename: ${completeResponse.data.data.filename}`);
    console.log(`  Path: ${completeResponse.data.data.filePath}`);
    console.log(`  Size: ${completeResponse.data.data.fileSize / (1024 * 1024)} MB`);
    
    return true;
  } catch (error) {
    console.error('Error in chunked upload:', error.response?.data || error.message);
    return false;
  }
}

/**
 * Main function to run all tests
 */
async function runTests() {
  console.log('=== Upload Test Script ===');
  
  // Test standard upload
  const standardUploadSuccess = await testStandardUpload();
  
  // Test chunked upload
  const chunkedUploadSuccess = await testChunkedUpload();
  
  // Summary
  console.log('\n=== Test Results ===');
  console.log(`Standard Upload: ${standardUploadSuccess ? 'PASSED' : 'FAILED'}`);
  console.log(`Chunked Upload: ${chunkedUploadSuccess ? 'PASSED' : 'FAILED'}`);
  
  if (standardUploadSuccess && chunkedUploadSuccess) {
    console.log('\nAll tests passed successfully!');
    process.exit(0);
  } else {
    console.log('\nSome tests failed. Check logs for details.');
    process.exit(1);
  }
}

// Run the tests
runTests().catch(error => {
  console.error('Test error:', error);
  process.exit(1);
}); 