# API Naming Conventions

## Overview

Our application bridges between two different code style conventions:

1. **Frontend (TypeScript/JavaScript)**: Uses `camelCase` for property names
2. **Backend (Python/FastAPI)**: Uses `snake_case` for property names

This document outlines our approach to handling these differences consistently.

## The Problem

Without a standardized approach, we end up with:

- Inconsistent naming in our codebase
- Redundant properties (both `report_id` and `reportId` in the same interface)
- Type errors and confusion about which convention to use where

## Our Solution: Adapters

We've implemented adapter utilities in `frontend/src/utils/adapters.ts` to convert between these conventions automatically.

### Key Components

1. **String Converters**:
   - `snakeToCamel()`: Converts `snake_case` to `camelCase`
   - `camelToSnake()`: Converts `camelCase` to `snake_case`

2. **Object Converters**:
   - `snakeToCamelObject()`: Recursively converts all keys in an object from `snake_case` to `camelCase`
   - `camelToSnakeObject()`: Recursively converts all keys in an object from `camelCase` to `snake_case`

3. **API Adapters**:
   - `adaptApiResponse()`: Converts backend responses (in `snake_case`) to frontend-friendly `camelCase`
   - `adaptApiRequest()`: Converts frontend requests (in `camelCase`) to backend-friendly `snake_case`

4. **TypeScript Utilities**:
   - `CamelCase<T>`: Type utility to derive a camelCase interface from a snake_case one

## How to Use

### In API Services

```typescript
import { adaptApiRequest, adaptApiResponse } from '../../utils/adapters';

// When making API requests:
async function createReport(reportId: string, userData: UserData) {
  // Convert request to snake_case for backend
  const requestData = adaptApiRequest({ reportId, userData });
  
  // Make API call
  const response = await api.post('/reports', requestData);
  
  // Convert response to camelCase for frontend
  return adaptApiResponse<ReportResponse>(response.data);
}
```

### For TypeScript Types

Use the `CamelCase` type utility to automatically generate frontend-friendly interfaces:

```typescript
// Backend API interface (snake_case)
interface ApiResponse {
  report_id: string;
  preview_url: string;
  user_data: {
    first_name: string;
    last_name: string;
  };
}

// Frontend interface (camelCase)
type ClientResponse = CamelCase<ApiResponse>;
// Equivalent to:
// interface ClientResponse {
//   reportId: string;
//   previewUrl: string;
//   userData: {
//     firstName: string;
//     lastName: string;
//   };
// }
```

## Best Practices

1. **Always use camelCase in frontend code**:
   - React components
   - State variables
   - TypeScript interfaces (except when directly representing API responses)
   - Function parameters

2. **Use the adapters at API boundaries**:
   - Convert to snake_case just before sending to the backend
   - Convert to camelCase immediately when receiving from the backend
   - Don't pass snake_case objects around in frontend code

3. **For path parameters and URL segments**:
   - These don't need conversion, use them directly: `/api/reports/${reportId}`

4. **Define separate interfaces** for:
   - API response/request types (with snake_case, matching the backend API)
   - Frontend types (with camelCase, for use throughout the app)

5. **Use the `Camel` suffix** for interfaces that represent camelCase versions of API interfaces:
   ```typescript
   // API response type (snake_case)
   interface GenerateReportResponse { report_id: string; ... }
   
   // Frontend-friendly version (camelCase)
   interface GenerateReportResponseCamel { reportId: string; ... }
   ```

## Type Safety

The adapters maintain type safety by:

1. Using TypeScript generics to preserve type information
2. Providing expected return types
3. Handling complex nested objects and arrays

## Examples

Check out `frontend/src/services/api/ReportService.ts` for a full example implementation of the adapter pattern.

## Legacy Code Notes

While migrating existing code:

1. Look for places where both versions co-exist (e.g., `report_id` and `reportId` in the same interface)
2. Use the adapter pattern to normalize to camelCase on the frontend
3. Use TypeScript interfaces to enforce consistency 