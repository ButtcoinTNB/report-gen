# Dependency Analysis

## Circular Import Chain

The main circular dependency chain identified:

```
backend/services/docx_formatter.py 
  → imports from utils.error_handler (handle_exception, logger)
  → imports from utils.resource_manager (resource_manager)

backend/utils/error_handler.py
  → imports from api.schemas (APIResponse)

backend/api/agent_loop.py
  → imports from utils.error_handler (ErrorResponse, raise_error)
  → imports from services.docx_formatter (generate_docx_async, get_document_metrics)
  → imports from utils.event_emitter (EventEmitter)
```

The cycle is: 
- `docx_formatter.py` imports `error_handler.py`
- `error_handler.py` imports `api.schemas`
- `api/agent_loop.py` imports both `error_handler.py` and `docx_formatter.py`

## Dependency Details

### backend/services/docx_formatter.py
- Imports `utils.resource_manager.resource_manager`
- Imports `utils.error_handler.handle_exception, logger`
- Imports `utils.metrics.MetricsCollector`
- Imports `.docx_service.docx_service`

### backend/utils/error_handler.py
- Imports `api.schemas.APIResponse`
- Imports `utils.exceptions`

### backend/api/agent_loop.py
- Imports `utils.event_emitter.EventEmitter`
- Imports `utils.metrics.MetricsCollector`
- Imports `utils.agents_loop.AIAgentLoop`
- Imports `utils.error_handler.ErrorResponse, raise_error`
- Imports `utils.security.validate_user`
- Imports `services.docx_formatter.generate_docx_async, get_document_metrics`
- Imports `main.app`

### backend/utils/resource_manager.py
- No imports from other custom modules
- Is imported by `docx_formatter.py`

### backend/utils/event_emitter.py
- No imports from other custom modules
- Is imported by `agent_loop.py`

## Problematic Patterns
1. **Cross-Domain Dependencies**: Services are importing from utils and API layers, while API is importing from services.
2. **Utility Modules with External Dependencies**: `error_handler.py` depends on `api.schemas` which violates separation of concerns.
3. **Implicit Module Initialization**: Modules being imported for initialization side effects.

## Next Steps
1. Extract core error types into a separate module
2. Break circular dependencies by restructuring imports
3. Standardize import approach (use absolute imports)
4. Refactor initialization patterns to avoid circular dependencies 