# fastapi-energy-platform/app/api/v1/projects.py
"""
Project Management API Endpoints for FastAPI.
Handles creation, loading, validation, and management of projects.
"""
import logging
import os
from datetime import datetime # Ensure datetime is imported
from typing import List, Optional, Dict, Any
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Form, Body, Request, Query
from pydantic import BaseModel, Field, validator

# Assuming utilities are adapted and available.
# These imports need to be verified and adapted based on the final location and content of these utils.
from app.utils.helpers import create_project_structure, validate_project_structure, copy_missing_templates, safe_filename
# from app.utils.constants import ERROR_MESSAGES # If used for standardized messages
# from app.utils.error_handlers import ResourceNotFoundError, ProcessingError, ValidationError # If using these custom exceptions

import json # Added import for json
from app.config import Settings, settings as global_settings # Import global settings

# Placeholder for session/user management - FastAPI typically uses Depends for this.
# For now, using a fixed user_id as per plan.
FIXED_USER_ID = "global_user"

def get_current_user_id() -> str: # Removed request: Request dependency
    """Returns a fixed user ID, as no authentication is implemented."""
    return FIXED_USER_ID

# Dependency to inject global settings
def get_app_settings() -> Settings:
    return global_settings


logger = logging.getLogger(__name__)
router = APIRouter()

# --- Pydantic Models ---
class ProjectPathPayload(BaseModel):
    projectPath: str # Path to the project

class CreateProjectPayload(BaseModel):
    projectName: str = Field(..., min_length=1)
    projectLocation: Optional[str] = Field(default=None, description="Base location for the project, relative to PROJECT_DATA_ROOT/projects or an absolute path.")

class RecentProjectEntry(BaseModel):
    name: str
    path: str
    last_opened: datetime
    timestamp: int


# --- Helper for Recent Projects (Adapted from Flask version) ---
async def save_recent_project(user_id: str, project_name: str, project_path: str, app_settings: Settings):
    logger.info(f"Saving recent project: '{project_name}' at '{project_path}' for user '{user_id}'")
    try:
        # Construct paths using PROJECT_DATA_ROOT from injected settings
        recent_projects_base_dir = app_settings.PROJECT_DATA_ROOT / "recent_projects"
        recent_projects_base_dir.mkdir(parents=True, exist_ok=True)
        filename = recent_projects_base_dir / f"{user_id}.json"

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

async def get_recent_projects_list(user_id: str, app_settings: Settings) -> List[RecentProjectEntry]:
    recent_projects_base_dir = app_settings.PROJECT_DATA_ROOT / "recent_projects"
    filename = recent_projects_base_dir / f"{user_id}.json"
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

async def delete_recent_project_entry(user_id: str, project_path_to_delete: str, app_settings: Settings) -> bool:
    recent_projects_base_dir = app_settings.PROJECT_DATA_ROOT / "recent_projects"
    filename = recent_projects_base_dir / f"{user_id}.json"
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

