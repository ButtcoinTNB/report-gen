# TypeScript Migration Tools

This document describes the tools implemented to support our migration from snake_case to camelCase in the Insurance Report Generator frontend.

## Overview

Our TypeScript codebase needs consistent type definitions and naming conventions. We've created several tools to:

1. **Detect** where snake_case is being used
2. **Convert** between snake_case and camelCase automatically
3. **Generate** camelCase interfaces from snake_case API definitions
4. **Enforce** style rules through ESLint

## Tools Available

### 1. Interface Generator

Automatically generates camelCase interfaces from snake_case API definitions.

**Usage:**
```bash
# Run with default settings
npm run generate:interfaces

# Run with specific input/output files
npm run generate:api-interfaces
```

The generator reads TypeScript interfaces from an input file, converts property names to camelCase, and outputs new interfaces with "Camel" suffix.

### 2. Snake Case Usage Analyzer

Scans the codebase for snake_case property access and generates an HTML report.

**Usage:**
```bash
npm run analyze:snake-case-usage
```

The analyzer:
- Traverses all TypeScript files in the src directory
- Identifies property access using snake_case naming
- Generates a detailed HTML report with file paths, line numbers, and context
- Outputs the report to `reports/snake-case-usage-report.html`

### 3. ESLint Rule for Snake Case Detection

Custom ESLint rule that warns when snake_case properties are accessed.

**Usage:**
The rule is automatically applied when running ESLint:
```bash
npm run lint
```

The rule:
- Detects property access using snake_case naming
- Suggests camelCase alternatives
- Can automatically fix issues when run with `--fix` flag

### 4. Adapter Utilities

Utility functions to convert between snake_case and camelCase for API interactions.

**Location:** `src/utils/adapters.ts`

Key functions:
- `snakeToCamel`: Converts string from snake_case to camelCase
- `camelToSnake`: Converts string from camelCase to snake_case
- `snakeToCamelObject`: Transforms an object's keys from snake_case to camelCase
- `camelToSnakeObject`: Transforms an object's keys from camelCase to snake_case
- `adaptApiResponse`: Adapts API responses to camelCase for frontend use
- `adaptApiRequest`: Adapts frontend data to snake_case for API requests
- Type utility `CamelCase<T>`: Creates camelCase types from snake_case types

## Implementation Strategy

For a full guide on how to use these tools as part of our migration strategy, see the [Migration Strategy](./MIGRATION_STRATEGY.md) document.

## Extending the Tools

### Adding New Adapter Functions

To add a new adapter for a specific API response type:

1. Define the snake_case interface in `src/types/api.ts`
2. Run the interface generator: `npm run generate:api-interfaces`
3. Create an adapter function in `src/utils/adapters.ts`:

```typescript
export function adaptMyApiResponse(response: MyApiResponse): MyApiResponseCamel {
  return snakeToCamelObject(response) as MyApiResponseCamel;
}
```

### Adding ESLint Rules

To add more TypeScript style rules:

1. Create a new rule file in `src/eslint-plugins/`
2. Export the rule in `src/eslint-plugins/index.js`
3. Add the rule to `.eslintrc.json`

## Troubleshooting

### Interface Generator Errors

If the interface generator fails with errors:

1. Ensure the input file contains valid TypeScript interface definitions
2. Check that interfaces don't have circular dependencies
3. Try running with the `--debug` flag: `ts-node src/scripts/generate-interfaces.ts --debug input.ts output.ts`

### ESLint Plugin Issues

If the ESLint plugin doesn't work:

1. Ensure you've added the plugin correctly to `.eslintrc.json`
2. Try running `npm i -g eslint-plugin-local` to install the plugin globally
3. Check for syntax errors in the plugin files

## Future Improvements

Planned enhancements for these tools:

1. Integration with CI/CD to block PRs with snake_case usage
2. Automatic code modification tool to convert snake_case to camelCase
3. Visual dashboard for monitoring migration progress
4. Extended test coverage for adapter functions 