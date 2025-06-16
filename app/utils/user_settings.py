import json
import os
# from config import Config # Config is usually accessed via current_app.config
from flask import current_app

MAX_RECENT_PROJECTS = 10

def get_user_data_path():
    """Returns the path to the user's recent projects JSON file."""
    # Assuming USER_DATA_DIR_ABS is configured in Flask app config
    base_user_data_dir = current_app.config.get('USER_DATA_DIR_ABS')
    if not base_user_data_dir:
        # This case should ideally not happen if app is configured correctly
        current_app.logger.error("USER_DATA_DIR_ABS not found in app config. Cannot determine user data path.")
        # Fallback to a local path or raise error, depending on desired handling.
        # For now, let it potentially fail in os.path.join if base_user_data_dir is None.
        # Or, define a default fallback within the function if critical.
        # Fallback for safety, though this indicates a config issue:
        base_user_data_dir = os.path.join(current_app.config.get('BASE_DIR', '.'), 'users')
        current_app.logger.warning(f"USER_DATA_DIR_ABS missing, falling back to {base_user_data_dir}")

    return os.path.join(base_user_data_dir, 'default', 'recent_projects.json')

def load_recent_projects():
    """
    Loads recent projects from the JSON file.
    Handles file errors and JSON decoding errors.
    """
    user_file = get_user_data_path()

    if not os.path.exists(user_file):
        current_app.logger.info(f"Recent projects file not found: {user_file}. Returning empty list.")
        return []

    try:
        with open(user_file, 'r', encoding='utf-8') as f: # Specify encoding
            data = json.load(f)

        if not isinstance(data, list):
            current_app.logger.warning(f"Recent projects data in {user_file} is not a list. Corrupted file? Returning empty list.")
            # Optionally, attempt to backup/rename the corrupted file here
            # os.rename(user_file, user_file + ".corrupted_" + datetime.now().strftime('%Y%m%d%H%M%S'))
            return []

        # Optional: Validate structure of items in the list (e.g., ensure each item is a dict with expected keys)
        # valid_projects = []
        # for project in data:
        #     if isinstance(project, dict) and 'project_name' in project and 'project_path_abs' in project:
        #         valid_projects.append(project)
        #     else:
        #         current_app.logger.warning(f"Invalid project entry found in {user_file}: {project}")
        # return valid_projects
        current_app.logger.debug(f"Successfully loaded {len(data)} recent projects from {user_file}.")
        return data

    except json.JSONDecodeError as e:
        current_app.logger.error(f"Error decoding JSON from recent projects file {user_file}: {e}", exc_info=True)
        # Optionally, backup/rename the corrupted file here
        return []
    except (IOError, OSError) as e:
        current_app.logger.error(f"Error reading recent projects file {user_file}: {e}", exc_info=True)
        return []
    except Exception as e: # Catch-all for any other unexpected errors
        current_app.logger.error(f"Unexpected error loading recent projects from {user_file}: {e}", exc_info=True)
        return []

def save_recent_project(project_name, project_folder, project_path_abs):
    """Saves a project to the recent projects list in JSON format.

    Manages the list size according to MAX_RECENT_PROJECTS.
    """
    recent_projects = load_recent_projects() # load_recent_projects now handles its own errors/logging

    # Remove existing entry if project_path_abs matches to prevent duplicates and move to top
    recent_projects = [p for p in recent_projects if p.get('project_path_abs') != project_path_abs]

    project_info = {
        'project_name': project_name,
        'project_folder': project_folder, # This is secured_name
        'project_path_abs': project_path_abs
        # Consider adding a timestamp for when it was last accessed/saved here
        # 'last_accessed_utc': datetime.utcnow().isoformat() + 'Z',
    }

    # Add new project to the beginning of the list
    recent_projects.insert(0, project_info)

    # Ensure list doesn't exceed max size
    if len(recent_projects) > MAX_RECENT_PROJECTS:
        recent_projects = recent_projects[:MAX_RECENT_PROJECTS]

    user_file_path = get_user_data_path()
    user_dir = os.path.dirname(user_file_path)

    try:
        # Ensure the directory structure exists (e.g., users/default/)
        # This was also added in app/__init__.py, but good to have here for robustness if called standalone
        os.makedirs(user_dir, exist_ok=True)
    except OSError as e:
        current_app.logger.error(f"Error creating user directory {user_dir} for recent projects: {e}", exc_info=True)
        return # Cannot proceed if directory creation fails

    try:
        with open(user_file_path, 'w', encoding='utf-8') as f: # Specify encoding
            json.dump(recent_projects, f, indent=2) # Using indent=2 for slightly more compact JSON
        current_app.logger.info(f"Recent project '{project_name}' (path: {project_path_abs}) saved to {user_file_path}.")
    except (IOError, OSError) as e:
        current_app.logger.error(f"Error writing recent projects to {user_file_path}: {e}", exc_info=True)
    except Exception as e: # Catch-all for any other unexpected errors
        current_app.logger.error(f"Unexpected error saving recent projects to {user_file_path}: {e}", exc_info=True)
