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
            content = await file.read() # Read the entire file content

            # Asynchronous file write
            def _write_file_sync(path: Path, data: bytes):
                with open(path, "wb") as buffer:
                    buffer.write(data)

            import asyncio # Make sure asyncio is imported
            await asyncio.to_thread(_write_file_sync, file_path, content)

            file_info = await get_file_info(file_path) # get_file_info is now async
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
        import asyncio # Make sure asyncio is imported
        tasks = []
        template_infos_for_processing = []

        for type_key, info in self.template_mapping.items():
            template_path = self.templates_base_dir / info['file']
            tasks.append(get_file_info(template_path)) # get_file_info is async
            template_infos_for_processing.append({'type_key': type_key, 'info': info})

        file_details_list = await asyncio.gather(*tasks)

        available_templates = []
        for i, file_details in enumerate(file_details_list):
            type_key = template_infos_for_processing[i]['type_key']
            info = template_infos_for_processing[i]['info']
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

        import asyncio # Make sure asyncio is imported
        exists = await asyncio.to_thread(template_path.exists)
        is_file = await asyncio.to_thread(template_path.is_file)

        if exists and is_file:
            return template_path
        else:
            logger.warning(f"Template file not found at path: {template_path} (exists: {exists}, is_file: {is_file})")
            return None

    async def get_project_file_info(self, project_name: str, relative_path_str: str) -> Dict[str, Any]:
        """
        Get information about a file within a specific project.
        relative_path_str is relative to the project's root.
        """
        if not project_name:
            raise ValueError("Project name must be provided.")

        import asyncio # Make sure asyncio is imported

        project_dir_name = safe_filename(project_name) # Santize once
        project_dir = self.projects_base_dir / project_dir_name

        project_dir_exists = await asyncio.to_thread(project_dir.exists)
        project_dir_is_dir = await asyncio.to_thread(project_dir.is_dir)

        if not project_dir_exists or not project_dir_is_dir:
            return {'exists': False, 'error': f"Project '{project_name}' not found or is not a directory."}

        # Ensure relative_path_str is truly relative and doesn't escape project_dir
        # Path.joinpath or / operator handles this safely if relative_path_str is simple.
        file_path = await asyncio.to_thread((project_dir / relative_path_str).resolve)

        # Security check: Ensure the resolved path is still within the project_dir
        resolved_project_dir = await asyncio.to_thread(project_dir.resolve)
        if resolved_project_dir not in file_path.parents and resolved_project_dir != file_path :
             logger.error(f"Path traversal attempt: '{relative_path_str}' for project '{project_name}' resolved to '{file_path}' which is outside project root '{resolved_project_dir}'")
             return {'exists': False, 'error': "Invalid file path (path traversal suspected)."}

        return await get_file_info(file_path) # get_file_info is async


    async def list_project_files(
        self, project_name: str, subdirectory: str = "", extensions: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        List files in a specific subdirectory of a project.
        Extensions should be like ['.xlsx', '.csv'].
        """
        if not project_name:
            raise ValueError("Project name must be provided.")

        import asyncio # Make sure asyncio is imported

        project_dir_name = safe_filename(project_name)
        project_dir = self.projects_base_dir / project_dir_name
        search_dir = await asyncio.to_thread((project_dir / subdirectory).resolve)

        search_dir_exists = await asyncio.to_thread(search_dir.exists)
        search_dir_is_dir = await asyncio.to_thread(search_dir.is_dir)

        if not search_dir_exists or not search_dir_is_dir:
            logger.warning(f"Search directory not found or not a directory: {search_dir}")
            return []

        # Security: ensure search_dir is within project_dir
        resolved_project_dir = await asyncio.to_thread(project_dir.resolve)
        if resolved_project_dir not in search_dir.parents and resolved_project_dir != search_dir:
            logger.error(f"List files attempt outside project: '{subdirectory}' for project '{project_name}' resolved to '{search_dir}'")
            return []

        listed_files_tasks = []
        # Get items from directory in a thread
        try:
            dir_items = await asyncio.to_thread(list, search_dir.iterdir())
        except OSError as e:
            logger.error(f"Error iterating directory {search_dir}: {e}")
            return []

        for item_path in dir_items:
            # Check if item is file in a thread
            is_file = await asyncio.to_thread(item_path.is_file)
            if is_file:
                if extensions:
                    normalized_extensions = [ext if ext.startswith('.') else f".{ext}" for ext in extensions]
                    if item_path.suffix.lower() not in normalized_extensions:
                        continue

                # get_file_info is already async
                listed_files_tasks.append(get_file_info(item_path))

        processed_file_infos = await asyncio.gather(*listed_files_tasks)

        listed_files = []
        for file_info_dict in processed_file_infos:
            if file_info_dict.get('exists'): # Ensure file still exists and info was fetched
                # Calculate relative path from project_dir for consistent client-side use
                # This part is tricky if item_path is not available directly, need to reconstruct from file_info_dict['path']
                item_path_from_info = Path(file_info_dict['path'])
                try:
                    file_info_dict['relative_path'] = str(item_path_from_info.relative_to(resolved_project_dir))
                except ValueError:
                    file_info_dict['relative_path'] = item_path_from_info.name
                listed_files.append(file_info_dict)

        listed_files.sort(key=lambda x: x.get('modified_iso', datetime.min.isoformat()), reverse=True)
        return listed_files

    async def get_project_inputs_info(self, project_name: str) -> Dict[str, Any]:
        """Get information about the project's 'inputs' directory."""
        if not project_name:
            raise ValueError("Project name must be provided.")
        project_dir = self.projects_base_dir / safe_filename(project_name)
        inputs_dir = project_dir / "inputs"

        import asyncio # Make sure asyncio is imported

        is_dir = await asyncio.to_thread(inputs_dir.is_dir)
        if not is_dir: # It might not exist yet, which is fine
            ensure_directory(inputs_dir) # Create if not exists (ensure_directory is sync)
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

        import asyncio # Make sure asyncio is imported

        project_inputs_dir = self.projects_base_dir / safe_filename(project_name) / "inputs"

        exists = await asyncio.to_thread(project_inputs_dir.exists)
        is_dir = await asyncio.to_thread(project_inputs_dir.is_dir)

        if not exists or not is_dir:
            return {'success': True, 'cleaned_files': [], 'failed_to_delete': [], 'message': "Inputs directory does not exist or is not a directory."}

        # cleanup_old_files is now async
        result = await cleanup_old_files(project_inputs_dir, max_age_days=max_age_days)
        return result

print("Defining data service for FastAPI... (merged and adapted from old_data_service.py)")
