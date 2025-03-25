# Backend Architecture Documentation

## Recent Improvements to Import Structure

### Circular Dependency Resolution

One of the major improvements made to the codebase was the resolution of circular dependencies between key modules. 
Circular dependencies caused issues when deploying to Render and created challenges when trying to fix relative 
imports beyond the top-level package.

#### Problem

The codebase had circular dependencies in the following pattern:

```
docx_formatter.py → utils/resource_manager.py → utils/__init__.py → utils/error_handler.py → api/schemas.py → api/__init__.py → api/agent_loop.py → utils/error_handler.py
```

This was causing the "attempted relative import beyond top-level package" error in deployment environments, and made
it impossible to fix all relative imports at once.

#### Solution Implemented

We implemented the following changes to resolve the circular dependencies:

1. Created a new `core` package with shared types in `core/types.py`:
   - Extracted common error types to prevent circular dependencies
   - Defined core types like `ErrorSeverity` and `ErrorResponse` that are used across modules

2. Refactored `utils/error_handler.py`:
   - Removed dependency on API schemas by using core types
   - Updated error handling code to use the new structure

3. Modified other modules to use the new `core.types` module:
   - Updated `services/docx_formatter.py` to import from core types 
   - Broke the circular dependency chain by removing cross-module imports

4. Verified the solution with a dedicated test script:
   - Created `scripts/test_specific_imports.py` to test import orders
   - Confirmed modules can now be imported in any order without circular dependencies

### Key Architecture Principles

Going forward, the application follows these principles to prevent circular dependencies:

1. **Layered Architecture**:
   - `core`: Contains shared types and constants used across the application
   - `utils`: Provides utility functions that depend only on core
   - `services`: Implements business logic using utils and core
   - `api`: Exposes endpoints that use services, utils, and core

2. **Import Rules**:
   - Lower layers should not import from higher layers
   - Core types should be imported from core.types
   - Error handling should use core error types
   - Avoid importing entire modules when only specific elements are needed

### Recommended Practices

1. When adding new features:
   - Consider which layer the code belongs to
   - Use absolute imports rather than relative imports
   - Avoid creating new dependencies that could lead to cycles

2. When encountering import errors:
   - Check if a dependency should be moved to the core module
   - Consider if the design needs to be refactored to maintain the layered architecture
   - Use dependency injection when appropriate

3. Testing imports:
   - Use the `scripts/test_specific_imports.py` script as a template for testing imports
   - Verify that new modules maintain the architectural standards

## Next Steps for Codebase Improvement

The following tasks are recommended for continued improvement:

1. Standardize all imports to use absolute imports
2. Create automated tests to detect potential circular dependencies
3. Refactor remaining modules to conform to the layered architecture
4. Document import patterns and architectural decisions for new developers

By following these guidelines, the codebase will remain maintainable and avoid deployment issues related to imports and module dependencies. 