import os
import json
import time
from werkzeug.utils import secure_filename
from datetime import datetime
from flask import current_app # Added current_app

class ProjectManager:
    def __init__(self, project_root_abs):
        self.project_root_abs = project_root_abs
        try:
            os.makedirs(self.project_root_abs, exist_ok=True)
            current_app.logger.info(f"Project root directory ensured: {self.project_root_abs}")
        except OSError as e:
            current_app.logger.error(f"Failed to create project root directory {self.project_root_abs}: {e}", exc_info=True)
            # Depending on severity, might raise an exception or handle gracefully
            # For now, if this fails, subsequent operations will likely fail too.
            raise # Re-raise the exception as this is critical

    def create_project(self, project_name_original):
        """
        Creates a new project directory structure and metadata file.

        Args:
            project_name_original (str): The desired name for the project.

        Returns:
            tuple: (project_name_original, project_folder_secured, project_path_abs)
                   Returns (None, None, None) if project creation fails (e.g., name collision after sanitization).
        """
        if not project_name_original:
            current_app.logger.warning("Attempted to create a project with an empty name.")
            # Consider if ValueError is appropriate or if it should return None tuple
            raise ValueError("Project name cannot be empty.")

        project_folder_secured = secure_filename(project_name_original)
        if not project_folder_secured:
            timestamp_suffix = datetime.now().strftime('%Y%m%d%H%M%S')
            project_folder_secured = f"unnamed_project_{timestamp_suffix}"
            current_app.logger.info(f"Original project name '{project_name_original}' was sanitized to empty. Using default: '{project_folder_secured}'")

        base_project_folder_secured = project_folder_secured
        project_path_abs = os.path.join(self.project_root_abs, project_folder_secured)

        counter = 1
        while os.path.exists(project_path_abs):
            current_app.logger.info(f"Project path {project_path_abs} already exists. Appending suffix.")
            project_folder_secured = f"{base_project_folder_secured}_{counter}"
            project_path_abs = os.path.join(self.project_root_abs, project_folder_secured)
            counter += 1

        current_app.logger.info(f"Final project path set to: {project_path_abs}")

        try:
            # Create all subdirectories
            subfolders = ['inputs', 'results', 'logs', 'config']
            os.makedirs(project_path_abs, exist_ok=True) # Create main project directory first
            for subfolder in subfolders:
                os.makedirs(os.path.join(project_path_abs, subfolder), exist_ok=True)
            current_app.logger.info(f"Created subdirectories for project: {project_folder_secured}")

            metadata = {
                'project_name_original': project_name_original,
                'project_folder_secured': project_folder_secured, # The potentially suffixed one
                'project_path_abs': project_path_abs,
                'created_at': datetime.utcnow().isoformat() + 'Z',
                'updated_at': datetime.utcnow().isoformat() + 'Z',
                'status': 'initialized',
                'description': ''
            }

            # Path for project.json is now inside the 'config' subfolder
            metadata_file_path = os.path.join(project_path_abs, 'config', 'project.json')
            with open(metadata_file_path, 'w') as f:
                json.dump(metadata, f, indent=4)

            current_app.logger.info(f"Project '{project_name_original}' (folder: {project_folder_secured}) created successfully at {project_path_abs}")
            return project_name_original, project_folder_secured, project_path_abs

        except OSError as e:
            current_app.logger.error(f"OSError creating project structure for '{project_name_original}' (folder: {project_folder_secured}) at {project_path_abs}: {e}", exc_info=True)
            # Attempt to clean up partially created directory if error occurred?
            # For now, leave as is, but this could be a point for more robust cleanup.
            return None, None, None
        except (IOError, json.JSONDecodeError) as e: # JSONDecodeError is unlikely on dump, but good practice
            current_app.logger.error(f"Error writing project.json for '{project_name_original}' (folder: {project_folder_secured}): {e}", exc_info=True)
            return None, None, None
        except Exception as e: # Catch any other unexpected errors
            current_app.logger.error(f"Unexpected error creating project '{project_name_original}' (folder: {project_folder_secured}): {e}", exc_info=True)
            return None, None, None


    def get_project_metadata(self, project_folder_secured):
        """
        Reads and returns project metadata from project.json.

        Args:
            project_folder_secured (str): The secured name of the project folder.

        Returns:
            dict: Project metadata, or None if file not found or JSON is invalid.
        """
        # project.json is now in config subfolder
        metadata_path = os.path.join(self.project_root_abs, project_folder_secured, 'config', 'project.json')

        if not os.path.exists(metadata_path):
            current_app.logger.warning(f"Metadata file not found for project {project_folder_secured} at {metadata_path}")
            return None
        try:
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            current_app.logger.debug(f"Successfully loaded metadata for project {project_folder_secured}")
            return metadata
        except FileNotFoundError: # Should be caught by os.path.exists, but good for robustness
            current_app.logger.error(f"FileNotFoundError for metadata file that supposedly exists: {metadata_path}", exc_info=True)
            return None
        except (IOError, OSError) as e:
            current_app.logger.error(f"IOError/OSError reading metadata for project {project_folder_secured} from {metadata_path}: {e}", exc_info=True)
            return None
        except json.JSONDecodeError as e:
            current_app.logger.error(f"JSONDecodeError for metadata file {metadata_path} in project {project_folder_secured}: {e}", exc_info=True)
            return None # Or raise a custom exception
        except Exception as e: # Catch any other unexpected errors
            current_app.logger.error(f"Unexpected error reading metadata for project {project_folder_secured}: {e}", exc_info=True)
            return None


    def list_projects(self):
        """
        Lists all valid projects by reading their metadata.
        A project is considered valid if it's a directory and contains a 'config/project.json' file.
        """
        projects = []
        if not os.path.exists(self.project_root_abs):
            current_app.logger.warning(f"Project root directory {self.project_root_abs} does not exist. Cannot list projects.")
            return projects # Return empty list

        try:
            for folder_name in os.listdir(self.project_root_abs):
                project_path = os.path.join(self.project_root_abs, folder_name)
                if os.path.isdir(project_path):
                    # get_project_metadata already handles its own logging and errors, returns None on failure
                    metadata = self.get_project_metadata(folder_name)
                    if metadata:
                        projects.append(metadata)
            current_app.logger.info(f"Found {len(projects)} valid projects in {self.project_root_abs}")
        except OSError as e:
            current_app.logger.error(f"OSError listing projects in {self.project_root_abs}: {e}", exc_info=True)
            return [] # Return empty list on error
        except Exception as e: # Catch any other unexpected errors
            current_app.logger.error(f"Unexpected error listing projects: {e}", exc_info=True)
            return []

        try:
            # Sort projects by 'updated_at' in descending order. Handle cases where 'updated_at' might be missing.
            return sorted(projects, key=lambda p: p.get('updated_at', datetime.min.isoformat()), reverse=True)
        except Exception as e: # Catch errors during sorting (e.g. inconsistent updated_at format, though unlikely with ISO)
            current_app.logger.error(f"Error sorting projects: {e}", exc_info=True)
            return projects # Return unsorted list if sorting fails

    def update_project_metadata(self, project_folder_secured, updates):
        """
        Updates metadata in project.json.

        Args:
            project_folder_secured (str): The secured name of the project folder.
            updates (dict): Dictionary containing updates to the metadata.

        Returns:
            bool: True if update was successful, False otherwise.
        """
        # project.json is now in config subfolder
        metadata_path = os.path.join(self.project_root_abs, project_folder_secured, 'config', 'project.json')

        if not os.path.exists(metadata_path):
            current_app.logger.warning(f"Cannot update metadata: File not found for project {project_folder_secured} at {metadata_path}")
            return False

        try:
            # Read existing metadata
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            current_app.logger.debug(f"Read existing metadata from {metadata_path}")

            # Update with new data
            metadata.update(updates)
            metadata['updated_at'] = datetime.utcnow().isoformat() + 'Z' # Update timestamp

            # Write updated metadata back
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=4)
            current_app.logger.info(f"Successfully updated metadata for project {project_folder_secured} with updates: {list(updates.keys())}")
            return True

        except FileNotFoundError: # Should be caught by os.path.exists, but good for robustness
            current_app.logger.error(f"FileNotFoundError for metadata file that supposedly exists during update: {metadata_path}", exc_info=True)
            return False
        except (IOError, OSError) as e:
            current_app.logger.error(f"IOError/OSError updating metadata for project {project_folder_secured} at {metadata_path}: {e}", exc_info=True)
            return False
        except json.JSONDecodeError as e: # Error reading existing JSON
            current_app.logger.error(f"JSONDecodeError reading metadata file {metadata_path} for update in project {project_folder_secured}: {e}", exc_info=True)
            return False
        except Exception as e: # Catch any other unexpected errors
            current_app.logger.error(f"Unexpected error updating metadata for project {project_folder_secured}: {e}", exc_info=True)
            return False


