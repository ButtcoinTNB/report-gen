# snake_case to camelCase Migration: Step-by-Step Guide

## Immediate Steps

### 1. Component Updates

#### FileUpload.tsx
- [x] Add camelCase interface for UploadResponse (UploadResponseCamel)
- [x] Update onDrop and handleSubmit methods to use camelCase properties
- [x] Fix remaining linter errors related to the UploadService

#### ReportGenerator.tsx
- [x] Import and use ReportCamel instead of Report where appropriate
- [x] Update references of snake_case properties to camelCase
- [x] Use adaptReport function when handling API responses

#### Edit Page
- [x] Create a ReportDataCamel interface extending ReportCamel
- [x] Update state to use camelCase properties
- [x] Change API call code to use camelCase consistently

### 2. Service Layer Refinements

#### UploadService.ts
- [x] Review uploadFiles method to ensure it handles FormData properly
- [x] Ensure all methods consistently use adaptApiResponse where needed
- [x] Add proper JSDoc documentation for all methods

#### ReportService.ts
- [x] Ensure all methods return camelCase interfaces
- [x] Update method signatures to use camelCase parameters

### 3. Type Definition Updates

- [x] Review all types in index.ts to ensure full coverage
- [x] Add explicit CamelCase versions for any missing types
- [x] Add deprecation notices to hybrid interfaces

## Medium-Term Goals

### 1. ESLint Rules Enhancement

- [ ] Create a script to run ESLint with the no-snake-case-props rule
- [ ] Generate a report of all remaining snake_case property usage
- [ ] Prioritize components with the most snake_case usage

### 2. Documentation Updates

- [ ] Update component documentation to explain camelCase usage
- [ ] Document adapter pattern implementation more thoroughly
- [ ] Create examples for common conversion patterns

### 3. Testing

- [ ] Add tests for adapter functions
- [ ] Verify all API services correctly convert between formats
- [ ] Test components with both snake_case and camelCase data

## Long-Term Goals

### 1. Complete Removal of snake_case

- [ ] Remove hybrid interfaces
- [ ] Update all components to only use camelCase
- [ ] Make the ESLint rule mandatory for all files

### 2. Architectural Improvements

- [ ] Centralize type definitions
- [ ] Standardize API service implementations
- [ ] Consider code generation for API interfaces

## Implementation Tracking

| Task | Owner | Status | Due Date |
|------|-------|--------|----------|
| FileUpload.tsx update | TBD | Completed | TBD |
| ReportGenerator.tsx update | TBD | Completed | TBD |
| Edit Page update | TBD | Completed | TBD |
| ESLint rule enhancement | TBD | Not Started | TBD |
| Documentation updates | TBD | Not Started | TBD |
| Final cleanup | TBD | Not Started | TBD | 