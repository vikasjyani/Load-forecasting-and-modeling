# fastapi-energy-platform/app/utils/error_handlers.py
"""
Error handling utilities for FastAPI, including custom exceptions and handlers.
"""
import logging
import traceback
import time
from functools import wraps
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from typing import Callable, Dict, Any, List, Optional
from collections import defaultdict, deque
from datetime import datetime

# Attempt to import response_utils for structured responses if they are used by handlers.
# If response_utils is not yet adapted or used, these imports can be conditional or removed.
# try:
#     from app.utils.response_utils import create_error_response # Assuming this function exists and is adapted
# except ImportError:
# Fallback or placeholder if response_utils is not ready
def _internal_create_error_response(message: str, error_type: Optional[str] = None,
                                    detail: Optional[Any] = None, status_code: int = 500) -> JSONResponse:
    # Basic JSONResponse if the custom one isn't available
    return JSONResponse(status_code=status_code, content={"error_type": error_type or "Error", "message": message, "detail": detail})


logger = logging.getLogger(__name__)

# ========== Custom Exception Classes (Adapted for FastAPI by inheriting HTTPException) ==========

class BaseAPIException(HTTPException):
    """Base class for custom API exceptions for FastAPI."""
    def __init__(self, status_code: int, detail: Any = None, error_type: Optional[str] = None, headers: Optional[Dict[str, str]] = None):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.error_type = error_type or self.__class__.__name__

class ValidationError(BaseAPIException):
    def __init__(self, message: str, field: Optional[str] = None, value: Optional[Any] = None, status_code: int = 422): # 422 for validation
        detail_payload = {"message": message, "type": "ValidationError"}
        if field: detail_payload["field"] = field
        if value is not None: detail_payload["value"] = str(value) # Ensure serializable
        super().__init__(status_code=status_code, detail=detail_payload, error_type="ValidationError")

class BusinessLogicError(BaseAPIException):
    def __init__(self, message: str, error_code: Optional[str] = None, context: Optional[Dict] = None, status_code: int = 400): # 400 for business logic errors
        detail_payload = {"message": message, "type": "BusinessLogicError"}
        if error_code: detail_payload["error_code"] = error_code
        if context: detail_payload["context"] = context # Ensure context is serializable
        super().__init__(status_code=status_code, detail=detail_payload, error_type="BusinessLogicError")

class ResourceNotFoundError(BaseAPIException):
    def __init__(self, resource_type: str, resource_id: Optional[str] = None, message: Optional[str] = None, status_code: int = 404):
        final_message = message or f"{resource_type} not found"
        if resource_id: final_message += f": ID '{resource_id}'"
        detail_payload = {"message": final_message, "type": "ResourceNotFoundError", "resource_type": resource_type}
        if resource_id: detail_payload["resource_id"] = resource_id
        super().__init__(status_code=status_code, detail=detail_payload, error_type="ResourceNotFoundError")

class ConfigurationError(BaseAPIException): # Typically results in a 500
    def __init__(self, message: str, config_key: Optional[str] = None, status_code: int = 500):
        detail_payload = {"message": message, "type": "ConfigurationError"}
        if config_key: detail_payload["config_key"] = config_key
        super().__init__(status_code=status_code, detail=detail_payload, error_type="ConfigurationError")

class ProcessingError(BaseAPIException): # Typically results in a 500 or 400/422 if input related
    def __init__(self, message: str, operation: Optional[str] = None, data_info: Optional[Dict] = None, status_code: int = 500):
        detail_payload = {"message": message, "type": "ProcessingError"}
        if operation: detail_payload["operation"] = operation
        if data_info: detail_payload["data_info"] = data_info
        super().__init__(status_code=status_code, detail=detail_payload, error_type="ProcessingError")


# ========== FastAPI Exception Handlers ==========
# These should be registered with the FastAPI app instance.
# e.g., app.add_exception_handler(ValidationError, validation_exception_handler_func)

async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom handler for FastAPI's own HTTPException and our BaseAPIException."""
    logger.info(f"HTTPException ({exc.status_code}) for {request.method} {request.url.path}: {exc.detail}")
    # If detail is already a dict (as in our BaseAPIException), use it, else wrap it.
    content_detail = exc.detail if isinstance(exc.detail, dict) else {"message": exc.detail}
    content_detail["error_type"] = getattr(exc, 'error_type', type(exc).__name__)

    return JSONResponse(
        status_code=exc.status_code,
        content=content_detail,
        headers=getattr(exc, 'headers', None) # Use getattr for headers as well
    )

