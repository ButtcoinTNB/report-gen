# Adapter Pattern for Type-Safe API Interactions

## Overview

This codebase uses an adapter pattern to bridge the gap between our backend API (which uses snake_case naming) and our frontend components (which use camelCase naming). This pattern ensures type safety while maintaining a clean separation between API data structures and frontend component props.

## Why We Need Adapters

1. **Different Naming Conventions**: 
   - Backend API uses `snake_case` (e.g., `report_id`)
   - Frontend components use `camelCase` (e.g., `reportId`)

2. **Type Safety**: 
   - Without adapters, we risk typos and undefined properties
   - Components may incorrectly access properties that don't exist

3. **Consistent API**: 
   - Provides a standardized way to convert between formats
   - Makes refactoring easier as the codebase grows

## Adapter Types

### 1. General Adapters

Located in `src/utils/adapters.ts`:

- `adaptApiResponse<T>`: Converts snake_case API responses to camelCase
- `adaptApiRequest<T>`: Converts camelCase frontend objects to snake_case for API requests
- `snakeToCamelObject<T>` and `camelToSnakeObject<T>`: Low-level utilities for key conversion

### 2. Component-Specific Adapters

- `createAnalysisResponse`: Converts API analysis responses to component-friendly format
- `createHybridReportPreview`: Creates objects with both snake_case and camelCase properties for backward compatibility

## Usage Examples

### API Service Layer

```typescript
// In a service file
async getReportPreview(reportId: string): Promise<ReportPreviewCamel> {
  const response = await this.get<ReportPreview>(`/preview/${reportId}`);
  return adaptApiResponse<ReportPreviewCamel>(response.data);
}
```

### Component Layer

```typescript
// In a component file
const apiResponse = {
  extracted_variables: analysisDetails,
  fields_needing_attention: fieldsNeedingAttention,
  status: 'success',
  message: ''
};

// Convert to component-friendly format
const analysisResponse = createAnalysisResponse(apiResponse);

// Access converted properties
analysisResponse.analysisDetails.forEach((details) => {
  console.log(details.confidence); // Uses camelCase
});
```

### Type Definitions

```typescript
// API types (snake_case)
export interface ReportPreview {
  report_id: string;
  preview_url: string;
  status: 'success' | 'error';
}

// Frontend types (camelCase)
export interface ReportPreviewCamel {
  reportId: string;
  previewUrl: string;
  status: 'success' | 'error';
}
```

## Best Practices

1. **Always Use Typed Adapters**: Specify the return type using generics: `adaptApiResponse<MyType>(data)`

2. **Create Component-Specific Adapters**: For complex conversions beyond simple key renaming

3. **Document Special Cases**: Add JSDoc comments explaining any non-obvious conversions

4. **Consistent Naming**: Use the pattern `TypeNameCamel` for camelCase versions of interfaces

5. **Error Handling**: All adapters should include error handling to prevent runtime crashes

## Migration Strategy

When working with legacy code that directly accesses snake_case properties:

1. Create hybrid objects with both snake_case and camelCase properties
2. Gradually update components to use camelCase properties
3. Eventually remove the snake_case properties when all components are updated 