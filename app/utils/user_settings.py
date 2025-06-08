import json
import os
from config import Config

MAX_RECENT_PROJECTS = 10

def get_user_data_path():
    """Returns the path to the user's recent projects JSON file."""
    return os.path.join(Config.USER_DATA_DIR_ABS, 'default', 'recent_projects.json')

def load_recent_projects():
    """Loads recent projects from the JSON file.

    Handles FileNotFoundError and json.JSONDecodeError if the file doesn't exist
    or is corrupted.
    """
    path = get_user_data_path()
    if not os.path.exists(path):
        return []
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []  # Return empty list if JSON is invalid

def save_recent_project(project_name, project_folder, project_path_abs):
    """Saves a project to the recent projects list in JSON format.

    Manages the list size according to MAX_RECENT_PROJECTS.
    """
    recent_projects = load_recent_projects()

    # Remove existing entry if project_path_abs matches
    recent_projects = [p for p in recent_projects if p.get('project_path_abs') != project_path_abs]

    project_info = {
        'project_name': project_name,
        'project_folder': project_folder,
        'project_path_abs': project_path_abs
    }

    # Add new project to the beginning
    recent_projects.insert(0, project_info)

    # Ensure list doesn't exceed max size
    if len(recent_projects) > MAX_RECENT_PROJECTS:
        recent_projects = recent_projects[:MAX_RECENT_PROJECTS]

    path = get_user_data_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)  # Ensure directory exists
    with open(path, 'w') as f:
        json.dump(recent_projects, f, indent=4)
