from pydantic import BaseModel, Field
from typing import Generic, TypeVar, Optional, List, Any

T = TypeVar('T')

class Message(BaseModel):
    """
    A simple message response.
    """
    message: str = Field(..., example="Operation successful")

class DataResponse(BaseModel, Generic[T]):
    """
    A generic data response model.
    """
    message: Optional[str] = Field(None, example="Data retrieved successfully")
    data: Optional[T] = None

class ErrorDetail(BaseModel):
    """
    Represents a single error detail.
    """
    loc: Optional[List[str]] = Field(None, title="Location", example=["body", "field_name"])
    msg: str = Field(..., title="Message", example="Invalid input.")
    type: Optional[str] = Field(None, title="Error Type", example="value_error")

class ErrorResponse(BaseModel):
    """
    A standard error response model.
    """
    detail: List[ErrorDetail] = Field(..., title="Error Details")

class JobStatusResponse(BaseModel):
    """
    Response model for job status.
    """
    job_id: str = Field(..., example="a1b2c3d4-e5f6-7890-1234-567890abcdef")
    status: str = Field(..., example="RUNNING")
    progress: Optional[int] = Field(None, ge=0, le=100, example=50)
    message: Optional[str] = Field(None, example="Processing sector 'Industrial'...")
    result_url: Optional[str] = Field(None, example="/api/v1/jobs/a1b2c3d4-e5f6-7890-1234-567890abcdef/result")
    detail: Optional[Any] = Field(None, description="Detailed information or result preview if available.")

class FileUploadResponse(BaseModel):
    """
    Response model for successful file uploads.
    """
    filename: str = Field(..., example="input_data.xlsx")
    content_type: Optional[str] = Field(None, example="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    size_bytes: Optional[int] = Field(None, example=102400)
    message: str = Field(default="File uploaded successfully.", example="File uploaded successfully.")
    file_id: Optional[str] = Field(None, example="unique_file_id_on_server") # If server assigns an ID
    additional_info: Optional[Dict[str, Any]] = Field(None, description="Any additional info about the uploaded file.")

class TaskAcceptedResponse(BaseModel):
    """
    Response for when a task is accepted for background processing.
    """
    job_id: str = Field(..., example="a1b2c3d4-e5f6-7890-1234-567890abcdef")
    message: str = Field(default="Task accepted for processing.", example="Task accepted for processing.")
    status_endpoint: Optional[str] = Field(None, example="/api/v1/jobs/a1b2c3d4-e5f6-7890-1234-567890abcdef/status")
    result_endpoint: Optional[str] = Field(None, example="/api/v1/jobs/a1b2c3d4-e5f6-7890-1234-567890abcdef/result")

class PaginatedResponse(BaseModel, Generic[T]):
    """
    A generic paginated response model.
    """
    items: List[T]
    total_items: int
    page: int
    size: int
    total_pages: int
    message: Optional[str] = None
