# Gradual Migration Strategy for Removing Hybrid Objects

## Overview

This document outlines our strategy for gradually moving away from "hybrid objects" (objects with both snake_case and camelCase properties) as we complete our migration to a fully camelCase frontend codebase. This transition ensures type safety while maintaining backward compatibility with legacy code.

## Current State

Currently, our codebase uses a combination of approaches:

1. **Snake_case API Types**: Represent the backend API's native format (`report_id`, `preview_url`, etc.)
2. **CamelCase Frontend Types**: Frontend-friendly versions of these types (`reportId`, `previewUrl`, etc.)
3. **Hybrid Types**: Objects containing both formats for compatibility during migration

The hybrid approach provides a bridge between legacy code and newer components but introduces redundancy and potential confusion.

## Migration Plan

### Phase 1: Identify and Track Usage (Current)

- [x] Document all locations where snake_case properties are accessed directly
- [x] Add adapter functions for all API responses
- [x] Implement the `createHybridX` pattern for backward compatibility

### Phase 2: Incremental Component Updates (In Progress)

- [ ] Update components one by one to use camelCase properties exclusively
- [ ] For each component migration:
  - [ ] Update props interfaces to use camelCase types
  - [ ] Update all property access to use camelCase
  - [ ] Update tests to reflect changes
  - [ ] Verify functionality remains unchanged

### Phase 3: Deprecation (Future)

- [ ] Add JSDoc `@deprecated` tags to hybrid creation functions
- [ ] Add ESLint rules to warn about usage of snake_case properties
- [ ] Add console warnings in development mode when hybrid objects are created
- [ ] Set a deadline for full migration (e.g., 3 months from now)

### Phase 4: Removal (Future)

- [ ] Remove all hybrid creation functions
- [ ] Update adapter functions to return only camelCase properties
- [ ] Remove snake_case properties from type definitions
- [ ] Update all imports to use generated camelCase types

## Implementation Techniques

### Tracking Progress

We will use a spreadsheet to track migration progress:

| Component | Status | Target Date | Notes |
|-----------|--------|-------------|-------|
| ReportPreview | ✅ Migrated | 2023-03-21 | Using camelCase props exclusively |
| DocumentUpload | ✅ Migrated | 2023-03-22 | Using camelCase return types |
| GenerateReport | ⏳ In Progress | 2023-03-25 | Still using some snake_case properties |
| ... | ... | ... | ... |

### Automated Detection

We've implemented several tools to assist in migration:

1. **Interface Generator**: Automatically creates camelCase versions of snake_case interfaces
   ```bash
   npm run generate:api-interfaces
   ```

2. **ESLint Rules**: Custom rules to identify snake_case property access
   ```javascript
   // Add to .eslintrc.js
   rules: {
     'no-snake-case-props': 'warn',
     // ...
   }
   ```

3. **Type Migration Helper**: TypeScript utility to identify code that needs updating
   ```bash
   npm run analyze:snake-case-usage
   ```

## Best Practices

1. **One Component at a Time**: Focus on fully migrating one component before moving to the next
2. **Test Thoroughly**: Ensure full test coverage before and after migration
3. **Keep Adapters Centralized**: Don't add new adapter logic in components
4. **Document Everything**: Add JSDoc comments explaining the migration status
5. **Coordinate with Team**: Communicate progress and changes to all developers

## Example Migration

### Before

```typescript
// Component using snake_case properties directly
const MyComponent: React.FC<Props> = ({ report }) => {
  return (
    <div>
      <h1>{report.title}</h1>
      <p>ID: {report.report_id}</p>
      <a href={report.preview_url}>Preview</a>
    </div>
  );
};
```

### After

```typescript
// Component using camelCase properties with proper typing
const MyComponent: React.FC<Props> = ({ report }) => {
  // report is now properly typed as ReportCamel
  return (
    <div>
      <h1>{report.title}</h1>
      <p>ID: {report.reportId}</p>
      <a href={report.previewUrl}>Preview</a>
    </div>
  );
};
```

## Timeline

- **Month 1**: Complete Phase 1 and begin Phase 2
- **Month 2-3**: Continue Phase 2, update 2-3 components per week
- **Month 4**: Begin Phase 3, start deprecation process
- **Month 6**: Begin Phase 4, completely remove hybrid objects

## Conclusion

By following this gradual migration strategy, we can eliminate hybrid objects from our codebase while maintaining backward compatibility and ensuring a smooth transition for developers. The end result will be a more type-safe, maintainable, and consistent frontend codebase. 