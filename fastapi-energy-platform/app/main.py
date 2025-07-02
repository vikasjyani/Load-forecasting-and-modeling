from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import time
import logging
import uuid
from datetime import datetime

# Configure logging first
from app.core.logging import setup_logging
setup_logging() # Apply logging configuration immediately

# Application-specific imports
from app.config import settings # Import the Pydantic settings
from app.api.router import api_router
from app.core.exceptions import (
    AppException,
    ProjectNotFoundError,
    ProjectAlreadyExistsError,
    FileOperationError,
    InvalidInputDataError,
    ConfigurationError,
    ServiceNotAvailableError,
    JobExecutionError,
    VisualizationError,
    ExternalServiceError
)
from app.models.common import ErrorResponse, ErrorDetail

logger = logging.getLogger(settings.APP_NAME) # Use app name from settings for logger

# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=settings.APP_DESCRIPTION,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    # Add lifespan context manager if needed for startup/shutdown events
    # lifespan=lifespan
)

# === Middleware ===

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS, # Use origins from settings
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request ID and Process Time Middleware
@app.middleware("http")
async def add_request_id_process_time(request: Request, call_next):
    request.state.request_id = str(uuid.uuid4())
    start_time = time.time()

    response = await call_next(request)

    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.4f}"
    response.headers["X-Request-ID"] = request.state.request_id

    # Log request details
    log_message = (
        f"RID: {request.state.request_id} "
        f"Path: {request.url.path} "
        f"Method: {request.method} "
        f"Status: {response.status_code} "
        f"Time: {process_time:.4f}s"
    )
    # Include query params if any
    if request.url.query:
        log_message += f" Query: {request.url.query}"

    logger.info(log_message)
    return response

# === Exception Handlers ===

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """Handles custom application exceptions (those inheriting from AppException)."""
    logger.error(f"RID: {getattr(request.state, 'request_id', 'N/A')} - App Exception: {exc.detail}", exc_info=True if exc.status_code == 500 else False)
    error_detail = ErrorDetail(msg=exc.detail, type=exc.error_type, loc=exc.loc)
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(detail=[error_detail]).model_dump(exclude_none=True),
        headers=exc.headers,
    )

@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handles FastAPI's RequestValidationError (Pydantic validation errors)."""
    error_details = []
    for error in exc.errors():
        error_details.append(
            ErrorDetail(
                loc=list(error["loc"]) if error["loc"] else None, # Ensure loc is a list or None
                msg=error["msg"],
                type=error["type"]
            )
        )
    logger.warning(f"RID: {getattr(request.state, 'request_id', 'N/A')} - Validation Error: {exc.errors()}")
    return JSONResponse(
        status_code=422, # Unprocessable Entity
        content=ErrorResponse(detail=error_details).model_dump(exclude_none=True),
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handles FastAPI's built-in HTTPException."""
    logger.error(f"RID: {getattr(request.state, 'request_id', 'N/A')} - HTTP Exception: Status {exc.status_code}, Detail: {exc.detail}", exc_info=True if exc.status_code >= 500 else False)
    error_detail = ErrorDetail(msg=exc.detail, type=exc.__class__.__name__) # Use exception class name as type
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(detail=[error_detail]).model_dump(exclude_none=True),
        headers=exc.headers,
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handles any other unhandled Python exceptions."""
    request_id = getattr(request.state, 'request_id', 'N/A')
    logger.critical(f"RID: {request_id} - Unhandled Exception: {exc}", exc_info=True)
    error_detail = ErrorDetail(
        msg="An unexpected internal server error occurred.",
        type=exc.__class__.__name__
    )
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(detail=[error_detail]).model_dump(exclude_none=True),
    )

# === Routers ===
app.include_router(api_router, prefix=settings.API_V1_PREFIX) # Use prefix from settings

# === Root and Health Endpoints ===
@app.get("/", summary="Root Endpoint", tags=["General"], include_in_schema=True)
async def root():
    """Provides basic information about the API."""
    return {
        "application": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": settings.APP_DESCRIPTION,
        "documentation_urls": [app.docs_url, app.redoc_url],
        "api_prefix": settings.API_V1_PREFIX
    }

@app.get("/health", summary="Health Check", tags=["General"])
async def health_check():
    """Performs a basic health check of the application."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat(), "application_version": settings.APP_VERSION}


# Initial log message to confirm settings are loaded
logger.info(f"'{settings.APP_NAME}' version '{settings.APP_VERSION}' is starting up...")
logger.info(f"Log level set to: {settings.LOG_LEVEL}")
logger.info(f"Project data root: {settings.PROJECT_DATA_ROOT}")
logger.info(f"Allowed CORS origins: {settings.ALLOWED_ORIGINS}")

# Ensure the old print statement is removed
# print("FastAPI app (app/main.py) created/updated with basic structure, middleware, and router inclusion.")
print(f"FastAPI app '{settings.APP_NAME}' initialized with custom error handlers and configuration.")
