"""
OpenAPI documentation utilities.

This module provides functions to enhance the FastAPI OpenAPI documentation
with custom examples, descriptions, and more.
"""

from typing import Dict, Any, Optional, Callable
from fastapi import FastAPI
from config import settings
import copy


def custom_openapi(app: FastAPI, endpoint_examples: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Generate a custom OpenAPI schema with enhanced documentation.
    
    Args:
        app: The FastAPI application instance
        endpoint_examples: Dictionary mapping endpoints to example request and response data
    
    Returns:
        The enhanced OpenAPI schema
    """
    if app.openapi_schema:
        # If we've already generated the schema, return it
        return app.openapi_schema
    
    # Generate the default schema
    openapi_schema = app.openapi()
    
    # Make a deep copy to avoid modifying the original
    openapi_schema = copy.deepcopy(openapi_schema)
    
    # Update metadata
    openapi_schema["info"] = {
        "title": "Insurance Report Generator API",
        "version": "1.0.0",
        "description": (
            "This API provides functionality for generating, editing, and downloading "
            "insurance reports based on document analysis. The API can:\n\n"
            "- Accept document uploads in various formats (PDF, DOCX, images)\n"
            "- Generate structured insurance reports from the uploaded documents\n"
            "- Allow editing and refining of generated reports\n"
            "- Provide download options for the final reports in various formats"
        ),
        "contact": {
            "name": "Technical Support",
            "email": "support@example.com",
            "url": "https://example.com/support"
        },
        "termsOfService": "https://example.com/terms",
        "license": {
            "name": "Proprietary",
            "url": "https://example.com/license"
        },
        "x-logo": {
            "url": "https://example.com/logo.png",
            "altText": "Insurance Report Generator Logo"
        }
    }
    
    # Add security schemes (for future implementation)
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter a valid JWT token"
        }
    }
    
    # Add custom server information
    openapi_schema["servers"] = [
        {
            "url": "{protocol}://{host}",
            "description": "Current server",
            "variables": {
                "protocol": {
                    "enum": ["http", "https"],
                    "default": "https"
                },
                "host": {
                    "default": settings.DOMAIN or "localhost:8000"
                }
            }
        },
        {
            "url": f"https://{settings.DOMAIN}" if settings.DOMAIN else "https://api.example.com",
            "description": "Production server"
        },
        {
            "url": "http://localhost:8000",
            "description": "Local development server"
        }
    ]
    
    # Enhance common error responses
    if "components" in openapi_schema and "schemas" in openapi_schema["components"]:
        # Define a better HTTPValidationError schema
        openapi_schema["components"]["schemas"]["HTTPValidationError"] = {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["error"],
                    "description": "Always 'error' for error responses"
                },
                "code": {
                    "type": "string",
                    "description": "Error code identifier"
                },
                "message": {
                    "type": "string",
                    "description": "Human-readable error message"
                },
                "detail": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "loc": {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                },
                                "description": "Location of the error"
                            },
                            "msg": {
                                "type": "string",
                                "description": "Error message"
                            },
                            "type": {
                                "type": "string",
                                "description": "Error type"
                            }
                        }
                    },
                    "description": "Detailed information about validation errors"
                }
            },
            "required": ["status", "code", "message"]
        }
    
    # Add examples to endpoints
    if endpoint_examples:
        for path, methods in endpoint_examples.items():
            if path in openapi_schema["paths"]:
                for method, examples in methods.items():
                    if method.lower() in openapi_schema["paths"][path]:
                        add_examples_to_endpoint(
                            openapi_schema, 
                            path, 
                            method.lower(), 
                            examples
                        )
    
    # Store and return the enhanced schema
    app.openapi_schema = openapi_schema
    return app.openapi_schema


def add_examples_to_endpoint(
    openapi_schema: Dict[str, Any],
    path: str,
    method: str,
    examples: Dict[str, Any]
) -> None:
    """
    Add example request and response data to a specific endpoint in the OpenAPI schema.
    
    Args:
        openapi_schema: The OpenAPI schema to modify
        path: The endpoint path
        method: The HTTP method
        examples: Dictionary containing request and response examples
    """
    # Verify the path and method exist in the schema
    if path not in openapi_schema["paths"] or method not in openapi_schema["paths"][path]:
        return
    
    # Add request body examples
    if "requestBody" in examples and "requestBody" in openapi_schema["paths"][path][method]:
        if "content" in openapi_schema["paths"][path][method]["requestBody"]:
            for content_type in openapi_schema["paths"][path][method]["requestBody"]["content"]:
                if "application/json" in content_type:
                    # Add examples to request body
                    openapi_schema["paths"][path][method]["requestBody"]["content"][content_type]["examples"] = (
                        examples["requestBody"]
                    )
    
    # Add response examples
    if "responses" in examples:
        for status_code, response_examples in examples["responses"].items():
            if status_code in openapi_schema["paths"][path][method]["responses"]:
                for content_type in openapi_schema["paths"][path][method]["responses"][status_code].get("content", {}):
                    if "application/json" in content_type:
                        # Add examples to responses
                        openapi_schema["paths"][path][method]["responses"][status_code]["content"][content_type]["examples"] = (
                            response_examples
                        ) 