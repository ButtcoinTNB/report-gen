# TypeScript Migration Guide: snake_case to camelCase

This document details the process of migrating the Insurance Report Generator frontend codebase from using mixed snake_case/camelCase properties to consistent camelCase naming conventions.

## Migration Goals

1. **Consistent Property Naming**: Use camelCase for all TypeScript properties to align with JavaScript/TypeScript conventions
2. **Type Safety**: Ensure proper typing throughout the codebase
3. **API Compatibility**: Maintain compatibility with the backend API that uses snake_case

## Tools Created for the Migration

### 1. Interface Generator

The interface generator automatically creates camelCase versions of our snake_case API interfaces.

**Usage:**
```bash
npm run generate:api-interfaces
```

This command:
1. Reads the snake_case interfaces from `src/types/api.ts`
2. Generates camelCase equivalents in `src/types/generated/api-camel.ts`

### 2. ESLint Plugin for Detecting snake_case Usage

A custom ESLint plugin that detects snake_case property usage and suggests camelCase alternatives.

**Configuration:**
- Plugin: `src/eslint-plugins/no-snake-case-props.js`
- Rule: `local/no-snake-case-props`

### 3. snake_case Analyzer

A utility script to analyze the codebase for remaining snake_case property references.

**Usage:**
```bash
npm run analyze:snake-case
```

This provides a detailed report of:
- Files containing snake_case properties
- Line numbers and context for each occurrence
- Overall migration progress percentage

## Migration Strategy

1. **Generate camelCase Interfaces**
   - Run `npm run generate:api-interfaces` to create camelCase versions of API interfaces

2. **Implement Adapter Pattern**
   - Use adapter functions to convert between snake_case (API) and camelCase (frontend)
   - See `src/utils/adapters.ts` for implementation

3. **Update Components**
   - Gradually update components to use camelCase properties
   - Use the ESLint plugin to identify snake_case usage
   - Run the analyzer regularly to track progress

4. **Continuous Monitoring**
   - Add linting to CI/CD pipeline to prevent new snake_case properties
   - Update the analyzer script as needed

## Adapter Pattern

The adapter pattern is used to convert between snake_case (API) and camelCase (frontend) formats:

```typescript
// Convert API response (snake_case) to frontend (camelCase)
const camelResponse = adaptApiResponse<ReportPreviewCamel>(response);

// Convert frontend request (camelCase) to API (snake_case)
const snakeRequest = adaptApiRequest<GenerateRequest>(request);
```

### Key Adapter Functions

- `snakeToCamel`: Converts string from snake_case to camelCase
- `camelToSnake`: Converts string from camelCase to snake_case
- `snakeToCamelObject`: Transforms an object's keys from snake_case to camelCase
- `camelToSnakeObject`: Transforms an object's keys from camelCase to snake_case
- `adaptApiResponse`: Adapts API responses to frontend format
- `adaptApiRequest`: Adapts frontend requests to API format

## Recent Enhancements

As part of our ongoing improvements, we've made the following enhancements:

### 1. Comprehensive JSDoc Documentation

We've significantly expanded the JSDoc documentation in `adapters.ts` to provide:
- A clear architectural overview of the adapter pattern
- Detailed usage guidelines for different parts of the codebase
- Specific examples for each adapter function
- Best practices for maintaining code consistency

### 2. Consistent API Client Implementation

We've improved the API client classes to consistently use adapter functions:
- Updated `createApiClient` to properly handle configuration options
- Ensured direct snake_case property access is limited to the adapter layer
- Applied consistent patterns for request/response handling across all API services

### 3. Layer Responsibility Clarification

We've clarified the responsibilities of each code layer:
- **API Services Layer**: Can reference snake_case for direct API communication but should convert data for components
- **Component Layer**: Should only work with camelCase properties
- **Adapter Layer**: Manages the transition between formats

## Utility Types

A `CamelCase<T>` utility type has been created to automatically transform snake_case interface properties to camelCase:

```typescript
// Define the utility type
export type CamelCase<T> = {
  [K in keyof T as K extends string 
    ? K extends `${infer A}_${infer B}` 
      ? `${A}${Capitalize<B>}` 
      : K 
    : never]: T[K] extends Record<string, any> 
      ? CamelCase<T[K]> 
      : T[K] extends Array<infer U> 
        ? U extends Record<string, any> 
          ? Array<CamelCase<U>> 
          : T[K] 
        : T[K]
};

// Use it to create camelCase versions of snake_case interfaces
type UserCamel = CamelCase<User>; // Converts user_id to userId, etc.
```

## Migration Progress Tracking

As of the last analysis, **77.78%** of files have been fully migrated to camelCase.

Remaining files with snake_case properties:
- `src/utils/adapters.ts`
- `src/services/api/DownloadService.ts`
- `src/services/api/ApiClient.ts`
- `src/services/api/UploadService.ts`

**Note:** These files are expected to retain some snake_case properties as they directly interface with the backend API.

## Best Practices Going Forward

1. **Always use camelCase** for new component properties and variables
2. **Use the adapter pattern** when interfacing with the API
3. **Run the linter** before committing code: `npm run lint`
4. **Track migration progress** regularly: `npm run analyze:snake-case`
5. **Refer to the JSDoc comments** in `adapters.ts` for guidance on proper implementation

## Troubleshooting

If you encounter type errors after migration:

1. Make sure you're importing the camelCase interface (`FooCamel`) not the snake_case one (`Foo`)
2. Use the adapter functions to convert between formats
3. Check for missing properties or incorrect property names

## Additional Resources

- [TypeScript Naming Conventions](https://www.typescriptlang.org/docs/handbook/declaration-files/do-s-and-don-ts.html)
- [ESLint Rules for TypeScript](https://typescript-eslint.io/rules/) 