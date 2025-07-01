# fastapi-energy-platform/app/api/v1/projects.py
"""
Project Management API Endpoints for FastAPI.
Handles creation, loading, validation, and management of projects.
"""
import logging
import os
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Form, Body, Request, Query
from pydantic import BaseModel, Field, validator

# Assuming utilities are adapted and available.
# These imports need to be verified and adapted based on the final location and content of these utils.
from app.utils.helpers import create_project_structure, validate_project_structure, copy_missing_templates, safe_filename
# from app.utils.constants import ERROR_MESSAGES # If used for standardized messages
# from app.utils.error_handlers import ResourceNotFoundError, ProcessingError, ValidationError # If using these custom exceptions

# Placeholder for session/user management - FastAPI typically uses Depends for this.
# For now, assuming a way to get user_id, or using a default.
def get_current_user_id(request: Request) -> str:
    # In a real app, this would come from an auth dependency that inspects request.
    # Example: user = await get_current_active_user(request)
    # return user.id
    return "default_user" # Placeholder

# Placeholder for application settings/config
# In FastAPI, this is often managed via a Pydantic Settings model injected as a dependency.
class AppSettings: # Placeholder
    UPLOAD_FOLDER: Path = Path("user_projects_data") # This should be configurable
    TEMPLATE_FOLDER: Path = Path("app_templates")   # This should be configurable

    def __init__(self):
        # Ensure base UPLOAD_FOLDER exists
        self.UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
        (self.UPLOAD_FOLDER / "recent_projects").mkdir(parents=True, exist_ok=True)
        self.TEMPLATE_FOLDER.mkdir(parents=True, exist_ok=True)


def get_app_settings(): # Dependency
    return AppSettings()


logger = logging.getLogger(__name__)
router = APIRouter()

# --- Pydantic Models ---
class ProjectPathPayload(BaseModel):
    projectPath: str # Path to the project

class CreateProjectPayload(BaseModel):
    projectName: str = Field(..., min_length=1)
    projectLocation: str = Field(default="", description="Base location for the project, can be relative to a root or absolute.")

class RecentProjectEntry(BaseModel):
    name: str
    path: str
    last_opened: datetime
    timestamp: int


# --- Helper for Recent Projects (Adapted from Flask version) ---
async def save_recent_project(user_id: str, project_name: str, project_path: str, settings: AppSettings):
    logger.info(f"Saving recent project: '{project_name}' at '{project_path}' for user '{user_id}'")
    try:
        recent_projects_dir = settings.UPLOAD_FOLDER / "recent_projects"
        filename = recent_projects_dir / f"{user_id}.json"

        recent_projects: List[Dict[str, Any]] = []
        if filename.exists():
            with open(filename, 'r') as f:
                recent_projects = json.load(f)

        existing_index: Optional[int] = None
        for i, project in enumerate(recent_projects):
            if project.get('path') == project_path:
                existing_index = i
                break

        if existing_index is not None:
            recent_projects.pop(existing_index)

        recent_projects.insert(0, {
            'name': project_name, 'path': project_path,
            'last_opened': datetime.now().isoformat(), 'timestamp': int(datetime.now().timestamp())
        })

        recent_projects = recent_projects[:10] # Keep only top 10

        with open(filename, 'w') as f:
            json.dump(recent_projects, f, indent=4)
        logger.info(f"Successfully saved recent project for user {user_id}")
        return True
    except Exception as e:
        logger.exception(f"Error saving recent project for user {user_id}: {e}")
        return False

async def get_recent_projects_list(user_id: str, settings: AppSettings) -> List[RecentProjectEntry]:
    recent_projects_dir = settings.UPLOAD_FOLDER / "recent_projects"
    filename = recent_projects_dir / f"{user_id}.json"
    if not filename.exists():
        return []
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
            # Validate with Pydantic model if desired
            return [RecentProjectEntry(**item) for item in data]
    except Exception as e:
        logger.error(f"Error reading recent projects for user {user_id}: {e}")
        return []

