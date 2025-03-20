#!/usr/bin/env ts-node
/**
 * Interface Generator Script
 * 
 * This script automatically generates camelCase TypeScript interfaces from
 * snake_case API definitions.
 * 
 * Usage:
 * ```
 * npx ts-node src/scripts/generate-interfaces.ts [input-file] [output-file]
 * ```
 * 
 * Example:
 * ```
 * npx ts-node src/scripts/generate-interfaces.ts src/types/api-definitions.ts src/types/generated.ts
 * ```
 */

const fs = require('fs');
const path = require('path');
const ts = require('typescript');

// Type definition for the typescript module
type TypeScript = typeof import('typescript');
const typescript: TypeScript = ts;

/**
 * Represents a property in an interface
 */
interface InterfaceProperty {
  name: string;
  type: string;
  optional: boolean;
  jsDoc?: string;
}

/**
 * Represents an interface definition
 */
interface InterfaceDefinition {
  name: string;
  properties: InterfaceProperty[];
  typeParameters: string[];
  extends: string[];
  jsDoc?: string;
}

/**
 * Converts a snake_case string to camelCase
 */
function snakeToCamel(str: string): string {
  return str.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());
}

/**
 * Extract interfaces from TypeScript source file
 */
function extractInterfaces(sourceFile: any): InterfaceDefinition[] {
  const interfaces: InterfaceDefinition[] = [];

  function visit(node: any) {
    if (typescript.isInterfaceDeclaration(node)) {
      const interfaceName = node.name.text;
      
      // Skip if it already ends with "Camel"
      if (interfaceName.endsWith('Camel')) {
        return;
      }
      
      const properties: InterfaceProperty[] = [];
      const typeParameters: string[] = [];
      const extendsClause: string[] = [];
      
      // Extract JSDoc comments
      const jsDoc = node.getFullText().split('\n')
        .filter((line: string) => line.trim().startsWith('/**') || line.trim().startsWith('*') || line.trim().startsWith('*/'))
        .join('\n');
      
      // Extract type parameters
      if (node.typeParameters) {
        node.typeParameters.forEach((param: any) => {
          typeParameters.push(param.getText(sourceFile));
        });
      }
      
      // Extract extends clause
      if (node.heritageClauses) {
        node.heritageClauses.forEach((clause: any) => {
          if (clause.token === typescript.SyntaxKind.ExtendsKeyword) {
            clause.types.forEach((type: any) => {
              extendsClause.push(type.getText(sourceFile));
            });
          }
        });
      }
      
      // Extract properties
      for (const member of node.members) {
        if (typescript.isPropertySignature(member)) {
          const propertyName = member.name?.getText(sourceFile);
          if (propertyName) {
            const type = member.type?.getText(sourceFile) || 'any';
            const optional = !!member.questionToken;
            
            // Extract property JSDoc
            const propertyJsDoc = member.getFullText().split('\n')
              .filter((line: string) => line.trim().startsWith('/**') || line.trim().startsWith('*') || line.trim().startsWith('*/'))
              .join('\n');
            
            properties.push({
              name: propertyName,
              type,
              optional,
              jsDoc: propertyJsDoc || undefined
            });
          }
        }
      }
      
      interfaces.push({
        name: interfaceName,
        properties,
        typeParameters,
        extends: extendsClause,
        jsDoc
      });
    }
    
    typescript.forEachChild(node, visit);
  }
  
  visit(sourceFile);
  return interfaces;
}

/**
 * Generate camelCase interface from snake_case interface definition
 */
