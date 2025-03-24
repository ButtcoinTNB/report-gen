/**
 * Simple test script for the chunked upload functionality
 * Run with: node test_chunked_upload.js
 */

const fs = require('fs');
const path = require('path');
const axios = require('axios');
const FormData = require('form-data');

// Configuration
const API_BASE_URL = 'http://localhost:8000';
const TEST_FILE_PATH = './test-file.txt'; // Create a test file or use an existing one
const CHUNK_SIZE = 1 * 1024 * 1024; // 1MB chunks for testing

// Create a test file if it doesn't exist
function createTestFile(size = 5 * 1024 * 1024) {
  console.log(`Creating test file of size ${size / (1024 * 1024)}MB...`);
  
  // Generate random content
  const content = Buffer.alloc(size, '0');
  for (let i = 0; i < size; i++) {
    content[i] = Math.floor(Math.random() * 256);
  }
  
  fs.writeFileSync(TEST_FILE_PATH, content);
  console.log(`Test file created at ${TEST_FILE_PATH}`);
}

// Main function to test the chunked upload
async function testChunkedUpload() {
  try {
    // Check if test file exists
    if (!fs.existsSync(TEST_FILE_PATH)) {
      createTestFile();
    }
    
    const fileStats = fs.statSync(TEST_FILE_PATH);
    console.log(`Test file size: ${fileStats.size / (1024 * 1024)}MB`);
    
    // Initialize upload
    console.log('1. Initializing chunked upload...');
    const formData = new FormData();
    formData.append('filename', path.basename(TEST_FILE_PATH));
    formData.append('fileSize', fileStats.size.toString());
    formData.append('mimeType', 'text/plain');
    
    const initResponse = await axios.post(
      `${API_BASE_URL}/api/upload-chunked/initialize`,
      formData,
      {
        headers: formData.getHeaders(),
      }
    );
    
    const { uploadId, chunkSize, totalChunks, uploadedChunks } = initResponse.data;
    console.log(`Upload initialized successfully: ID=${uploadId}, totalChunks=${totalChunks}`);
    
    // Upload chunks
    console.log('2. Uploading chunks...');
    const fileContent = fs.readFileSync(TEST_FILE_PATH);
    
    for (let i = 0; i < totalChunks; i++) {
      // Skip already uploaded chunks
      if (uploadedChunks.includes(i)) {
        console.log(`Chunk ${i} already uploaded, skipping...`);
        continue;
      }
      
      const start = i * chunkSize;
      const end = Math.min(start + chunkSize, fileStats.size);
      const chunkData = fileContent.slice(start, end);
      
      const chunkFormData = new FormData();
      chunkFormData.append('uploadId', uploadId);
      chunkFormData.append('chunkIndex', i.toString());
      chunkFormData.append('start', start.toString());
      chunkFormData.append('end', end.toString());
      chunkFormData.append('chunk', Buffer.from(chunkData), `chunk_${i}.bin`);
      
      console.log(`Uploading chunk ${i}/${totalChunks-1} (${chunkData.length} bytes)...`);
      
      const chunkResponse = await axios.post(
        `${API_BASE_URL}/api/upload-chunked/chunk`,
        chunkFormData,
        {
          headers: chunkFormData.getHeaders(),
        }
      );
      
      console.log(`Chunk ${i} uploaded successfully`);
    }
    
    // Finalize upload
    console.log('3. Finalizing upload...');
    const finalizeFormData = new FormData();
    finalizeFormData.append('uploadId', uploadId);
    finalizeFormData.append('filename', path.basename(TEST_FILE_PATH));
    
    const finalizeResponse = await axios.post(
      `${API_BASE_URL}/api/upload-chunked/finalize`,
      finalizeFormData,
      {
        headers: finalizeFormData.getHeaders(),
      }
    );
    
    console.log('Upload completed successfully!');
    console.log('Response:', JSON.stringify(finalizeResponse.data, null, 2));
    
    return finalizeResponse.data;
  } catch (error) {
    console.error('Error during chunked upload test:');
    if (error.response) {
      console.error(`Status: ${error.response.status}`);
      console.error('Data:', error.response.data);
    } else {
      console.error(error.message);
    }
    throw error;
  }
}

// Run the test
testChunkedUpload()
  .then(() => {
    console.log('Test completed successfully!');
    process.exit(0);
  })
  .catch(() => {
    console.error('Test failed!');
    process.exit(1);
  }); 