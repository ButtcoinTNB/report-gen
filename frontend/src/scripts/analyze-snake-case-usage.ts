#!/usr/bin/env ts-node
/**
 * @fileoverview Tool for analyzing snake_case property usage in the codebase
 * @author Insurance Report Generator Team
 * 
 * Usage:
 * ```
 * npm run analyze:snake-case-usage
 * ```
 */

import * as fs from 'fs';
import * as path from 'path';
import * as ts from 'typescript';
import * as glob from 'glob';

interface SnakeCaseUsage {
  filePath: string;
  lineNumber: number;
  column: number;
  propertyName: string;
  context: string;
}

/**
 * Checks if a string is in snake_case
 * @param str The string to check
 * @returns True if the string is in snake_case
 */
function isSnakeCase(str: string): boolean {
  return /^[a-z]+(_[a-z]+)+$/.test(str);
}

/**
 * Analyzes a TypeScript file for snake_case property access
 * @param filePath Path to the TypeScript file
 * @returns Array of snake_case usage information
 */
function analyzeFile(filePath: string): SnakeCaseUsage[] {
  const usages: SnakeCaseUsage[] = [];
  
  // Read the file
  const fileContent = fs.readFileSync(filePath, 'utf8');
  const lines = fileContent.split('\n');
  
  // Parse the file
  const sourceFile = ts.createSourceFile(
    filePath,
    fileContent,
    ts.ScriptTarget.Latest,
    true
  );
  
  // Visit each node in the source file
  function visit(node: ts.Node) {
    // Check for property access
    if (ts.isPropertyAccessExpression(node)) {
      const propertyName = node.name.escapedText.toString();
      
      if (isSnakeCase(propertyName)) {
        const { line, character } = sourceFile.getLineAndCharacterOfPosition(node.name.getStart());
        const lineNumber = line + 1; // Lines are 0-indexed in TypeScript
        const column = character + 1;
        
        // Get the context (the line of code)
        const context = lines[line].trim();
        
        usages.push({
          filePath,
          lineNumber,
          column,
          propertyName,
          context
        });
      }
    }
    
    // Continue traversing the AST
    ts.forEachChild(node, visit);
  }
  
  visit(sourceFile);
  
  return usages;
}

/**
 * Analyzes the project for snake_case property usage
 * @returns Array of all snake_case usages in the project
 */
function analyzeProject(): SnakeCaseUsage[] {
  const sourceDir = path.resolve(process.cwd(), 'src');
  const tsFiles = glob.sync(`${sourceDir}/**/*.{ts,tsx}`, {
    ignore: [`${sourceDir}/**/*.d.ts`, `${sourceDir}/**/node_modules/**`]
  });
  
  console.log(`Analyzing ${tsFiles.length} TypeScript files...`);
  
  let allUsages: SnakeCaseUsage[] = [];
  
  for (const file of tsFiles) {
    try {
      const usages = analyzeFile(file);
      allUsages = [...allUsages, ...usages];
    } catch (error) {
      console.error(`Error analyzing file ${file}:`, error);
    }
  }
  
  return allUsages;
}

/**
 * Writes the analysis results to an HTML report
 * @param usages The snake_case usages found in the project
 */
function generateReport(usages: SnakeCaseUsage[]): void {
  const reportDir = path.resolve(process.cwd(), 'reports');
  if (!fs.existsSync(reportDir)) {
    fs.mkdirSync(reportDir, { recursive: true });
  }
  
  const reportPath = path.join(reportDir, 'snake-case-usage-report.html');
  
  // Group usages by file
  const fileGroups: { [key: string]: SnakeCaseUsage[] } = {};
  for (const usage of usages) {
    const relativePath = path.relative(process.cwd(), usage.filePath);
    if (!fileGroups[relativePath]) {
      fileGroups[relativePath] = [];
    }
    fileGroups[relativePath].push(usage);
  }
  
  // Generate HTML
  const html = `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Snake Case Usage Report</title>
  <style>
    body {
      font-family: Arial, sans-serif;
      margin: 0;
      padding: 20px;
      line-height: 1.6;
    }
    h1, h2, h3 {
      color: #333;
    }
    .summary {
      background-color: #f5f5f5;
      padding: 15px;
      border-radius: 5px;
      margin-bottom: 20px;
    }
    .file {
      margin-bottom: 30px;
      border: 1px solid #ddd;
      border-radius: 5px;
      overflow: hidden;
    }
    .file-header {
      background-color: #eee;
      padding: 10px 15px;
      border-bottom: 1px solid #ddd;
      cursor: pointer;
    }
    .file-content {
      padding: 15px;
    }
    .usage {
      margin-bottom: 15px;
      padding-bottom: 15px;
      border-bottom: 1px solid #eee;
    }
    .usage:last-child {
      border-bottom: none;
    }
    .context {
      font-family: monospace;
      background-color: #f9f9f9;
      padding: 10px;
      border-radius: 3px;
      overflow-x: auto;
    }
    .property {
      color: #d73a49;
      font-weight: bold;
    }
    .badge {
      display: inline-block;
      padding: 3px 8px;
      border-radius: 10px;
      font-size: 12px;
      font-weight: bold;
      margin-left: 10px;
      background-color: #e0e0e0;
    }
  </style>
</head>
<body>
  <h1>Snake Case Usage Report</h1>
  
  <div class="summary">
    <h2>Summary</h2>
    <p>Total snake_case usages found: <strong>${usages.length}</strong></p>
    <p>Files with snake_case usages: <strong>${Object.keys(fileGroups).length}</strong></p>
    <p>Generated on: <strong>${new Date().toLocaleString()}</strong></p>
  </div>
  
  <h2>Detailed Results</h2>
  
  ${Object.entries(fileGroups)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([filePath, fileUsages]) => `
    <div class="file">
      <div class="file-header" onclick="this.nextElementSibling.style.display = this.nextElementSibling.style.display === 'none' ? 'block' : 'none'">
        ${filePath} <span class="badge">${fileUsages.length}</span>
      </div>
      <div class="file-content">
        ${fileUsages
          .sort((a, b) => a.lineNumber - b.lineNumber)
          .map(usage => `
          <div class="usage">
            <p>
              <strong>Line ${usage.lineNumber}, Column ${usage.column}</strong>: 
              Property <span class="property">${usage.propertyName}</span>
            </p>
            <div class="context">${usage.context.replace(
              usage.propertyName,
              `<span class="property">${usage.propertyName}</span>`
            )}</div>
          </div>
        `).join('')}
      </div>
    </div>
  `).join('')}
  
  <script>
    // Toggle file content visibility
    document.querySelectorAll('.file-header').forEach(header => {
      header.addEventListener('click', () => {
        const content = header.nextElementSibling;
        content.style.display = content.style.display === 'none' ? 'block' : 'none';
      });
    });
  </script>
</body>
</html>
  `;
  
  fs.writeFileSync(reportPath, html);
  
  console.log(`Report generated at: ${reportPath}`);
}

/**
 * Main function
 */
function main(): void {
  console.log('Analyzing snake_case property usage in the codebase...');
  
  const usages = analyzeProject();
  
  console.log(`Found ${usages.length} snake_case property usages in the codebase.`);
  
  if (usages.length > 0) {
    generateReport(usages);
  } else {
    console.log('No snake_case property usages found! Great job!');
  }
}

main(); 