function generateCamelCaseInterface(interfaceDef: InterfaceDefinition): string {
  const camelName = `${interfaceDef.name}Camel`;
  let camelInterface = '';
  
  // Add JSDoc if available
  if (interfaceDef.jsDoc) {
    camelInterface += `${interfaceDef.jsDoc}\n`;
  } else {
    camelInterface += `/**\n * Frontend-friendly version of ${interfaceDef.name} with camelCase properties\n */\n`;
  }
  
  // Start interface definition
  camelInterface += `export interface ${camelName}`;
  
  // Add type parameters if available
  if (interfaceDef.typeParameters.length > 0) {
    camelInterface += `<${interfaceDef.typeParameters.join(', ')}>`;
  }
  
  // Add extends clause if available
  if (interfaceDef.extends.length > 0) {
    // Convert the extends to camelCase versions
    const camelExtends = interfaceDef.extends.map(ext => ext.endsWith('Camel') ? ext : `${ext}Camel`).join(', ');
    
    camelInterface += ` extends ${camelExtends}`;
  }
  
  camelInterface += ' {\n';
  
  // Add properties
  for (const prop of interfaceDef.properties) {
    // Skip properties that should be inherited
    if (interfaceDef.extends.length > 0 && prop.name.startsWith('inherited_')) {
      continue;
    }
    
    // Add property JSDoc if available
    if (prop.jsDoc) {
      camelInterface += `  ${prop.jsDoc}\n`;
    }
    
    const camelPropName = snakeToCamel(prop.name.replace(/['"]/g, ''));
    const optional = prop.optional ? '?' : '';
    
    camelInterface += `  ${camelPropName}${optional}: ${prop.type};\n`;
  }
  
  camelInterface += '}\n\n';
  
  // Generate adapter function
  camelInterface += `/**\n * Helper function to convert API response to frontend format\n */\n`;
  camelInterface += `export function adapt${interfaceDef.name}(response: ${interfaceDef.name}): ${camelName} {\n`;
  camelInterface += '  return adaptApiResponse<' + camelName + '>(response);\n';
  camelInterface += '}\n\n';
  
  return camelInterface;
}

/**
 * Generate a TypeScript file with camelCase interfaces
 */
function generateInterfacesFile(
  inputFile: string, 
  outputFile: string
): void {
  // Read input file
  const source = fs.readFileSync(inputFile, 'utf-8');
  
  // Parse TypeScript
  const sourceFile = typescript.createSourceFile(
    path.basename(inputFile),
    source,
    typescript.ScriptTarget.Latest,
    true
  );
  
  // Extract interfaces
  const interfaces = extractInterfaces(sourceFile);
  
  // Generate camelCase interfaces
  let output = `/**
 * GENERATED FILE - DO NOT EDIT DIRECTLY
 * Generated by generate-interfaces.ts
 * from ${path.basename(inputFile)}
 * 
 * This file contains camelCase versions of the snake_case interfaces
 * defined in the API types.
 */

import { adaptApiResponse } from '../../utils/adapters';

/**
 * Utility type for converting snake_case properties to camelCase
 */
export type CamelCase<T> = {
  [K in keyof T as K extends string 
    ? K extends \`\${infer A}_\${infer B}\` 
      ? \`\${A}\${Capitalize<B>}\` 
      : K 
    : never]: T[K] extends Record<string, any> 
      ? CamelCase<T[K]> 
      : T[K] extends Array<infer U> 
        ? U extends Record<string, any> 
          ? Array<CamelCase<U>> 
          : T[K] 
        : T[K]
};\n`;

  // Import original interfaces
  output += `import {\n`;
  interfaces.forEach(intf => {
    output += `  ${intf.name},\n`;
  });
  output += `} from './${path.basename(inputFile, '.ts')}';\n\n`;
  
  // Generate camelCase interfaces
  for (const intf of interfaces) {
    output += generateCamelCaseInterface(intf);
  }
  
  // Write output file
  fs.writeFileSync(outputFile, output);
  
  console.log(`Generated ${interfaces.length} camelCase interfaces in ${outputFile}`);
}

// Main function
function main() {
  const args = process.argv.slice(2);
  
  if (args.length < 2) {
    console.error('Usage: npx ts-node src/scripts/generate-interfaces.ts [input-file] [output-file]');
    process.exit(1);
  }
  
  const inputFile = args[0];
  const outputFile = args[1];
  
  try {
    generateInterfacesFile(inputFile, outputFile);
  } catch (error) {
    console.error('Error generating interfaces:', error);
    process.exit(1);
  }
}

// Run the script
if (require.main === module) {
  main();
}

// Export for testing using CommonJS syntax
module.exports = { extractInterfaces, generateCamelCaseInterface }; 