async def delete_recent_project_entry(user_id: str, project_path_to_delete: str, settings: AppSettings) -> bool:
    recent_projects_dir = settings.UPLOAD_FOLDER / "recent_projects"
    filename = recent_projects_dir / f"{user_id}.json"
    if not filename.exists(): return False

    try:
        with open(filename, 'r') as f:
            recent_projects = json.load(f)

        original_len = len(recent_projects)
        recent_projects = [p for p in recent_projects if p.get('path') != project_path_to_delete]

        if len(recent_projects) < original_len:
            with open(filename, 'w') as f:
                json.dump(recent_projects, f, indent=4)
            return True
        return False
    except Exception as e:
        logger.error(f"Error deleting recent project entry for user {user_id}: {e}")
        return False

# --- API Endpoints ---

@router.post("/create", summary="Create a New Project")
async def create_project_api(
    payload: CreateProjectPayload = Body(...),
    user_id: str = Depends(get_current_user_id),
    settings: AppSettings = Depends(get_app_settings)
):
    logger.info(f"Processing create_project request for user '{user_id}'")
    project_name = payload.projectName
    project_location_input = payload.projectLocation

    if not project_name:
        raise HTTPException(status_code=400, detail="Project name is required.")
    if not project_location_input: # Assuming projectLocation is relative to a base if not absolute
        # Default to a 'projects' subdirectory under UPLOAD_FOLDER
        base_projects_dir = settings.UPLOAD_FOLDER / "projects"
    else:
        # Interpret projectLocation: if it's an absolute path, use it.
        # If relative, assume it's relative to UPLOAD_FOLDER/projects.
        # This logic needs to be robust and secure against path traversal.
        loc_path = Path(project_location_input)
        if loc_path.is_absolute():
            # Security check: ensure absolute path is within an allowed base, if applicable
            # For now, allowing absolute paths if user provides them, but this is risky.
            base_projects_dir = loc_path
        else:
            base_projects_dir = settings.UPLOAD_FOLDER / "projects" / loc_path

    base_projects_dir.mkdir(parents=True, exist_ok=True)

    # Sanitize project_name for use as a directory name
    s_project_name = safe_filename(project_name) # Use adapted safe_filename
    if not s_project_name:
         raise HTTPException(status_code=400, detail="Invalid project name resulting in empty safe filename.")

    project_path = base_projects_dir / s_project_name

    logger.debug(f"Attempting to create project at: {project_path}")

    if project_path.exists():
        raise HTTPException(status_code=409, detail=f"Project '{s_project_name}' already exists at this location.")

    try:
        # create_project_structure should use Path objects and be async or run in threadpool
        # For now, assuming it's adapted and sync for simplicity here.
        # template_folder_path = settings.TEMPLATE_FOLDER
        # result = await asyncio.to_thread(create_project_structure, project_path, template_folder_path)
        result = create_project_structure(project_path, settings.TEMPLATE_FOLDER) # Using sync version

        if not result or not result.get('success'):
            error_msg = result.get('message', 'Failed to create project structure.')
            logger.error(f"Project structure creation failed for {project_path}: {error_msg}")
            raise HTTPException(status_code=500, detail=error_msg)

        logger.info(f"Project '{project_name}' created at {project_path}")
        await save_recent_project(user_id, project_name, str(project_path), settings)

        # In FastAPI, we don't typically set current_app.config.
        # The concept of a "current project" needs to be handled differently,
        # e.g., per user session, via request headers, or path parameters for project-specific routes.
        # For now, just return success.

        return {
            "status": "success",
            "message": f"Project '{project_name}' created successfully!",
            "project_path": str(project_path), # Return string path
            "project_name": project_name
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error creating project '{project_name}': {e}")
        raise HTTPException(status_code=500, detail=f"Error creating project: {str(e)}")


@router.post("/validate", summary="Validate Project Structure")
async def validate_project_api(payload: ProjectPathPayload = Body(...)):
    project_path_str = payload.projectPath
    logger.info(f"Validating project at: {project_path_str}")
    project_path = Path(project_path_str)

    if not project_path.exists():
        raise HTTPException(status_code=404, detail=f"Project path does not exist: {project_path_str}")
    if not project_path.is_dir():
        raise HTTPException(status_code=400, detail=f"Path is not a directory: {project_path_str}")

    try:
        # validate_project_structure should be adapted to work with Path and be async if needed
        # result = await asyncio.to_thread(validate_project_structure, project_path)
        result = validate_project_structure(project_path) # Using sync version
        return result
    except Exception as e:
        logger.exception(f"Error validating project at {project_path_str}: {e}")
        raise HTTPException(status_code=500, detail=f"Error validating project: {str(e)}")


@router.post("/load", summary="Load a Project")
async def load_project_api(
    payload: ProjectPathPayload = Body(...),
    user_id: str = Depends(get_current_user_id),
    settings: AppSettings = Depends(get_app_settings)
):
    project_path_str = payload.projectPath
    logger.info(f"Loading project for user '{user_id}' from path: {project_path_str}")
    project_path = Path(project_path_str)

    if not project_path.exists() or not project_path.is_dir():
        raise HTTPException(status_code=404, detail=f"Project not found at path: {project_path_str}")

    try:
        # validation_result = await asyncio.to_thread(validate_project_structure, project_path)
        validation_result = validate_project_structure(project_path)

        if validation_result.get('status') == 'error':
            raise HTTPException(status_code=400, detail=f"Project validation failed: {validation_result.get('message')}")

        if validation_result.get('status') == 'warning' and validation_result.get('can_fix', False):
            logger.info(f"Attempting to fix missing templates for {project_path_str}")
            # copy_missing_templates should be Path-aware and potentially async
            # await asyncio.to_thread(copy_missing_templates, project_path, validation_result.get('missing_templates', []), settings.TEMPLATE_FOLDER)
            copy_missing_templates(project_path, validation_result.get('missing_templates', []), settings.TEMPLATE_FOLDER)


        project_name = project_path.name
        await save_recent_project(user_id, project_name, str(project_path), settings)

        # The concept of setting a "current project" in app config doesn't apply directly.
        # Client would typically store this, or subsequent requests would include project_id/path.
        logger.info(f"Project '{project_name}' loaded successfully by user '{user_id}'.")
        return {
            "status": "success",
            "message": "Project loaded successfully",
            "project_path": str(project_path),
            "project_name": project_name,
            "validation_status": validation_result.get('status')
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error loading project at {project_path_str}: {e}")
        raise HTTPException(status_code=500, detail=f"Error loading project: {str(e)}")


@router.get("/recent", response_model=List[RecentProjectEntry], summary="Get Recent Projects for Current User")
async def api_get_recent_projects(
    user_id: str = Depends(get_current_user_id),
    settings: AppSettings = Depends(get_app_settings)
):
    logger.info(f"Fetching recent projects for user '{user_id}'")
    return await get_recent_projects_list(user_id, settings)


@router.post("/delete_recent", summary="Delete a Project from Recent List")
async def api_delete_recent_project_entry( # Renamed to avoid conflict
    payload: ProjectPathPayload = Body(...),
    user_id: str = Depends(get_current_user_id),
    settings: AppSettings = Depends(get_app_settings)
):
    project_path_to_delete = payload.projectPath
    logger.info(f"Request to delete '{project_path_to_delete}' from recent projects for user '{user_id}'")

    success = await delete_recent_project_entry(user_id, project_path_to_delete, settings)
    if not success:
        # Could be not found or error during delete
        raise HTTPException(status_code=404, detail=f"Project path '{project_path_to_delete}' not found in recent projects or error deleting.")

    return {"status": "success", "message": "Project removed from recent projects."}


logger.info("Project management API router defined for FastAPI.")
print("Project management API router defined for FastAPI.")
