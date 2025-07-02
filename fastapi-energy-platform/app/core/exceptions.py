"""
Custom exception classes for the FastAPI Energy Platform application.
"""
from typing import Optional, List, Any, Dict

class AppException(Exception):
    """
    Base class for custom application exceptions.
    Allows associating a status code and custom detail with exceptions.
    """
    def __init__(
        self,
        status_code: int = 500,
        detail: Optional[str] = None,
        loc: Optional[List[str]] = None,
        error_type: Optional[str] = None,
        headers: Optional[Dict[str, Any]] = None,
    ):
        self.status_code = status_code
        self.detail = detail or "An unexpected application error occurred."
        self.loc = loc # For field-specific errors, like Pydantic validation
        self.error_type = error_type or self.__class__.__name__
        self.headers = headers # For custom headers in the HTTP response
        super().__init__(self.detail)

class ProjectNotFoundError(AppException):
    """Exception raised when a project is not found."""
    def __init__(self, project_name: str, detail: Optional[str] = None, loc: Optional[List[str]] = None):
        super().__init__(
            status_code=404,
            detail=detail or f"Project '{project_name}' not found.",
            loc=loc,
            error_type="ProjectNotFound"
        )
        self.project_name = project_name

class ProjectAlreadyExistsError(AppException):
    """Exception raised when trying to create a project that already exists."""
    def __init__(self, project_name: str, detail: Optional[str] = None, loc: Optional[List[str]] = None):
        super().__init__(
            status_code=409, # Conflict
            detail=detail or f"Project '{project_name}' already exists.",
            loc=loc,
            error_type="ProjectAlreadyExists"
        )
        self.project_name = project_name

class FileOperationError(AppException):
    """Exception for errors during file operations (read, write, delete)."""
    def __init__(self, file_path: str, operation: str, detail: Optional[str] = None, loc: Optional[List[str]] = None):
        super().__init__(
            status_code=500,
            detail=detail or f"Error during file operation '{operation}' on '{file_path}'.",
            loc=loc,
            error_type="FileOperationError"
        )
        self.file_path = file_path
        self.operation = operation

class InvalidInputDataError(AppException):
    """Exception for invalid input data provided to a service or operation."""
    def __init__(self, message: str = "Invalid input data provided.", errors: Optional[List[Dict[str, Any]]] = None, loc: Optional[List[str]] = None):
        super().__init__(
            status_code=400, # Bad Request
            detail=message,
            loc=loc,
            error_type="InvalidInputData"
        )
        self.errors = errors # Can hold more detailed validation errors, e.g., from Pydantic

class ConfigurationError(AppException):
    """Exception for application or service configuration issues."""
    def __init__(self, message: str = "Application configuration error.", loc: Optional[List[str]] = None):
        super().__init__(
            status_code=500,
            detail=message,
            loc=loc,
            error_type="ConfigurationError"
        )

class ServiceNotAvailableError(AppException):
    """Exception if a dependent service or resource is not available."""
    def __init__(self, service_name: str, detail: Optional[str] = None, loc: Optional[List[str]] = None):
        super().__init__(
            status_code=503, # Service Unavailable
            detail=detail or f"The service '{service_name}' is currently unavailable.",
            loc=loc,
            error_type="ServiceUnavailable"
        )
        self.service_name = service_name

class JobExecutionError(AppException):
    """Exception for errors during the execution of background jobs."""
    def __init__(self, job_id: str, message: str = "Error during job execution.", loc: Optional[List[str]] = None):
        super().__init__(
            status_code=500,
            detail=f"Error in job '{job_id}': {message}",
            loc=loc,
            error_type="JobExecutionError"
        )
        self.job_id = job_id

class VisualizationError(AppException):
    """Exception for errors during data visualization generation."""
    def __init__(self, message: str = "Error generating visualization.", loc: Optional[List[str]] = None):
        super().__init__(
            status_code=500,
            detail=message,
            loc=loc,
            error_type="VisualizationError"
        )

class ExternalServiceError(AppException):
    """ Exception for errors when interacting with an external service or API """
    def __init__(self, service_name: str, status_code_from_external: Optional[int] = None, detail: Optional[str] = None):
        actual_detail = f"Error interacting with external service '{service_name}'."
        if status_code_from_external:
            actual_detail += f" External status: {status_code_from_external}."
        if detail:
            actual_detail += f" Details: {detail}"

        super().__init__(
            status_code=502, # Bad Gateway, as our app acts as a gateway to the external service
            detail=actual_detail,
            error_type="ExternalServiceError"
        )
        self.service_name = service_name
        self.status_code_from_external = status_code_from_external


# Remove the old print statement
# print("Defining custom exceptions...")
print("Custom application exceptions defined.")
