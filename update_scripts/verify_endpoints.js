#!/usr/bin/env node

/**
 * Endpoint Verification Script for Insurance Report Generator
 * 
 * This script automatically tests that the API endpoints in the documentation
 * are working correctly by making actual requests to a running server.
 * 
 * Usage: node update_scripts/verify_endpoints.js
 */

const axios = require('axios');
const fs = require('fs');
const path = require('path');
const FormData = require('form-data');

// Configuration
const API_BASE_URL = 'http://localhost:8000';
const TEST_FILE_PATH = path.join(__dirname, '..', 'tests', 'test.pdf');
const RESULTS_DIR = path.join(__dirname, 'results');

// Create results directory if it doesn't exist
if (!fs.existsSync(RESULTS_DIR)) {
  fs.mkdirSync(RESULTS_DIR, { recursive: true });
}

// ANSI color codes for terminal output
const colors = {
  reset: "\x1b[0m",
  bright: "\x1b[1m",
  dim: "\x1b[2m",
  underscore: "\x1b[4m",
  blink: "\x1b[5m",
  reverse: "\x1b[7m",
  hidden: "\x1b[8m",
  
  fg: {
    black: "\x1b[30m",
    red: "\x1b[31m",
    green: "\x1b[32m",
    yellow: "\x1b[33m",
    blue: "\x1b[34m",
    magenta: "\x1b[35m",
    cyan: "\x1b[36m",
    white: "\x1b[37m"
  },
  
  bg: {
    black: "\x1b[40m",
    red: "\x1b[41m",
    green: "\x1b[42m",
    yellow: "\x1b[43m",
    blue: "\x1b[44m",
    magenta: "\x1b[45m",
    cyan: "\x1b[46m",
    white: "\x1b[47m"
  }
};

// Store state between tests
let state = {
  uploadId: null,
  fileId: null,
  taskId: null,
  reportId: null
};

// Save results of the endpoint verification
const results = {
  timestamp: new Date().toISOString(),
  endpoints: [],
  success: 0,
  failed: 0,
  skipped: 0
};

/**
 * Log a message with color
 */
function logMessage(message, color = 'white', bold = false) {
  const colorCode = colors.fg[color];
  const boldCode = bold ? colors.bright : '';
  console.log(`${boldCode}${colorCode}${message}${colors.reset}`);
}

/**
 * Log a test result
 */
function logResult(endpoint, method, success, message, data = null) {
  const color = success ? 'green' : 'red';
  const status = success ? 'SUCCESS' : 'FAILED';
  
  logMessage(`[${status}] ${method} ${endpoint}`, color, true);
  logMessage(`  ${message}`, success ? 'green' : 'yellow');
  
  // Add to results
  results.endpoints.push({
    endpoint,
    method,
    success,
    message,
    data: data ? JSON.stringify(data) : null
  });
  
  if (success) {
    results.success++;
  } else {
    results.failed++;
  }
}

/**
 * Test an endpoint
 */
async function testEndpoint(method, endpoint, data = null, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  
  logMessage(`Testing ${method} ${endpoint}...`, 'cyan');
  
  try {
    const response = await axios({
      method,
      url,
      data,
      ...options
    });
    
    logResult(
      endpoint, 
      method, 
      true, 
      `Status: ${response.status}`, 
      response.data
    );
    
    return response.data;
  } catch (error) {
    let errorMessage = error.message;
    let errorData = null;
    
    if (error.response) {
      errorMessage = `Status: ${error.response.status} - ${error.response.statusText}`;
      errorData = error.response.data;
    }
    
    logResult(
      endpoint, 
      method, 
      false, 
      errorMessage, 
      errorData
    );
    
    throw error;
  }
}

/**
 * Test uploadId initialization
 */
async function testInitializeUpload() {
  logMessage('\n=== Testing Upload Initialization ===', 'blue', true);
  
  const formData = new FormData();
  formData.append('filename', 'test.pdf');
  formData.append('fileSize', fs.statSync(TEST_FILE_PATH).size);
  formData.append('mimeType', 'application/pdf');
  
  try {
    const result = await testEndpoint('post', '/api/uploads/initialize', formData, {
      headers: formData.getHeaders()
    });
    
    if (result.uploadId) {
      state.uploadId = result.uploadId;
      return true;
    }
  } catch (error) {
    logMessage('  Upload initialization failed', 'red');
  }
  
  return false;
}

/**
 * Test chunk upload
 */
