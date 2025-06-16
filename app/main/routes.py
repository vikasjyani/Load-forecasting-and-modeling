from flask import render_template, request, redirect, url_for, flash, jsonify, current_app
from app.main import bp
from app.utils.file_manager import ProjectManager
from app.utils.user_settings import load_recent_projects, save_recent_project
import os

@bp.route('/')
def home():
    logger = current_app.logger
    try:
        logger.info(f"Accessing home page. Current project: {current_app.config.get('CURRENT_PROJECT_NAME', 'None')}")
        # load_recent_projects is already refactored to be robust and log errors.
        recent_projects = load_recent_projects()
        return render_template('home.html', recent_projects=recent_projects)
    except Exception as e:
        logger.error(f"Unhandled error in home route: {e}", exc_info=True)
        flash("An unexpected server error occurred. Please try again later.", "danger")
        # In a real scenario, you might want a more user-friendly error page or a redirect to a safe static page.
        # For now, rendering home with potentially missing data or redirecting to a simpler home might be options.
        # If home.html can handle recent_projects being None or empty gracefully:
        return render_template('home.html', recent_projects=[]) # Render with empty recent projects on error


@bp.route('/project/create_page')
def create_project_page():
    logger = current_app.logger
    try:
        logger.info("Accessing create project page.")
        return render_template('create_project.html')
    except Exception as e:
        logger.error(f"Unhandled error in create_project_page route: {e}", exc_info=True)
        flash("An unexpected server error occurred while trying to load the page.", "danger")
        return redirect(url_for('main.home')) # Redirect to home on error


@bp.route('/project/create', methods=['POST'])
def create_project_route():
    logger = current_app.logger
    try:
        project_name_original = request.form.get('project_name')
        if not project_name_original or not project_name_original.strip():
            logger.warning("Project creation attempt with empty name.")
            flash('Project name is required and cannot be empty.', 'warning')
            return redirect(url_for('main.create_project_page'))

        project_name_original = project_name_original.strip()
        logger.info(f"Attempting to create project: '{project_name_original}'")

        # ProjectManager instantiation might fail if PROJECT_ROOT_ABS is not configured or accessible
        # but __init__ now raises error if root cannot be created.
        try:
            pm = ProjectManager(current_app.config['PROJECT_ROOT_ABS'])
        except Exception as e_pm_init: # Catch error from ProjectManager.__init__
            logger.error(f"Failed to initialize ProjectManager: {e_pm_init}", exc_info=True)
            flash("Error initializing project management system. Cannot create project.", "danger")
            return redirect(url_for('main.create_project_page'))

        # pm.create_project was refactored to return (None, None, None) on failure and log its own errors.
        name, folder, path_abs = pm.create_project(project_name_original)

        if not path_abs: # Indicates failure from create_project
            logger.error(f"ProjectManager failed to create project '{project_name_original}'.")
            flash(f'Error creating project "{project_name_original}". Please check server logs for details or try a different name.', 'danger')
            return redirect(url_for('main.create_project_page'))

        # save_recent_project is refactored and logs its own errors. Failure here is non-critical for project creation.
        save_recent_project(name, folder, path_abs)

        # Update app config with current project details
        current_app.config['CURRENT_PROJECT_NAME'] = name
        current_app.config['CURRENT_PROJECT_FOLDER'] = folder
        current_app.config['CURRENT_PROJECT_PATH_ABS'] = path_abs

        logger.info(f"Project '{name}' (Folder: {folder}) created and loaded successfully. Path: {path_abs}")
        flash(f'Project "{name}" created and loaded successfully!', 'success')
        return redirect(url_for('main.home'))

    except ValueError as ve: # Catch specific ValueError from create_project if name is empty (though checked above)
        logger.warning(f"ValueError during project creation: {ve}", exc_info=True)
        flash(str(ve), 'danger') # Show specific error from create_project if it was a ValueError
        return redirect(url_for('main.create_project_page'))
    except Exception as e:
        logger.error(f"Unhandled error in create_project_route: {e}", exc_info=True)
        flash("An unexpected server error occurred while creating the project. Please try again or contact support.", "danger")
        return redirect(url_for('main.create_project_page'))


