# Changelog

## [Unreleased]

### Added
- Standardized API Response format across all endpoints using the new `APIResponse` model
- Created documentation for the standardized API response format at `backend/docs/api_response_standard.md`
- Added automatic response wrapping with `api_error_handler` decorator for consistent error handling

### Changed
- Updated validation exception handler to use the standard response format
- Refactored `/api/format/preview` endpoint to use standardized response format
- Updated `/api/download/cleanup/{report_id}` endpoint to use standardized response format
- Updated `/api/upload/documents` endpoint to use standardized response format with the `api_error_handler` decorator
- Improved error handling consistency across API endpoints
- Enhanced error logging using the logger instead of print statements

### Fixed
- Inconsistent API response structures across different endpoints
- Improved error messages with appropriate error codes 