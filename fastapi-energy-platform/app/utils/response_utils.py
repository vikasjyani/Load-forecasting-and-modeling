# fastapi-energy-platform/app/utils/response_utils.py
"""
API response utilities for FastAPI
"""
import logging
import time
import uuid
from datetime import datetime
from typing import Any, Dict, Optional, Union, List, Generator
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from .constants import API_STATUS # Assuming API_STATUS is still relevant

logger = logging.getLogger(__name__)

# --- Pydantic Models for Standardized Responses ---
class StandardResponseMeta(BaseModel):
    request_id: str
    timestamp: datetime
    response_time_ms: Optional[float] = None

class SuccessResponse(BaseModel):
    status: str = API_STATUS['SUCCESS']
    message: Optional[str] = None
    data: Optional[Any] = None
    meta: StandardResponseMeta

class ErrorResponse(BaseModel):
    status: str = API_STATUS['ERROR']
    message: Optional[str] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    details: Optional[Any] = None # For validation errors or more detailed info
    meta: StandardResponseMeta

class PaginatedData(BaseModel):
    items: List[Any]
    page: int
    per_page: int
    total_items: int
    total_pages: int
    has_next: bool
    has_prev: bool
    next_page_num: Optional[int] = None
    prev_page_num: Optional[int] = None

class PaginatedResponse(SuccessResponse):
    data: PaginatedData


# --- Helper to build meta object ---
def _build_meta(request: Optional[Request] = None, start_time: Optional[float] = None) -> StandardResponseMeta:
    request_id = str(uuid.uuid4())[:8]
    response_time_ms = None

    if request and hasattr(request.state, 'request_id'):
        request_id = request.state.request_id
    if request and hasattr(request.state, 'start_time') and request.state.start_time:
        start_time = request.state.start_time # Use start_time from request state if available

    if start_time:
        duration = time.time() - start_time
        response_time_ms = round(duration * 1000, 2)

    return StandardResponseMeta(
        request_id=request_id,
        timestamp=datetime.now(),
        response_time_ms=response_time_ms
    )

# --- Core Response Functions ---
def create_success_response(
    data: Optional[Any] = None,
    message: Optional[str] = "Operation successful",
    status_code: int = 200,
    request: Optional[Request] = None, # Pass request for meta
    start_time: Optional[float] = None # Pass start_time for meta
) -> JSONResponse:
    """Creates a standardized success JSONResponse."""
    content = SuccessResponse(
        message=message,
        data=data,
        meta=_build_meta(request, start_time)
    ).model_dump(exclude_none=True)
    return JSONResponse(status_code=status_code, content=content)

def create_error_response(
    message: str = "An error occurred",
    error: Optional[str] = "Internal Server Error",
    error_type: Optional[str] = "APIError",
    details: Optional[Any] = None,
    status_code: int = 500,
    request: Optional[Request] = None,
    start_time: Optional[float] = None
) -> JSONResponse:
    """Creates a standardized error JSONResponse."""
    logger.error(f"Error Response: {message} - {error_type}: {error} - Details: {details}")
    content = ErrorResponse(
        message=message,
        error=error,
        error_type=error_type,
        details=details,
        meta=_build_meta(request, start_time)
    ).model_dump(exclude_none=True)
    return JSONResponse(status_code=status_code, content=content)

# --- Specific Error Response Conveniences ---
def http_exception_to_error_response(exc: HTTPException, request: Optional[Request] = None) -> JSONResponse:
    """Converts a FastAPI HTTPException to a standardized error response."""
    return create_error_response(
        message=str(exc.detail), # Or a more generic message
        error=str(exc.detail),
        error_type=type(exc).__name__,
        status_code=exc.status_code,
        request=request
    )

def validation_error_response(
    validation_errors: Any, # Typically List[Dict] from Pydantic's .errors()
    message: str = "Validation failed",
    request: Optional[Request] = None
) -> JSONResponse:
    """Creates a 422 Unprocessable Entity error response for validation issues."""
    return create_error_response(
        message=message,
        error="Validation Error",
        error_type="UnprocessableEntity",
        details=validation_errors,
        status_code=422, # HTTP 422 Unprocessable Entity
        request=request
    )

def not_found_response(
    resource_name: str = "Resource",
    request: Optional[Request] = None
) -> JSONResponse:
    """Creates a 404 Not Found error response."""
    return create_error_response(
        message=f"{resource_name} not found.",
        error="Not Found",
        error_type="NotFoundError",
        status_code=404,
        request=request
    )

