# fastapi-energy-platform/app/api/v1/data.py
"""
Data API Endpoints for FastAPI
Handles file uploads, template downloads, and other data-related operations.
"""
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from fastapi.responses import FileResponse # For serving files for download

# Assuming DataService is adapted and available for DI.
try:
    from app.services.data_service import DataService
except ImportError:
    logging.warning("DataService not found, using placeholder for data API.")
    class DataService: # Placeholder
        def __init__(self, project_data_root: Path = Path("."), templates_base_dir: Path = Path(".")):
            self.project_data_root = project_data_root
            self.templates_base_dir = templates_base_dir
        async def save_uploaded_file(self, project_name: str, file: UploadFile) -> Dict[str, Any]:
            return {"filename": file.filename, "file_path": f"/mock_uploads/{project_name}/{file.filename}", "success": True, "file_info": {"size_mb": 1}}
        async def get_available_templates_info(self) -> List[Dict[str, Any]]:
            return [{"type": "input_demand_file", "filename": "input_demand_file.xlsx", "description": "Mock template"}]
        async def get_template_file_path(self, template_type: str) -> Optional[Path]:
            mock_path = self.templates_base_dir / f"{template_type}_mock.xlsx"
            mock_path.touch(exist_ok=True) # Create dummy file for FileResponse
            return mock_path if mock_path.exists() else None
        async def get_document_path(self, filename: str) -> Optional[Path]: # Assuming documents are in templates_base_dir too
            mock_path = self.templates_base_dir / filename
            mock_path.touch(exist_ok=True)
            return mock_path if mock_path.exists() else None
        async def get_project_inputs_info(self, project_name: str) -> Dict[str, Any]: # Placeholder for upload_status
            return {"can_upload": True, "project_selected": project_name, "allowed_extensions": [".xlsx", ".csv"], "max_file_size_mb": 100}


from app.utils.error_handlers import ProcessingError, ResourceNotFoundError, ValidationError as CustomValidationError
# Assuming constants are moved and adapted
from app.utils.constants import ALLOWED_EXTENSIONS, MAX_FILE_SIZE # MAX_FILE_SIZE in bytes

logger = logging.getLogger(__name__)
router = APIRouter()

# --- Dependency for DataService ---
from app.dependencies import get_data_service as get_data_service_dependency
# The local get_data_service function is no longer needed.

# --- API Endpoints ---

@router.post("/upload", summary="Upload Data File to a Project")
async def upload_data_api(
    project_name: str = Query(..., description="Name of the project to upload the file to."),
    file: UploadFile = File(...),
    service: DataService = Depends(get_data_service_dependency)
):
    """
    Uploads a data file (e.g., Excel, CSV) to the specified project's input directory.
    Validates file extension and size.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected or filename is empty.")

    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in ALLOWED_EXTENSIONS: # ALLOWED_EXTENSIONS should include the dot, e.g. {'.xlsx', '.csv'}
        raise HTTPException(status_code=400, detail=f"File type {file_extension} not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")

    # Check file size (UploadFile.file is a SpooledTemporaryFile)
    # Reading the whole file into memory to check size can be an issue for very large files.
    # FastAPI/Starlette handle MAX_REQUEST_SIZE, but for fine-grained control per-endpoint:
    # One way is to stream it to a temp location and check size, or use file.size if available (added in Starlette 0.20.0)
    if hasattr(file, 'size') and file.size is not None:
        if file.size > MAX_FILE_SIZE:
             raise HTTPException(status_code=413, detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024 * 1024)}MB")
    else: # Fallback if file.size is not available (older Starlette or certain conditions)
        contents = await file.read()
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail=f"File too large (checked after read). Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB")
        await file.seek(0) # Reset file pointer after reading for size check if using contents

    try:
        result = await service.save_uploaded_file(project_name=project_name, file=file)
        if not result.get("success"):
            raise ProcessingError(message=result.get("error", "Failed to save file."))
        return result
    except (ProcessingError, ValueError, IOError) as e:
        logger.error(f"Error uploading file for project {project_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception(f"Unexpected error uploading file for project {project_name}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred during file upload.")


@router.get("/download/template/{template_type}", summary="Download Template File")
async def download_template_api(template_type: str, service: DataService = Depends(get_data_service_dependency)):
    """Downloads a specific template file (e.g., input_demand_file.xlsx)."""
    try:
        template_path = await service.get_template_file_path(template_type)
        if not template_path or not template_path.exists():
            raise ResourceNotFoundError(resource_type="Template", resource_id=template_type)

        # Generate a user-friendly download name
        download_filename = f"KSEB_{template_type}_template_{datetime.now().strftime('%Y%m%d')}{template_path.suffix}"

        return FileResponse(
            path=template_path,
            filename=download_filename,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' # Assuming xlsx
        )
    except ResourceNotFoundError as e:
        raise e # Re-raise to be handled by FastAPI's exception handlers
    except Exception as e:
        logger.exception(f"Error downloading template {template_type}: {e}")
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

# Similar endpoints for download_user_guide, download_methodology would be created
# if these documents are managed by DataService and stored in a configurable location.

@router.get("/templates", summary="List Available Templates")
async def list_templates_api(service: DataService = Depends(get_data_service_dependency)):
    """Retrieves a list of available data templates with their descriptions."""
    try:
        templates_info = await service.get_available_templates_info()
        return {"templates": templates_info, "total_templates": len(templates_info)}
    except Exception as e:
        logger.exception("Error listing templates_api")
        raise HTTPException(status_code=500, detail=f"Failed to list templates: {str(e)}")

@router.get("/upload_status", summary="Get Upload Status and Configuration")
async def upload_status_api(
    project_name: str = Query(..., description="Name of the project to check upload status for."),
    service: DataService = Depends(get_data_service_dependency)
):
    """Provides information about upload capabilities for a project, like allowed extensions and max size."""
    try:
        # This method in DataService might need to be adapted or it's a placeholder
        # In FastAPI, "project selected" is more about which project context the request is for.
        # This might come from a path parameter, a header, or a user session.
        status_info = await service.get_project_inputs_info(project_name) # Assuming this gives relevant info
        status_info["allowed_extensions"] = list(ALLOWED_EXTENSIONS)
        status_info["max_file_size_mb"] = MAX_FILE_SIZE // (1024*1024)
        return status_info
    except Exception as e:
        logger.exception(f"Error getting upload status for project {project_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get upload status: {str(e)}")


logger.info("Data API router defined for FastAPI.")
print("Data API router defined for FastAPI.")