async function testUploadChunk() {
  if (!state.uploadId) {
    logMessage('  No upload ID available. Skipping chunk upload test.', 'yellow');
    results.skipped++;
    return false;
  }
  
  logMessage('\n=== Testing Chunk Upload ===', 'blue', true);
  
  const formData = new FormData();
  formData.append('uploadId', state.uploadId);
  formData.append('chunkIndex', 0);
  formData.append('start', 0);
  formData.append('end', fs.statSync(TEST_FILE_PATH).size - 1);
  formData.append('chunk', fs.createReadStream(TEST_FILE_PATH));
  
  try {
    const result = await testEndpoint('post', '/api/uploads/chunk', formData, {
      headers: formData.getHeaders()
    });
    
    return result.chunkIndex === 0;
  } catch (error) {
    logMessage('  Chunk upload failed', 'red');
    return false;
  }
}

/**
 * Test finalize upload
 */
async function testFinalizeUpload() {
  if (!state.uploadId) {
    logMessage('  No upload ID available. Skipping finalize test.', 'yellow');
    results.skipped++;
    return false;
  }
  
  logMessage('\n=== Testing Upload Finalization ===', 'blue', true);
  
  const formData = new FormData();
  formData.append('uploadId', state.uploadId);
  formData.append('filename', 'test.pdf');
  
  try {
    const result = await testEndpoint('post', '/api/uploads/finalize', formData, {
      headers: formData.getHeaders()
    });
    
    if (result.success && result.fileId) {
      state.fileId = result.fileId;
      return true;
    } else if (result.success) {
      // Some implementations might not return fileId
      return true;
    }
  } catch (error) {
    logMessage('  Finalize upload failed', 'red');
  }
  
  return false;
}

/**
 * Test report generation
 */
async function testGenerateReport() {
  logMessage('\n=== Testing Report Generation ===', 'blue', true);
  
  // We can still test this endpoint with a dummy document ID
  const documentId = state.fileId || "test-document-id";
  
  const reportData = {
    insurance_data: {
      policy_number: '12345',
      claim_number: 'C-789456'
    },
    document_ids: [documentId],
    input_type: 'insurance',
    max_iterations: 1
  };
  
  try {
    const result = await testEndpoint('post', '/api/agent-loop/generate-report', reportData, {
      headers: {
        'Content-Type': 'application/json'
      }
    });
    
    if (result.status === 'success' && result.data && result.data.task_id) {
      state.taskId = result.data.task_id;
      return true;
    }
  } catch (error) {
    logMessage('  Report generation failed', 'red');
  }
  
  return false;
}

/**
 * Test task status
 */
async function testTaskStatus() {
  if (!state.taskId) {
    logMessage('  No task ID available. Skipping task status test.', 'yellow');
    results.skipped++;
    return false;
  }
  
  logMessage('\n=== Testing Task Status ===', 'blue', true);
  
  try {
    const result = await testEndpoint('get', `/api/agent-loop/task-status/${state.taskId}`);
    return true;
  } catch (error) {
    logMessage('  Task status check failed', 'red');
    return false;
  }
}

/**
 * Save the test results
 */
function saveResults() {
  const resultsFile = path.join(RESULTS_DIR, `endpoint_verification_${Date.now()}.json`);
  fs.writeFileSync(resultsFile, JSON.stringify(results, null, 2));
  logMessage(`\nResults saved to ${resultsFile}`, 'cyan');
}

/**
 * Print a summary of the tests
 */
function printSummary() {
  logMessage('\n=== Test Summary ===', 'blue', true);
  logMessage(`Total tests: ${results.success + results.failed + results.skipped}`, 'white', true);
  logMessage(`Successful: ${results.success}`, 'green');
  logMessage(`Failed: ${results.failed}`, results.failed > 0 ? 'red' : 'white');
  logMessage(`Skipped: ${results.skipped}`, results.skipped > 0 ? 'yellow' : 'white');
}

/**
 * Run all tests
 */
async function runTests() {
  logMessage('Starting API Endpoint Verification', 'magenta', true);
  logMessage('This script will test that the API endpoints match the documentation.\n', 'cyan');
  
  try {
    // Test the upload flow
    await testInitializeUpload();
    await testUploadChunk();
    await testFinalizeUpload();
    
    // Test the report generation flow
    await testGenerateReport();
    await testTaskStatus();
    
    // Print a summary and save results
    printSummary();
    saveResults();
    
    // Exit with appropriate code
    process.exit(results.failed > 0 ? 1 : 0);
  } catch (error) {
    logMessage('\nTest execution encountered an error:', 'red', true);
    console.error(error);
    process.exit(1);
  }
}

// Execute tests
runTests(); 