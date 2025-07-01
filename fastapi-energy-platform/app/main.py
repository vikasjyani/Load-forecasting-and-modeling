from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware # For CORS
import time
import logging

# Assuming router and error handlers will be correctly imported
from app.api.router import api_router
# from app.core.config import settings # If you have a Pydantic settings model
from app.utils.error_handlers import ( # Import custom exceptions and handlers
    BaseAPIException,
    # http_exception_handler, # Generic FastAPI HTTPException handler
    # general_exception_handler, # Catch-all
    # Specific custom exception handlers if defined and registered separately
    validation_error_handler, ValidationError,
    resource_not_found_error_handler, ResourceNotFoundError,
    business_logic_error_handler, BusinessLogicError,
    # ... any other custom handlers
)

logger = logging.getLogger(__name__)

# Initialize FastAPI app
# Title and version can come from settings
app = FastAPI(
    title="FastAPI Energy Platform",
    version="1.0.0",
    description="Backend API for the Energy Platform, migrated from Flask to FastAPI.",
    # openapi_url=f"{settings.API_V1_STR}/openapi.json" # Example if using settings
    openapi_url="/api/v1/openapi.json", # Default if not using settings for this
    # Add lifespan context manager if needed for startup/shutdown events
    # lifespan=lifespan
)

# === Middleware ===

# CORS Middleware
# Adjust origins as needed for your frontend URL
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"], # Add your frontend origin(s)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import uuid # Moved import to top
from datetime import datetime # Added for health check timestamp

# Request ID and Process Time Middleware (Example)
@app.middleware("http")
async def add_request_id_process_time(request: Request, call_next):
    request.state.request_id = str(uuid.uuid4())
    start_time = time.time()

    response = await call_next(request)

    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.4f}" # Use f-string
    response.headers["X-Request-ID"] = request.state.request_id
    logger.info(
        f"RID: {request.state.request_id} Path: {request.url.path} Method: {request.method} Status: {response.status_code} Time: {process_time:.4f}s"
    )
    return response

# === Exception Handlers ===
# Register your custom exception handlers and generic ones.
# FastAPI automatically handles its own HTTPException and Pydantic's RequestValidationError.
# You might want to customize RequestValidationError handling too.

# Using the more specific http_exception_handler from error_handlers.py for BaseAPIException
# and FastAPI's built-in HTTPException, if defined and registered.
# Otherwise, FastAPI handles HTTPException by default.
# For other custom exceptions:
if 'validation_error_handler' in globals() and 'ValidationError' in globals(): # Check if defined (might be placeholder)
    app.add_exception_handler(ValidationError, validation_error_handler)
if 'resource_not_found_error_handler' in globals() and 'ResourceNotFoundError' in globals():
    app.add_exception_handler(ResourceNotFoundError, resource_not_found_error_handler)
if 'business_logic_error_handler' in globals() and 'BusinessLogicError' in globals():
    app.add_exception_handler(BusinessLogicError, business_logic_error_handler)

# It's good practice to have a generic handler for BaseAPIException if specific ones are not caught
# And a very generic one for Python's Exception (already defined as general_exception_handler)
# from app.utils.error_handlers import base_api_exception_handler, general_exception_handler
# app.add_exception_handler(BaseAPIException, base_api_exception_handler)
# app.add_exception_handler(Exception, general_exception_handler)


# === Routers ===
# Include the main API router (which then includes v1, v2, etc.)
app.include_router(api_router, prefix="/api") # Or settings.API_V1_STR

# Root endpoint
@app.get("/", summary="Root Endpoint", tags=["General"], include_in_schema=False) # Exclude from OpenAPI docs if it's just informational
async def root():
    """Provides basic information about the API."""
    return {
        "message": "Welcome to the FastAPI Energy Platform API!",
        "documentation_urls": [app.docs_url, app.redoc_url], # Use app's configured doc URLs
        "api_version_prefix": "/api" # Or from settings
    }

# Health check endpoint
@app.get("/health", summary="Health Check", tags=["General"])
async def health_check():
    """Performs a basic health check of the application."""
    # In a real app, this might check DB connection, external services, etc.
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


# Example: How settings might be loaded if you use Pydantic's BaseSettings
# from app.core.config import settings # Assuming settings is your loaded Settings object
# logger.info(f"API running with title: {settings.PROJECT_NAME}")

# For development: Uvicorn server startup (if running this file directly)
# This is usually removed for production builds where Uvicorn is run externally.
# if __name__ == "__main__":
#     import uvicorn
#     # This is for direct execution. `CMD ["uvicorn", "app.main:app"...]` in Dockerfile is preferred for containers.
#     uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")

print("FastAPI app (app/main.py) created/updated with basic structure, middleware, and router inclusion.")
