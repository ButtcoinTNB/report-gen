/**
 * Interactive API Test Script
 * Tests the key API endpoints for the Insurance Report Generator
 * 
 * Usage: node api_test.js
 */

const fs = require('fs');
const path = require('path');
const axios = require('axios');
const FormData = require('form-data');

// Configuration
const API_BASE_URL = 'http://localhost:8000';
const TEST_FILE_PATH = path.join(__dirname, 'test.pdf');
const TEST_FILE_SIZE = 1024; // 1KB

// Create test file if it doesn't exist
if (!fs.existsSync(TEST_FILE_PATH)) {
  fs.writeFileSync(TEST_FILE_PATH, 'Test PDF content');
  console.log(`Created test file at ${TEST_FILE_PATH}`);
}

// Store state between tests
let state = {
  uploadId: null,
  fileId: null,
  taskId: null,
  reportId: null
};

// Helper for making API requests
async function callApi(method, endpoint, data = null, config = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  try {
    console.log(`${method.toUpperCase()} ${url}`);
    
    const response = await axios({
      method,
      url,
      data,
      ...config
    });
    
    console.log(`  Status: ${response.status}`);
    if (response.headers['x-ratelimit-remaining']) {
      console.log(`  Rate limit: ${response.headers['x-ratelimit-remaining']}/${response.headers['x-ratelimit-limit']}`);
    }
    
    return response.data;
  } catch (error) {
    console.error(`  Error: ${error.message}`);
    if (error.response) {
      console.error(`  Status: ${error.response.status}`);
      console.error(`  Data:`, error.response.data);
    }
    throw error;
  }
}

// Tests
async function testInitializeUpload() {
  console.log('\n=== Testing Upload Initialization ===');
  
  const formData = new FormData();
  formData.append('filename', 'test.pdf');
  formData.append('fileSize', TEST_FILE_SIZE);
  formData.append('mimeType', 'application/pdf');
  
  const result = await callApi('post', '/api/uploads/initialize', formData, {
    headers: formData.getHeaders()
  });
  
  console.log('  Result:', JSON.stringify(result, null, 2));
  
  if (result.uploadId) {
    state.uploadId = result.uploadId;
    return true;
  }
  
  return false;
}

async function testUploadChunk() {
  if (!state.uploadId) {
    console.error('No upload ID available. Skipping chunk upload test.');
    return false;
  }
  
  console.log('\n=== Testing Chunk Upload ===');
  
  const formData = new FormData();
  formData.append('uploadId', state.uploadId);
  formData.append('chunkIndex', 0);
  formData.append('start', 0);
  formData.append('end', TEST_FILE_SIZE - 1);
  formData.append('chunk', fs.createReadStream(TEST_FILE_PATH));
  
  const result = await callApi('post', '/api/uploads/chunk', formData, {
    headers: formData.getHeaders()
  });
  
  console.log('  Result:', JSON.stringify(result, null, 2));
  
  return result.chunkIndex === 0;
}

async function testFinalizeUpload() {
  if (!state.uploadId) {
    console.error('No upload ID available. Skipping finalize test.');
    return false;
  }
  
  console.log('\n=== Testing Upload Finalization ===');
  
  const formData = new FormData();
  formData.append('uploadId', state.uploadId);
  formData.append('filename', 'test.pdf');
  
  const result = await callApi('post', '/api/uploads/finalize', formData, {
    headers: formData.getHeaders()
  });
  
  console.log('  Result:', JSON.stringify(result, null, 2));
  
  if (result.status === 'success' && result.data && result.data.fileId) {
    state.fileId = result.data.fileId;
    return true;
  }
  
  return false;
}

async function testGenerateReport() {
  if (!state.fileId) {
    console.error('No file ID available. Skipping report generation test.');
    return false;
  }
  
  console.log('\n=== Testing Report Generation ===');
  
  const reportData = {
    insurance_data: {
      policy_number: '12345',
      claim_number: 'C-789456'
    },
    document_ids: [state.fileId],
    input_type: 'insurance',
    max_iterations: 1
  };
  
  try {
    const result = await callApi('post', '/api/agent-loop/generate-report', reportData, {
      headers: {
        'Content-Type': 'application/json'
      }
    });
    
    console.log('  Result:', JSON.stringify(result, null, 2));
    
    if (result.status === 'success' && result.data && result.data.task_id) {
      state.taskId = result.data.task_id;
      return true;
    }
  } catch (error) {
    console.log('  Note: Report generation may fail in test environment without proper document processing');
    return false;
  }
  
  return false;
}

async function testTaskStatus() {
  if (!state.taskId) {
    console.error('No task ID available. Skipping task status test.');
    return false;
  }
  
  console.log('\n=== Testing Task Status ===');
  
  try {
    const result = await callApi('get', `/api/agent-loop/task-status/${state.taskId}`);
    
    console.log('  Result:', JSON.stringify(result, null, 2));
    
    return true;
  } catch (error) {
    return false;
  }
}

// Run all tests
async function runTests() {
  try {
    console.log('Starting API Tests...');
    
    // Upload flow
    if (await testInitializeUpload()) {
      await testUploadChunk();
      await testFinalizeUpload();
    }
    
    // Report generation flow
    if (state.fileId) {
      await testGenerateReport();
      
      if (state.taskId) {
        await testTaskStatus();
      }
    }
    
    console.log('\nTests completed.');
  } catch (error) {
    console.error('\nTest execution failed:', error);
  }
}

// Execute tests
runTests(); 