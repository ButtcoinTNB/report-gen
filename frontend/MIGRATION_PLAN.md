# Frontend Migration Plan: snake_case to camelCase

## Overview

This document outlines our plan to systematically address the medium priority issue related to type inconsistency between frontend and backend. Our codebase currently has a mix of snake_case (backend style) and camelCase (frontend style) properties, with some "hybrid" interfaces that maintain both for compatibility.

## Current Status

Our codebase has several issues that need to be addressed:

1. **Hybrid Interfaces**: Many interfaces contain both snake_case and camelCase properties, leading to confusion and potential bugs.
2. **Inconsistent Property Access**: Some components directly access snake_case properties, while others use camelCase.
3. **Adapter Function Usage**: Adapter functions exist but are not consistently used across all API service calls.

## Incremental Migration Strategy

We'll use a gradual approach to ensure minimal disruption to the application:

### Phase 1: API Services Cleanup (In Progress)

1. ✅ Ensure all API services use the `ApiClient` which handles conversion automatically
2. ✅ Remove direct references to `adaptApiRequest` and `adaptApiResponse` where the `ApiClient` already handles this
3. ✅ Update method signatures to work with camelCase interfaces

### Phase 2: Component Interface Migration

1. Create a list of all components using snake_case properties:
   - FileUpload.tsx
   - ReportGenerator.tsx
   - Other components found during the analysis

2. For each component:
   - Define clear camelCase interfaces
   - Update property access to use camelCase properties
   - Update component state to use camelCase objects

### Phase 3: Type Definition Cleanup

1. Review all interfaces in `/src/types`:
   - ✅ Ensure all interfaces have both snake_case (API) and camelCase (frontend) versions
   - ✅ Add proper JSDoc comments to indicate usage for each type
   - ✅ Consider deprecating hybrid interfaces
   
2. Create adapter functions for any missing type conversions

### Phase 4: Standardization

1. Update the ESLint rule `no-snake-case-props` to error level (currently warning)
2. Run ESLint across the codebase to identify remaining snake_case property usage
3. Create an issue for each remaining snake_case usage
4. Update the remaining components one by one

## Implementation Details

### Conversion Functions

We have a set of utility functions in `src/utils/adapters.ts`:

- `snakeToCamel`: Converts a string from snake_case to camelCase
- `camelToSnake`: Converts a string from camelCase to snake_case
- `snakeToCamelObject`: Converts all object keys from snake_case to camelCase
- `camelToSnakeObject`: Converts all object keys from camelCase to snake_case
- `adaptApiResponse`: Converts API responses from snake_case to camelCase
- `adaptApiRequest`: Converts frontend requests from camelCase to snake_case

### API Client

Our `ApiClient` already has built-in conversion:
- Request interceptor converts camelCase to snake_case
- Response interceptor converts snake_case to camelCase
- All API services should use this client for automatic conversion

## Tracking Progress

| Component/File | Status | Next Steps |
|----------------|--------|------------|
| ApiClient.ts | ✅ Complete | None |
| DownloadService.ts | ✅ Updated | None |
| ReportService.ts | ✅ Updated | None |
| UploadService.ts | ✅ Using ApiClient | None |
| FileUpload.tsx | 🟡 In Progress | Complete conversion to camelCase |
| ReportGenerator.tsx | 🟡 In Progress | Complete conversion to camelCase |
| EditPage | ❌ Not Started | Convert to camelCase interfaces |

## Timeline

- Phase 1: 1 week (in progress)
- Phase 2: 2 weeks
- Phase 3: 1 week
- Phase 4: 2 weeks

Total estimated time: 6 weeks

## Resources

- [TypeScript Best Practices](https://www.typescriptlang.org/docs/handbook/declaration-files/do-s-and-don-ts.html)
- [Frontend MIGRATION_STRATEGY.md](./src/docs/MIGRATION_STRATEGY.md)
- [Adapter Pattern Documentation](./src/docs/ADAPTER_PATTERN.md) 