@bp.route('/project/load_page')
def load_project_page():
    logger = current_app.logger
    try:
        logger.info("Accessing load project page.")
        # ProjectManager instantiation can raise error if root dir fails (handled in __init__)
        try:
            pm = ProjectManager(current_app.config['PROJECT_ROOT_ABS'])
        except Exception as e_pm_init:
            logger.error(f"Failed to initialize ProjectManager for load_project_page: {e_pm_init}", exc_info=True)
            flash("Error initializing project management system. Cannot list projects.", "danger")
            return render_template('load_project.html', projects=[]) # Render with empty list

        # pm.list_projects() is already refactored to log its errors and return [] on failure.
        all_projects = pm.list_projects()

        if not all_projects:
            logger.info("No projects found or error listing projects for load_project_page.")
            # Flash message can be added here if desired, e.g., "No projects found."
            # The template should ideally handle an empty 'projects' list gracefully.
            pass # No need to flash, template should show "no projects"

        return render_template('load_project.html', projects=all_projects)

    except Exception as e:
        logger.error(f"Unhandled error in load_project_page route: {e}", exc_info=True)
        flash("An unexpected server error occurred while trying to load the projects list.", "danger")
        return render_template('load_project.html', projects=[]) # Render with empty list on error


@bp.route('/project/load', methods=['POST'])
def load_project_route():
    logger = current_app.logger
    try:
        project_folder_name = request.form.get('project_folder') # Name from form is 'project_folder'
        if not project_folder_name or not project_folder_name.strip():
            logger.warning("Load project attempt with no project folder selected.")
            flash('No project selected from the list.', 'warning')
            return redirect(url_for('main.load_project_page'))

        project_folder_secured = secure_filename(project_folder_name) # Ensure it's a safe name
        logger.info(f"Attempting to load project with folder: '{project_folder_secured}'")

        try:
            pm = ProjectManager(current_app.config['PROJECT_ROOT_ABS'])
        except Exception as e_pm_init:
             logger.error(f"Failed to initialize ProjectManager for load_project_route: {e_pm_init}", exc_info=True)
             flash("Error initializing project management system. Cannot load project.", "danger")
             return redirect(url_for('main.load_project_page'))

        # pm.get_project_metadata is already refactored to log errors and return None on failure.
        metadata = pm.get_project_metadata(project_folder_secured)

        if metadata:
            # Validate essential keys from metadata
            required_keys = ['project_name_original', 'project_folder_secured', 'project_path_abs']
            if not all(key in metadata for key in required_keys):
                logger.error(f"Project metadata for '{project_folder_secured}' is incomplete. Missing keys: {[key for key in required_keys if key not in metadata]}")
                flash(f'Error loading project "{project_folder_name}". Metadata is incomplete or corrupted.', 'danger')
                return redirect(url_for('main.load_project_page'))

            current_app.config['CURRENT_PROJECT_NAME'] = metadata['project_name_original']
            current_app.config['CURRENT_PROJECT_FOLDER'] = metadata['project_folder_secured']
            current_app.config['CURRENT_PROJECT_PATH_ABS'] = metadata['project_path_abs']

            # save_recent_project is refactored and logs its own errors. Non-critical for load success.
            save_recent_project(
                metadata['project_name_original'],
                metadata['project_folder_secured'],
                metadata['project_path_abs']
            )

            logger.info(f"Project '{metadata['project_name_original']}' (Folder: {metadata['project_folder_secured']}) loaded successfully.")
            flash(f'Project "{metadata["project_name_original"]}" loaded successfully!', 'success')
            return redirect(url_for('main.home'))
        else:
            logger.warning(f"Failed to load project: Metadata not found or invalid for folder '{project_folder_secured}'.")
            flash(f'Error loading project "{project_folder_name}". Metadata not found or is invalid. Please ensure the project exists and is correctly structured.', 'danger')
            return redirect(url_for('main.load_project_page'))

    except Exception as e:
        logger.error(f"Unhandled error in load_project_route: {e}", exc_info=True)
        flash("An unexpected server error occurred while trying to load the project.", "danger")
        return redirect(url_for('main.load_project_page'))


@bp.route('/api/projects', methods=['GET'])
def api_list_projects():
    logger = current_app.logger
    try:
        logger.info("API request received for listing projects.")
        # ProjectManager instantiation can raise error (handled in __init__)
        try:
            pm = ProjectManager(current_app.config['PROJECT_ROOT_ABS'])
        except Exception as e_pm_init:
            logger.error(f"API: Failed to initialize ProjectManager for api_list_projects: {e_pm_init}", exc_info=True)
            return jsonify({'error': 'Failed to initialize project management system.'}), 500

        # pm.list_projects() is already refactored to log its errors and return [] on internal failure.
        projects = pm.list_projects()

        # No specific error to flash here as it's an API. If projects is empty, it's a valid state.
        # The robust list_projects already logs if it had issues.
        logger.info(f"API: Returning {len(projects)} projects.")
        return jsonify(projects), 200

    except Exception as e:
        logger.error(f"Unhandled error in api_list_projects: {e}", exc_info=True)
        return jsonify({'error': 'An unexpected server error occurred while retrieving project list.'}), 500