def unauthorized_response(
    message: str = "Not authenticated or insufficient permissions.",
    request: Optional[Request] = None
) -> JSONResponse:
    """Creates a 401 Unauthorized error response."""
    return create_error_response(
        message=message,
        error="Unauthorized",
        error_type="AuthenticationError", # Or "AuthorizationError"
        status_code=401,
        request=request
    )

def forbidden_response(
    message: str = "You do not have permission to perform this action.",
    request: Optional[Request] = None
) -> JSONResponse:
    """Creates a 403 Forbidden error response."""
    return create_error_response(
        message=message,
        error="Forbidden",
        error_type="AuthorizationError",
        status_code=403,
        request=request
    )


# --- Paginated Response ---
def create_paginated_response(
    items: List[Any],
    page: int,
    per_page: int,
    total_items: int,
    message: Optional[str] = "Items retrieved successfully",
    request: Optional[Request] = None,
    start_time: Optional[float] = None
) -> JSONResponse:
    """Creates a standardized paginated success JSONResponse."""
    total_pages = (total_items + per_page - 1) // per_page if total_items > 0 else 0
    has_next = page < total_pages
    has_prev = page > 1

    paginated_data = PaginatedData(
        items=items,
        page=page,
        per_page=per_page,
        total_items=total_items,
        total_pages=total_pages,
        has_next=has_next,
        has_prev=has_prev,
        next_page_num=page + 1 if has_next else None,
        prev_page_num=page - 1 if has_prev else None
    )
    content = PaginatedResponse(
        message=message,
        data=paginated_data,
        meta=_build_meta(request, start_time)
    ).model_dump(exclude_none=True)
    return JSONResponse(status_code=200, content=content)


# --- Streaming Response ---
async def create_streaming_response(
    generator: Generator[str, None, None], # Assuming generator yields strings (e.g., JSON lines)
    media_type: str = "application/x-ndjson", # Newline Delimited JSON
    headers: Optional[Dict[str, str]] = None,
    request: Optional[Request] = None # For logging or context
) -> StreamingResponse:
    """
    Creates a FastAPI StreamingResponse.
    The generator should handle its own errors and can yield error messages as part of the stream.
    """
    request_id = "unknown"
    if request and hasattr(request.state, 'request_id'):
        request_id = request.state.request_id

    async def stream_wrapper():
        logger.info(f"[{request_id}] Starting streaming response ({media_type})")
        count = 0
        try:
            async for chunk in generator: # If generator is async
                yield chunk
                count +=1
            # If generator is sync:
            # for chunk in generator:
            #    yield chunk
            #    count +=1
        except Exception as e:
            logger.error(f"[{request_id}] Error during streaming: {e}", exc_info=True)
            # Yield a final error message in the stream if the media type allows it (e.g., NDJSON)
            if media_type == "application/x-ndjson":
                error_payload = ErrorResponse(
                    message="Streaming failed due to an internal error.",
                    error=str(e),
                    error_type=type(e).__name__,
                    meta=_build_meta(request) # Meta for the error object itself
                ).model_dump_json(exclude_none=True)
                yield f"{error_payload}\n" # Ensure newline for NDJSON
        finally:
            logger.info(f"[{request_id}] Streaming completed. Chunks yielded: {count}")

    final_headers = {
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Content-Type': media_type, # Ensure Content-Type is set correctly
        'X-Content-Type-Options': 'nosniff', # Good practice
    }
    if headers:
        final_headers.update(headers)

    return StreamingResponse(stream_wrapper(), media_type=media_type, headers=final_headers)


# --- File Information (Example, can be expanded) ---
class FileInfo(BaseModel):
    filename: str
    content_type: Optional[str] = None
    size_bytes: Optional[int] = None

def get_file_info_for_response(
    filename: str,
    content_type: Optional[str] = None,
    size_bytes: Optional[int] = None
) -> FileInfo:
    """Creates a FileInfo model for responses, e.g., after a file upload."""
    import mimetypes
    if not content_type:
        content_type, _ = mimetypes.guess_type(filename)
        if not content_type:
            content_type = "application/octet-stream"
    return FileInfo(filename=filename, content_type=content_type, size_bytes=size_bytes)


print("Defining response utilities for FastAPI... (merged from old_response_utils.py and adapted)")
