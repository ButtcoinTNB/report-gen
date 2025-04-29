"""
Examples for the OpenAPI documentation.

This module contains example request and response data for API endpoints,
which are used to enhance the OpenAPI documentation.
"""

import datetime
import uuid
from typing import Any, Dict

# Generate examples for the generate report endpoint
GENERATE_REPORT_EXAMPLES = {
    "requestBody": {
        "Example request": {
            "summary": "Basic report generation request",
            "value": {
                "document_ids": [str(uuid.uuid4()), str(uuid.uuid4())],
                "additional_info": "Include analysis of water damage in bathroom",
                "template_id": str(uuid.uuid4()),
            },
        },
        "Minimal request": {
            "summary": "Minimal report generation request",
            "value": {"document_ids": [str(uuid.uuid4())]},
        },
    },
    "responses": {
        "200": {
            "Successful response": {
                "summary": "Report successfully generated",
                "value": {
                    "status": "success",
                    "data": {"report_id": str(uuid.uuid4())},
                },
            }
        },
        "404": {
            "Document not found": {
                "summary": "Document not found error",
                "value": {
                    "status": "error",
                    "code": "NOT_FOUND",
                    "message": "One or more documents not found",
                    "details": {
                        "resource_type": "document",
                        "resource_id": str(uuid.uuid4()),
                    },
                },
            }
        },
        "500": {
            "AI service error": {
                "summary": "AI service error",
                "value": {
                    "status": "error",
                    "code": "AI_SERVICE_ERROR",
                    "message": "Error communicating with AI service",
                    "details": {
                        "error_type": "AIConnectionError",
                        "original_error": "Failed to connect to AI service: timeout",
                    },
                },
            }
        },
    },
}

# Examples for the upload endpoint
UPLOAD_EXAMPLES = {
    "responses": {
        "200": {
            "Successful upload": {
                "summary": "Files successfully uploaded",
                "value": {
                    "status": "success",
                    "data": {
                        "files": [
                            {
                                "file_id": str(uuid.uuid4()),
                                "filename": "example.pdf",
                                "file_size": 1024567,
                                "mime_type": "application/pdf",
                            }
                        ],
                        "report_id": str(uuid.uuid4()),
                    },
                },
            }
        },
        "413": {
            "File too large": {
                "summary": "File exceeds size limit",
                "value": {
                    "status": "error",
                    "code": "VALIDATION_ERROR",
                    "message": "File too large. The maximum allowed size is 1GB.",
                    "details": {"file_size": 1073741825, "max_size": 1073741824},
                },
            }
        },
        "422": {
            "Validation error": {
                "summary": "Validation error",
                "value": {
                    "status": "error",
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid file type",
                    "details": {
                        "file_extension": "exe",
                        "allowed_extensions": ["pdf", "docx", "jpg", "png"],
                    },
                },
            }
        },
    }
}

# Examples for the download endpoint
DOWNLOAD_EXAMPLES = {
    "responses": {
        "200": {
            "Download info": {
                "summary": "Download information",
                "value": {
                    "status": "success",
                    "data": {
                        "file_path": "/path/to/report.docx",
                        "download_url": "/api/download/file/123456",
                    },
                },
            }
        },
        "404": {
            "Report not found": {
                "summary": "Report not found error",
                "value": {
                    "status": "error",
                    "code": "NOT_FOUND",
                    "message": "Report not found",
                    "details": {
                        "resource_type": "report",
                        "resource_id": str(uuid.uuid4()),
                    },
                },
            }
        },
    }
}

# Examples for the refine endpoint
REFINE_EXAMPLES = {
    "requestBody": {
        "Example refinement": {
            "summary": "Refine report request",
            "value": {
                "instructions": "Expand on the water damage section and add more detail about estimated repair costs."
            },
        }
    },
    "responses": {
        "200": {
            "Successful refinement": {
                "summary": "Report successfully refined",
                "value": {
                    "status": "success",
                    "data": {
                        "report_id": str(uuid.uuid4()),
                        "content": "The refined report content with expanded sections...",
                        "updated_at": datetime.datetime.now().isoformat(),
                    },
                },
            }
        },
        "503": {
            "AI service unavailable": {
                "summary": "AI service unavailable",
                "value": {
                    "status": "error",
                    "code": "SERVICE_UNAVAILABLE",
                    "message": "AI service is currently unavailable",
                    "details": {"retry_after": 60, "service": "OpenAI API"},
                },
            }
        },
    },
}

# Common error response examples that can be shared across endpoints
COMMON_ERROR_EXAMPLES = {
    "401": {
        "Unauthorized": {
            "summary": "Authentication required",
            "value": {
                "status": "error",
                "code": "UNAUTHORIZED",
                "message": "Authentication required to access this resource",
            },
        }
    },
    "403": {
        "Forbidden": {
            "summary": "Permission denied",
            "value": {
                "status": "error",
                "code": "FORBIDDEN",
                "message": "You don't have permission to access this resource",
                "details": {"required_role": "admin"},
            },
        }
    },
    "429": {
        "Too Many Requests": {
            "summary": "Rate limit exceeded",
            "value": {
                "status": "error",
                "code": "TOO_MANY_REQUESTS",
                "message": "Rate limit exceeded. Please try again later.",
                "details": {"retry_after": 30, "limit": 100, "period": "1 hour"},
            },
        }
    },
    "500": {
        "Internal Server Error": {
            "summary": "Generic server error",
            "value": {
                "status": "error",
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
            },
        }
    },
}

# Mapping of endpoints to examples
ENDPOINT_EXAMPLES: Dict[str, Dict[str, Any]] = {
    "/api/agent-loop/generate-report": {"post": GENERATE_REPORT_EXAMPLES},
    "/api/uploads/initialize": {"post": UPLOAD_EXAMPLES},
    "/api/download/{report_id}": {"get": DOWNLOAD_EXAMPLES},
    "/api/edit/refine/{report_id}": {"post": REFINE_EXAMPLES},
}
