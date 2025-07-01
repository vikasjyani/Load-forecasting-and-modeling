# fastapi-energy-platform/app/services/data_service.py
"""
Data Service Layer for FastAPI
Handles file operations, template management, and document handling.
"""
import os
import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from fastapi import UploadFile # For handling file uploads in FastAPI

# Assuming utilities are adapted and available
from app.utils.helpers import ensure_directory, get_file_info, safe_filename
# Constants might be loaded from config or defined here/in utils
# from app.config import Settings # Example for getting configured paths
# from app.utils.constants import TEMPLATE_FILES # If still used

logger = logging.getLogger(__name__)

class DataService:
    """
    Service for data and file operations.
    Paths for projects, templates, etc., should be injected or come from settings.
    """

    def __init__(
        self,
        # settings: Settings = Depends(get_settings_dependency) # Example DI
        # For now, using placeholders for paths. These MUST be configured.
        projects_base_dir: Path = Path("user_projects_data"), # Example base for all projects
        templates_base_dir: Path = Path("app_templates") # Example base for app's templates
    ):
        # self.projects_base_dir = settings.PROJECTS_BASE_DIR
        # self.templates_base_dir = settings.TEMPLATES_DIR
        self.projects_base_dir = projects_base_dir
        self.templates_base_dir = templates_base_dir
        ensure_directory(self.projects_base_dir)
        ensure_directory(self.templates_base_dir)

        # Template type mapping - this could also be loaded from a config file
        # The keys are internal identifiers, 'file' is the actual filename within templates_base_dir
        self.template_mapping = {
            'data_input': {'file': 'input_demand_file.xlsx', 'description': 'Data input template for demand forecasting'},
            'load_curve': {'file': 'load_curve_template.xlsx', 'description': 'Load curve template for profile generation'},
            'pypsa_input': {'file': 'pypsa_input_template.xlsx', 'description': 'PyPSA model input template'},
            'load_profile_excel': {'file': 'load_profile.xlsx', 'description': 'Load profile Excel template'}
        }
        # Note: 'input_demand_file.xlsx' was duplicated in original, consolidated here.


    async def save_uploaded_file(self, project_name: str, file: UploadFile) -> Dict[str, Any]:
        """
        Save uploaded file to a specific project's inputs directory.

        Args:
            project_name: The name of the project.
            file: UploadFile object from FastAPI.

        Returns:
            Dict with file information or error.
        """
        if not project_name:
            raise ValueError("Project name must be provided.")
        if not file.filename:
            raise ValueError("Uploaded file has no filename.")

        project_inputs_dir = self.projects_base_dir / safe_filename(project_name) / "inputs"
        ensure_directory(project_inputs_dir)

        # Sanitize filename from UploadFile
        s_filename = safe_filename(file.filename)
        file_path = project_inputs_dir / s_filename

        try:
            # In FastAPI, UploadFile has a file-like interface (SpooledTemporaryFile)
            # We read from it and write to the destination.
            # For large files, consider streaming in chunks.
            with open(file_path, "wb") as buffer:
                content = await file.read() # Read the entire file content
                buffer.write(content)

            file_info = get_file_info(file_path) # Assuming get_file_info works with Path objects
            logger.info(f"Saved uploaded file to: {file_path}")
            return {
                'filename': s_filename,
                'file_path': str(file_path), # Return as string for JSON responses
                'project_name': project_name,
                'file_info': file_info,
                'success': True
            }
        except IOError as e: # Catch more specific IO errors
            logger.exception(f"IOError saving uploaded file {s_filename} to {project_inputs_dir}: {e}")
            raise IOError(f"Could not save file: {s_filename}. Check permissions or disk space.")
        except Exception as e:
            logger.exception(f"Error saving uploaded file {s_filename}: {e}")
            # Re-raise a more generic or specific custom exception
            raise RuntimeError(f"An unexpected error occurred while saving the file: {s_filename}")


    async def get_available_templates_info(self) -> List[Dict[str, Any]]:
        """Get list of available template types with their details."""
        available_templates = []
        for type_key, info in self.template_mapping.items():
            template_path = self.templates_base_dir / info['file']
            file_details = get_file_info(template_path)
            available_templates.append({
                "type": type_key,
                "filename": info['file'],
                "description": info['description'],
                "available": file_details['exists'],
                "size_mb": file_details.get('size_mb'),
                "modified_at": file_details.get('modified')
            })
        return available_templates

    async def get_template_file_path(self, template_type: str) -> Optional[Path]:
        """
        Get the absolute file path for a given template type.
        Returns Path object if found, None otherwise.
        """
        if template_type not in self.template_mapping:
            logger.warning(f"Template type '{template_type}' not found in mapping.")
            return None

        template_filename = self.template_mapping[template_type]['file']
        template_path = self.templates_base_dir / template_filename

        if template_path.exists() and template_path.is_file():
            return template_path
        else:
            logger.warning(f"Template file not found at path: {template_path}")
            return None

    async def get_project_file_info(self, project_name: str, relative_path_str: str) -> Dict[str, Any]:
        """
        Get information about a file within a specific project.
        relative_path_str is relative to the project's root.
        """
        if not project_name:
            raise ValueError("Project name must be provided.")

        project_dir = self.projects_base_dir / safe_filename(project_name)
        if not project_dir.exists() or not project_dir.is_dir():
            return {'exists': False, 'error': f"Project '{project_name}' not found."}

        # Ensure relative_path_str is truly relative and doesn't escape project_dir
        # Path.joinpath or / operator handles this safely if relative_path_str is simple.
        # For untrusted input, more validation might be needed.
        file_path = (project_dir / relative_path_str).resolve()

        # Security check: Ensure the resolved path is still within the project_dir
        if project_dir.resolve() not in file_path.parents and project_dir.resolve() != file_path :
             logger.error(f"Path traversal attempt: {relative_path_str} for project {project_name}")
             return {'exists': False, 'error': "Invalid file path (path traversal suspected)."}

        return get_file_info(file_path)


    async def list_project_files(
        self, project_name: str, subdirectory: str = "", extensions: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        List files in a specific subdirectory of a project.
        Extensions should be like ['.xlsx', '.csv'].
        """
        if not project_name:
            raise ValueError("Project name must be provided.")

        project_dir = self.projects_base_dir / safe_filename(project_name)
        search_dir = (project_dir / subdirectory).resolve()

        if not search_dir.exists() or not search_dir.is_dir():
            logger.warning(f"Search directory not found: {search_dir}")
            return []

        # Security: ensure search_dir is within project_dir
        if project_dir.resolve() not in search_dir.parents and project_dir.resolve() != search_dir:
            logger.error(f"List files attempt outside project: {subdirectory} for project {project_name}")
            return []

        listed_files = []
        for item_path in search_dir.iterdir():
            if item_path.is_file():
                if extensions:
                    # Ensure extensions have a leading dot for consistency if not provided
                    normalized_extensions = [ext if ext.startswith('.') else f".{ext}" for ext in extensions]
                    if item_path.suffix.lower() not in normalized_extensions:
                        continue

                file_info_dict = get_file_info(item_path)
                # Calculate relative path from project_dir for consistent client-side use
                try:
                    file_info_dict['relative_path'] = str(item_path.relative_to(project_dir))
                except ValueError: # Should not happen if security check above is correct
                    file_info_dict['relative_path'] = item_path.name

                listed_files.append(file_info_dict)

        listed_files.sort(key=lambda x: x.get('modified', datetime.min.isoformat()), reverse=True)
        return listed_files

    async def get_project_inputs_info(self, project_name: str) -> Dict[str, Any]:
        """Get information about the project's 'inputs' directory."""
        if not project_name:
            raise ValueError("Project name must be provided.")
        project_dir = self.projects_base_dir / safe_filename(project_name)
        inputs_dir = project_dir / "inputs"

        if not inputs_dir.is_dir(): # It might not exist yet, which is fine
            ensure_directory(inputs_dir) # Create if not exists
            return {'path': str(inputs_dir), 'file_count': 0, 'files': [], 'total_size_mb': 0.0, 'available': True}

        files = await self.list_project_files(project_name, subdirectory="inputs")
        total_size_mb = sum(f.get('size_mb', 0.0) for f in files if f.get('size_mb'))
        return {
            'path': str(inputs_dir),
            'file_count': len(files),
            'files': files,
            'total_size_mb': round(total_size_mb, 2),
            'available': True
        }

    async def cleanup_project_old_uploads(self, project_name: str, max_age_days: int = 30) -> Dict[str, Any]:
        """Clean up old uploaded files in a specific project's 'inputs' directory."""
        if not project_name:
            raise ValueError("Project name must be provided.")

        project_inputs_dir = self.projects_base_dir / safe_filename(project_name) / "inputs"
        if not project_inputs_dir.exists() or not project_inputs_dir.is_dir():
            return {'success': True, 'cleaned_files': [], 'failed_files': [], 'message': "Inputs directory does not exist."}

        # cleanup_old_files needs to be Path-aware or adapted
        # For now, assuming it works with Path objects:
        result = cleanup_old_files(project_inputs_dir, max_age_days=max_age_days)
        # cleanup_old_files from helpers.py returns:
        # {'success': True, 'cleaned_files': cleaned_files, 'failed_files': failed_files, 'message': ...}
        return result

print("Defining data service for FastAPI... (merged and adapted from old_data_service.py)")
