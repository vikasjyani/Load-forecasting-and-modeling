"""
Pydantic models for administrative tasks and configurations.
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class SystemStatus(BaseModel):
    """
    Represents the overall system status.
    """
    status: str = Field(default="OK", example="OK")
    timestamp: datetime = Field(default_factory=datetime.now)
    active_version: Optional[str] = Field(None, example="1.0.2")
    message: Optional[str] = Field(None, example="System is operating normally.")

class StorageInfo(BaseModel):
    """
    Information about the file storage.
    """
    base_data_path: str = Field(..., example="/mnt/data/energy_platform_projects")
    total_projects: Optional[int] = Field(None, example=15)
    total_disk_space_gb: Optional[float] = Field(None, example=500.0)
    used_disk_space_gb: Optional[float] = Field(None, example=120.5)
    free_disk_space_gb: Optional[float] = Field(None, example=379.5)

class LogEntry(BaseModel):
    """
    Represents a single log entry for admin viewing.
    """
    timestamp: datetime
    level: str = Field(..., example="INFO")
    message: str = Field(..., example="User 'data_processor' initiated a new forecast.")
    source: Optional[str] = Field(None, example="DemandProjectionService")

class RecentLogsResponse(BaseModel):
    """
    Response model for a list of recent log entries.
    """
    logs: List[LogEntry]
    count: int

class AdminActionRequest(BaseModel):
    """
    Generic model for requesting an administrative action.
    """
    action_name: str = Field(..., example="trigger_cleanup_old_results")
    parameters: Optional[Dict[str, Any]] = Field(None, example={"older_than_days": 90})

class AdminActionResponse(BaseModel):
    """
    Response model for an administrative action.
    """
    action_name: str = Field(..., example="trigger_cleanup_old_results")
    status: str = Field(..., example="success")
    message: str
    details: Optional[Dict[str, Any]] = None