ALLOWED_EXTENSIONS = {'xlsx', 'csv', 'json', 'txt'} # Expanded for general use, but can be context-specific
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

def validate_file_upload(file, allowed_extensions=ALLOWED_EXTENSIONS, max_size=MAX_FILE_SIZE):
    """
    Validates a file upload.

    Args:
        file (FileStorage): The file object from Flask request.
        allowed_extensions (set): A set of allowed file extensions (e.g., {'txt', 'pdf', 'png'}).
        max_size (int): Maximum allowed file size in bytes.

    Returns:
        tuple: (bool, str) where bool is True if valid, False otherwise,
               and str is a message ("Valid" or an error message).
    """
    if not file:
        return False, "No file provided."

    filename = file.filename
    if filename == '':
        return False, "No selected file."

    if '.' not in filename or \
       filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
        return False, f"Invalid file type. Allowed extensions are: {', '.join(allowed_extensions)}"

    try:
        # Check file size without saving the entire file to memory if it's too large
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)  # Reset cursor to the beginning of the file
    except Exception as e: #pylint: disable=broad-except
        # print(f"Could not determine file size: {e}") # Optional logging
        return False, "Could not determine file size."


    if size > max_size:
        return False, f"File is too large. Maximum size is {max_size // (1024*1024)}MB."

    current_app.logger.debug(f"File '{filename}' validated successfully (size: {size} bytes, type: {filename.rsplit('.', 1)[1].lower()}).")
    return True, "Valid"
