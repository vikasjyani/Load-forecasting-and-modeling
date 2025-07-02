"""
Pydantic models for project management.
A project in this system is primarily a directory with a defined structure,
containing input files, configurations, and results.
"""
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

from app.models.core import FileReference # Re-use for file listings

class ProjectStatusType(str, Enum):
    """
    Enum for project statuses.
    """
    PLANNING = "Planning"
    ACTIVE = "Active"
    ON_HOLD = "On Hold"
    COMPLETED = "Completed"
    ARCHIVED = "Archived"

class ProjectBase(BaseModel):
    """
    Base model for project attributes.
    """
    project_name: str = Field(
        ...,
        min_length=3,
        max_length=100,
        regex="^[a-zA-Z0-9_-]+$", # Basic validation for directory-friendly names
        example="SolarFarmFeasibilityStudy"
    )
    description: Optional[str] = Field(None, max_length=1000, example="Feasibility study for a 10MW solar farm in Nevada.")
    status: ProjectStatusType = Field(default=ProjectStatusType.ACTIVE, example=ProjectStatusType.ACTIVE)
    tags: Optional[List[str]] = Field(default_factory=list, example=["solar", "feasibility", "nevada", "10MW"])
    lead_contact: Optional[str] = Field(None, example="jane.doe@example.com")
    start_date: Optional[date] = Field(None)
    end_date: Optional[date] = Field(None)

class ProjectCreate(BaseModel):
    """
    Model for creating a new project.
    The 'project_name' will be used to create a directory.
    """
    project_name: str = Field(
        ...,
        min_length=3,
        max_length=100,
        regex="^[a-zA-Z0-9_-]+$",
        example="NewWindTurbineAnalysis"
    )
    description: Optional[str] = Field(None, max_length=1000)
    # Initial status can be set, or defaults to a specific one in the service
    status: Optional[ProjectStatusType] = Field(default=ProjectStatusType.PLANNING)
    tags: Optional[List[str]] = Field(default_factory=list)

    @validator('project_name')
    def project_name_alphanumeric(cls, v):
        if not v.isalnum() and '_' not in v and '-' not in v:
            # This regex is a bit more permissive than isalnum to allow hyphens and underscores
            # The main regex on the field handles this, this is more of a double check or alternative.
            pass
        # Potentially check for reserved names or existing names at service layer
        return v

class ProjectUpdateRequest(BaseModel):
    """
    Model for updating an existing project's metadata.
    Project name is typically not updatable as it defines the directory.
    """
    description: Optional[str] = Field(None, max_length=1000)
    status: Optional[ProjectStatusType] = None
    tags: Optional[List[str]] = None
    lead_contact: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    # Custom metadata fields can be added if projects need flexible metadata
    custom_metadata: Optional[Dict[str, Any]] = Field(None, example={"client_id": "CL001", "priority": "High"})


class ProjectStructureNode(BaseModel):
    """
    Represents a node (file or directory) in the project's file tree.
    """
    name: str = Field(..., example="input_data")
    path_relative: str = Field(..., example="input_data") # Relative to project root
    is_directory: bool = Field(..., example=True)
    size_bytes: Optional[int] = Field(None, description="Size in bytes, null for directories or if not calculated")
    last_modified: Optional[datetime] = Field(None)
    children: Optional[List['ProjectStructureNode']] = Field(None, description="For directories, list of child nodes")
    file_type: Optional[str] = Field(None, description="MIME type or extension for files", example="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

ProjectStructureNode.update_forward_refs() # Needed because 'children' refers to ProjectStructureNode itself


class ProjectMetadataFile(BaseModel):
    """
    Represents the content of a potential project_metadata.json file.
    """
    project_name: str # Should match the directory name
    description: Optional[str] = None
    status: ProjectStatusType = ProjectStatusType.ACTIVE
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    last_metadata_update_at: datetime = Field(default_factory=datetime.now)
    custom_fields: Dict[str, Any] = Field(default_factory=dict)
    # List of key input files, configurations, or results for quick access
    # key_files: Optional[List[FileReference]] = None


class ProjectDetailResponse(ProjectBase):
    """
    Comprehensive response model for a single project's details.
    """
    project_name: str # Ensure project_name is always present from Base
    created_at: datetime # Should be read from file system or metadata file
    last_modified_at: datetime # Based on most recent file/dir modification or metadata update
    # file_structure: Optional[List[ProjectStructureNode]] = Field(None, description="Root level files and directories")
    # For a simpler flat list of all files:
    all_files: Optional[List[FileReference]] = Field(None, description="Flat list of all files in the project")
    # Or include the metadata file content if it exists:
    metadata_file_content: Optional[ProjectMetadataFile] = Field(None, description="Content of the project's metadata file, if any")
    total_size_bytes: Optional[int] = Field(None, description="Total disk space used by the project")
    file_count: Optional[int] = Field(None)
    directory_count: Optional[int] = Field(None)

    class Config:
        orm_mode = True # If ever used with an ORM or for easy dict conversion

class ProjectListItemResponse(BaseModel):
    """
    A lighter-weight model for listing multiple projects.
    """
    project_name: str = Field(..., example="SolarFarmFeasibilityStudy")
    description: Optional[str] = Field(None)
    status: ProjectStatusType = Field(default=ProjectStatusType.ACTIVE)
    tags: Optional[List[str]] = Field(default_factory=list)
    created_at: Optional[datetime] = None # From folder creation time or metadata
    last_modified_at: Optional[datetime] = None # From folder/file modification or metadata
    # Add a few key stats if readily available without deep scan
    # total_files: Optional[int] = None
    # total_size_mb: Optional[float] = None

class ProjectCopyRequest(BaseModel):
    """Request to copy an existing project."""
    source_project_name: str = Field(..., example="BaseTemplateProject")
    new_project_name: str = Field(..., example="NewProjectFromBase")
    new_description: Optional[str] = Field(None, example="A new project based on the BaseTemplateProject.")

class ProjectMoveOrRenameRequest(BaseModel):
    """Request to move or rename a project."""
    current_project_name: str = Field(..., example="OldProjectName")
    new_project_name: str = Field(..., example="NewProjectNameOrPath") # Could involve moving to a sub-folder if paths are supported
    # For simplicity, let's assume it's just a rename within the same base projects directory.
    # If moving between different base paths is allowed, that adds complexity.
from datetime import date # ensure date is imported

ProjectListItemResponse.update_forward_refs()
ProjectDetailResponse.update_forward_refs()
ProjectBase.update_forward_refs()
ProjectCreate.update_forward_refs()
ProjectUpdateRequest.update_forward_refs()
ProjectMetadataFile.update_forward_refs()