async def general_exception_handler(request: Request, exc: Exception):
    """Catch-all for unhandled exceptions."""
    request_id = getattr(request.state, 'request_id', 'N/A') # Assuming request_id middleware
    logger.error(
        f"Unhandled Exception for Request ID {request_id} ({request.method} {request.url.path}): {type(exc).__name__} - {str(exc)}",
        exc_info=True # Include traceback in logs
    )
    return JSONResponse( # Using the fallback response creator
        status_code=500,
        content={
            "error_type": "InternalServerError",
            "detail": {"message": "An unexpected internal server error occurred."},
            "request_id": request_id
        }
    )


# ========== Error Statistics and Tracking (Adapted from original) ==========
class ErrorTracker:
    def __init__(self, max_history: int = 100): # Reduced history for simplicity
        self.error_history = deque(maxlen=max_history)
        self.error_counts = defaultdict(int) # Key: error_type:source_identifier

    def record_error(self, error_type: str, source_identifier: str, # e.g., "router_name.endpoint_name"
                     message: str, request: Optional[Request] = None, exc_info=False):
        timestamp = time.time()
        log_entry = {
            'timestamp': timestamp,
            'datetime_iso': datetime.fromtimestamp(timestamp).isoformat(),
            'error_type': error_type,
            'source_identifier': source_identifier,
            'message': message,
            'request_id': getattr(request.state, 'request_id', None) if request and hasattr(request.state, 'request_id') else None,
            'request_path': str(request.url.path) if request else None,
            'client_host': request.client.host if request and request.client else None,
        }
        if exc_info:
            log_entry['traceback'] = traceback.format_exc(limit=5)

        self.error_history.append(log_entry)
        self.error_counts[f"{error_type}:{source_identifier}"] += 1
        logger.debug(f"Error recorded by tracker: {error_type} at {source_identifier}")

    def get_error_stats(self, hours: int = 24) -> Dict[str, Any]:
        cutoff_time = time.time() - (hours * 3600)
        recent_errors = [err for err in self.error_history if err['timestamp'] > cutoff_time]
        stats: Dict[str, Any] = {"total_errors": len(recent_errors), "errors_by_type": defaultdict(int), "errors_by_source": defaultdict(int)}
        for err in recent_errors:
            stats["errors_by_type"][err['error_type']] += 1
            stats["errors_by_source"][err['source_identifier']] += 1
        stats["errors_by_type"] = dict(stats["errors_by_type"])
        stats["errors_by_source"] = dict(stats["errors_by_source"])
        return stats

error_tracker = ErrorTracker()


# ========== Decorator for Service Layer Error Handling (Optional) ==========
def handle_service_errors(source_identifier: str):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except BaseAPIException: raise
            except (ValueError, TypeError) as py_exc:
                logger.warning(f"Service input/type error in {source_identifier}.{func.__name__}: {type(py_exc).__name__} - {str(py_exc)}")
                error_tracker.record_error(type(py_exc).__name__, f"{source_identifier}.{func.__name__}", str(py_exc))
                raise BusinessLogicError(message=f"Invalid data or operation in {source_identifier}: {str(py_exc)}") from py_exc
            except FileNotFoundError as fnf_exc:
                logger.warning(f"Service resource not found in {source_identifier}.{func.__name__}: {str(fnf_exc)}")
                error_tracker.record_error(type(fnf_exc).__name__, f"{source_identifier}.{func.__name__}", str(fnf_exc))
                raise ResourceNotFoundError(resource_type="File", message=str(fnf_exc)) from fnf_exc
            except Exception as unhandled_exc:
                logger.error(f"Unexpected service error in {source_identifier}.{func.__name__}: {type(unhandled_exc).__name__} - {str(unhandled_exc)}", exc_info=True)
                error_tracker.record_error("UnexpectedServiceError", f"{source_identifier}.{func.__name__}", str(unhandled_exc), exc_info=True)
                raise ProcessingError(message=f"An internal error occurred in {source_identifier}.") from unhandled_exc
        return wrapper
    return decorator

logger.info("Error handlers (custom exceptions, FastAPI handlers, tracker, decorator) defined.")
print("Error handlers (custom exceptions, FastAPI handlers, tracker, decorator) defined.")
