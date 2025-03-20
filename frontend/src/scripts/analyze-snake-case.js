#!/usr/bin/env node

/**
 * Analyze snake_case usage in the codebase
 * 
 * This script scans the codebase for snake_case property references 
 * and reports files that need migration to camelCase.
 * 
 * Usage:
 *   node src/scripts/analyze-snake-case.js
 */

const fs = require('fs');
const path = require('path');
const glob = require('glob');

// Configuration
const SCAN_PATTERNS = [
  'src/**/*.ts',
  'src/**/*.tsx',
  'src/**/*.js',
  'src/**/*.jsx'
];

const EXCLUDE_PATTERNS = [
  'src/eslint-plugins/**',
  'src/scripts/**',
  'src/types/api.ts',
  'src/types/generated/**',
  'node_modules/**',
  'dist/**',
  '.next/**'
];

/**
 * Checks if a string contains snake_case property access
 * @param {string} content - The file content to check
 * @returns {Array<{match: string, line: number}>} Array of matches with line numbers
 */
function findSnakeCaseProperties(content) {
  // This regex looks for property access with snake_case (.something_like_this)
  const snakeCaseRegex = /\.([a-z][a-z0-9]*)(_[a-z][a-z0-9]*)+/g;
  
  const lines = content.split('\n');
  const results = [];
  
  lines.forEach((line, index) => {
    let match;
    while ((match = snakeCaseRegex.exec(line)) !== null) {
      results.push({
        match: match[0].substring(1), // Remove the dot
        line: index + 1, // 1-based line number
        context: line.trim()
      });
    }
  });
  
  return results;
}

/**
 * Processes a single file
 * @param {string} filePath - Path to the file
 * @returns {Array<{match: string, line: number, file: string}>} Array of matches with metadata
 */
function processFile(filePath) {
  try {
    const content = fs.readFileSync(filePath, 'utf-8');
    const matches = findSnakeCaseProperties(content);
    
    return matches.map(match => ({
      ...match,
      file: filePath
    }));
  } catch (error) {
    console.error(`Error processing ${filePath}:`, error.message);
    return [];
  }
}

/**
 * Gets files to analyze based on include and exclude patterns
 * @param {string[]} patterns - Glob patterns to include
 * @param {string[]} exclude - Glob patterns to exclude
 * @returns {string[]} Array of file paths
 */
function getFilesToAnalyze(patterns, exclude) {
  const allFiles = [];
  
  patterns.forEach(pattern => {
    const files = glob.sync(pattern, { ignore: exclude });
    allFiles.push(...files);
  });
  
  return [...new Set(allFiles)]; // Remove duplicates
}

/**
 * Main analysis function
 */
function analyzeSnakeCase() {
  console.log('Analyzing codebase for snake_case property usage...');
  
  // Get files to analyze
  const files = getFilesToAnalyze(SCAN_PATTERNS, EXCLUDE_PATTERNS);
  console.log(`Found ${files.length} files to analyze.`);
  
  // Process files
  let totalMatches = 0;
  const fileResults = {};
  
  files.forEach(file => {
    const matches = processFile(file);
    if (matches.length > 0) {
      fileResults[file] = matches;
      totalMatches += matches.length;
    }
  });
  
  // Report results
  console.log(`\nFound ${totalMatches} snake_case property references in ${Object.keys(fileResults).length} files.`);
  
  if (totalMatches > 0) {
    console.log('\nFiles with snake_case properties:');
    
    Object.entries(fileResults)
      .sort((a, b) => b[1].length - a[1].length) // Sort by number of matches (descending)
      .forEach(([file, matches]) => {
        console.log(`\n${file} (${matches.length} matches):`);
        matches.forEach(match => {
          console.log(`  - Line ${match.line}: ${match.match}`);
          console.log(`    "${match.context}"`);
        });
      });
      
    console.log('\nMigration progress:');
    const totalFiles = files.length;
    const filesWithSnakeCase = Object.keys(fileResults).length;
    const migrationPercentage = ((totalFiles - filesWithSnakeCase) / totalFiles * 100).toFixed(2);
    
    console.log(`${migrationPercentage}% of files migrated to camelCase (${totalFiles - filesWithSnakeCase}/${totalFiles})`);
  } else {
    console.log('\nAll analyzed files are using camelCase. Migration complete!');
  }
}

// Run analysis
analyzeSnakeCase(); 