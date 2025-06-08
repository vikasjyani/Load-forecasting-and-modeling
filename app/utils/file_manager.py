import os
import json
import time
from werkzeug.utils import secure_filename
from datetime import datetime

class ProjectManager:
    def __init__(self, project_root_abs):
        self.project_root_abs = project_root_abs
        os.makedirs(self.project_root_abs, exist_ok=True)

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
            raise ValueError("Project name cannot be empty.")

        project_folder_secured = secure_filename(project_name_original)
        if not project_folder_secured: # Handle cases where secure_filename might return an empty string
            project_folder_secured = f"project_{int(time.time())}"


        project_path_abs = os.path.join(self.project_root_abs, project_folder_secured)

        # Handle potential name collisions by appending a suffix
        counter = 1
        temp_project_path_abs = project_path_abs
        temp_project_folder_secured = project_folder_secured
        while os.path.exists(temp_project_path_abs):
            temp_project_folder_secured = f"{project_folder_secured}_{counter}"
            temp_project_path_abs = os.path.join(self.project_root_abs, temp_project_folder_secured)
            counter += 1

        project_path_abs = temp_project_path_abs
        project_folder_secured = temp_project_folder_secured

        try:
            os.makedirs(project_path_abs, exist_ok=True)
            os.makedirs(os.path.join(project_path_abs, 'inputs'), exist_ok=True)
            os.makedirs(os.path.join(project_path_abs, 'results'), exist_ok=True)
            os.makedirs(os.path.join(project_path_abs, 'logs'), exist_ok=True)
            os.makedirs(os.path.join(project_path_abs, 'config'), exist_ok=True)

            metadata = {
                'project_name_original': project_name_original,
                'project_folder_secured': project_folder_secured,
                'project_path_abs': project_path_abs,
                'created_at': datetime.utcnow().isoformat() + 'Z',
                'updated_at': datetime.utcnow().isoformat() + 'Z',
                'status': 'initialized',
                'description': ''
            }
            with open(os.path.join(project_path_abs, 'project.json'), 'w') as f:
                json.dump(metadata, f, indent=4)

            return project_name_original, project_folder_secured, project_path_abs
        except OSError as e:
            # Log error or handle appropriately
            print(f"Error creating project directories or metadata file: {e}")
            return None, None, None


    def get_project_metadata(self, project_folder_secured):
        """
        Reads and returns project metadata from project.json.

        Args:
            project_folder_secured (str): The secured name of the project folder.

        Returns:
            dict: Project metadata, or None if file not found or JSON is invalid.
        """
        metadata_path = os.path.join(self.project_root_abs, project_folder_secured, 'project.json')
        if not os.path.exists(metadata_path):
            return None
        try:
            with open(metadata_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return None # Or raise a custom exception

    def list_projects(self):
        """
        Lists all valid projects by reading their metadata.
        A project is considered valid if it's a directory and contains a 'project.json' file.
        """
        projects = []
        if not os.path.exists(self.project_root_abs):
            return projects

        for folder_name in os.listdir(self.project_root_abs):
            project_path = os.path.join(self.project_root_abs, folder_name)
            if os.path.isdir(project_path):
                metadata = self.get_project_metadata(folder_name)
                if metadata:
                    projects.append(metadata)
        return sorted(projects, key=lambda p: p.get('updated_at', ''), reverse=True)

    def update_project_metadata(self, project_folder_secured, updates):
        """
        Updates metadata in project.json.

        Args:
            project_folder_secured (str): The secured name of the project folder.
            updates (dict): Dictionary containing updates to the metadata.

        Returns:
            bool: True if update was successful, False otherwise.
        """
        metadata_path = os.path.join(self.project_root_abs, project_folder_secured, 'project.json')
        if not os.path.exists(metadata_path):
            return False

        try:
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)

            metadata.update(updates)
            metadata['updated_at'] = datetime.utcnow().isoformat() + 'Z'

            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=4)
            return True
        except (json.JSONDecodeError, OSError) as e:
            # Log error
            print(f"Error updating project metadata: {e}")
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

    return True, "Valid"