@router.post("/create", summary="Create a New Project", response_model=Dict[str, Any])
async def create_project_api(
    payload: CreateProjectPayload = Body(...),
    user_id: str = Depends(get_current_user_id),
    app_settings: Settings = Depends(get_app_settings) # Use the new dependency
):
    logger.info(f"Processing create_project request for user '{user_id}'")
    project_name = payload.projectName
    project_location_input = payload.projectLocation

    if not project_name:
        raise HTTPException(status_code=400, detail="Project name is required.")

    # Determine base directory for projects
    # All projects will be created under PROJECT_DATA_ROOT/projects/
    # projectLocation can specify a subdirectory within this, or be an absolute path (checked for safety)
    default_projects_base = app_settings.PROJECT_DATA_ROOT / "projects"

    if project_location_input:
        loc_path = Path(project_location_input)
        if loc_path.is_absolute():
            # Security: Ensure absolute path is within or equal to PROJECT_DATA_ROOT if specified this way.
            # This is a very basic check. More robust checks might be needed depending on security requirements.
            if not str(loc_path.resolve()).startswith(str(app_settings.PROJECT_DATA_ROOT.resolve())):
                raise HTTPException(status_code=403, detail="Absolute projectLocation is outside the allowed data root.")
            base_projects_dir = loc_path
        else:
            # Relative to PROJECT_DATA_ROOT/projects/
            base_projects_dir = default_projects_base / loc_path
    else:
        # Default to PROJECT_DATA_ROOT/projects/
        base_projects_dir = default_projects_base

    base_projects_dir.mkdir(parents=True, exist_ok=True)

    s_project_name = safe_filename(project_name)
    if not s_project_name:
         raise HTTPException(status_code=400, detail="Invalid project name resulting in empty safe filename.")

    project_path = base_projects_dir / s_project_name

    logger.debug(f"Attempting to create project at: {project_path}")

    if project_path.exists():
        raise HTTPException(status_code=409, detail=f"Project '{s_project_name}' already exists at this location: {project_path}")

    try:
        # template_folder_path is typically where global templates are, not from AppSettings directly yet
        # This might need adjustment if template_folder is part of Settings. For now, assume helpers handle it.
        # The helper create_project_structure expects the global template root, not one from settings.
        # For now, let's assume the helper has access to a predefined template location or we pass one.
        # The global_settings.GLOBAL_FEATURES_CONFIG_PATH.parent / "templates" could be a convention
        # Or settings.TEMPLATE_FOLDER if defined in app.config.Settings.
        # For now, using a placeholder that needs to be confirmed:
        templates_dir = Path(app_settings.BASE_DIR) / "templates" # Assuming templates are at <repo_root>/templates/
        if not (templates_dir.exists() and templates_dir.is_dir()):
            # Fallback if BASE_DIR is not what we expect, or templates are elsewhere.
            # This path needs to be robust. Let's use a relative path from app for now
            templates_dir = Path(__file__).resolve().parent.parent.parent.parent / "static" / "templates"
            logger.warning(f"Global templates directory not found via settings, trying default: {templates_dir}")


        # result = await create_project_structure(project_path, app_settings.TEMPLATE_FOLDER) # if TEMPLATE_FOLDER is in Settings
        result = await create_project_structure(project_path, templates_dir)


        if not result or not result.get('success'):
            error_msg = result.get('message', 'Failed to create project structure.')
            logger.error(f"Project structure creation failed for {project_path}: {error_msg}")
            raise HTTPException(status_code=500, detail=error_msg)

        logger.info(f"Project '{project_name}' created at {project_path}")
        await save_recent_project(user_id, project_name, str(project_path.resolve()), app_settings)


        return {
            "status": "success",
            "message": f"Project '{project_name}' created successfully!",
            "project_path": str(project_path.resolve()),
            "project_name": project_name
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error creating project '{project_name}': {e}")
        raise HTTPException(status_code=500, detail=f"Error creating project: {str(e)}")


@router.post("/validate", summary="Validate Project Structure", response_model=Dict[str, Any])
async def validate_project_api(
    payload: ProjectPathPayload = Body(...),
    app_settings: Settings = Depends(get_app_settings) # Added for consistency, though not directly used here yet
):
    project_path_str = payload.projectPath
    logger.info(f"Validating project at: {project_path_str}")
    project_path = Path(project_path_str)

    # Security: Ensure project_path is within PROJECT_DATA_ROOT
    resolved_project_path = project_path.resolve()
    if not str(resolved_project_path).startswith(str(app_settings.PROJECT_DATA_ROOT.resolve())):
        raise HTTPException(status_code=403, detail="Access to this project path is forbidden.")

    if not project_path.exists():
        raise HTTPException(status_code=404, detail=f"Project path does not exist: {project_path_str}")
    if not project_path.is_dir():
        raise HTTPException(status_code=400, detail=f"Path is not a directory: {project_path_str}")

    try:
        result = await validate_project_structure(project_path) # validate_project_structure is async
        return result
    except Exception as e:
        logger.exception(f"Error validating project at {project_path_str}: {e}")
        raise HTTPException(status_code=500, detail=f"Error validating project: {str(e)}")


@router.post("/load", summary="Load a Project", response_model=Dict[str, Any])
async def load_project_api(
    payload: ProjectPathPayload = Body(...),
    user_id: str = Depends(get_current_user_id),
    app_settings: Settings = Depends(get_app_settings)
):
    project_path_str = payload.projectPath
    logger.info(f"Loading project for user '{user_id}' from path: {project_path_str}")
    project_path = Path(project_path_str)

    # Security: Ensure project_path is within PROJECT_DATA_ROOT
    resolved_project_path = project_path.resolve()
    if not str(resolved_project_path).startswith(str(app_settings.PROJECT_DATA_ROOT.resolve())):
        raise HTTPException(status_code=403, detail="Access to this project path is forbidden.")


    if not project_path.exists() or not project_path.is_dir():
        raise HTTPException(status_code=404, detail=f"Project not found at path: {project_path_str}")

    try:
        validation_result = await validate_project_structure(project_path) # is async

        if validation_result.get('status') == 'error':
            raise HTTPException(status_code=400, detail=f"Project validation failed: {validation_result.get('message')}")

        if validation_result.get('status') == 'warning' and validation_result.get('can_fix', False):
            logger.info(f"Attempting to fix missing templates for {project_path_str}")
            # Similar to create, template_folder needs to be robustly determined
            templates_dir = Path(app_settings.BASE_DIR) / "templates"
            if not (templates_dir.exists() and templates_dir.is_dir()):
                 templates_dir = Path(__file__).resolve().parent.parent.parent.parent / "static" / "templates"

            await copy_missing_templates(project_path, validation_result.get('missing_templates', []), templates_dir)


        project_name = project_path.name
        await save_recent_project(user_id, project_name, str(project_path.resolve()), app_settings)

        logger.info(f"Project '{project_name}' loaded successfully by user '{user_id}'.")
        return {
            "status": "success",
            "message": "Project loaded successfully",
            "project_path": str(project_path.resolve()),
            "project_name": project_name,
            "validation_status": validation_result.get('status')
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error loading project at {project_path_str}: {e}")
        raise HTTPException(status_code=500, detail=f"Error loading project: {str(e)}")


@router.get("/recent", response_model=List[RecentProjectEntry], summary="Get Recent Projects")
async def api_get_recent_projects( # Removed "for Current User" from summary as it's global
    user_id: str = Depends(get_current_user_id), # Still pass user_id, even if fixed
    app_settings: Settings = Depends(get_app_settings)
):
    logger.info(f"Fetching recent projects for user '{user_id}' (globally stored)")
    return await get_recent_projects_list(user_id, app_settings)


@router.post("/delete_recent", summary="Delete a Project from Recent List", response_model=Dict[str, str])
async def api_delete_recent_project_entry(
    payload: ProjectPathPayload = Body(...),
    user_id: str = Depends(get_current_user_id),
    app_settings: Settings = Depends(get_app_settings)
):
    project_path_to_delete = payload.projectPath # This is the path stored in recent_projects.json
    logger.info(f"Request to delete '{project_path_to_delete}' from recent projects for user '{user_id}' (globally stored)")

    # No path validation needed here as we are just removing a string from a JSON list.
    # The path itself isn't accessed on the filesystem by this operation.

    success = await delete_recent_project_entry(user_id, project_path_to_delete, app_settings)
    if not success:
        raise HTTPException(status_code=404, detail=f"Project path '{project_path_to_delete}' not found in recent projects or error deleting.")

    return {"status": "success", "message": "Project removed from recent projects."}


logger.info("Project management API router defined for FastAPI.")
# Removed print statement from here, it's better in main.py or config.py after loading.
