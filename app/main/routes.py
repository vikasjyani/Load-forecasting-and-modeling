from flask import render_template, request, redirect, url_for, flash, jsonify, current_app
from app.main import bp
from app.utils.file_manager import ProjectManager
from app.utils.user_settings import load_recent_projects, save_recent_project
import os

@bp.route('/')
def home():
    recent_projects = load_recent_projects()
    return render_template('home.html', recent_projects=recent_projects)

@bp.route('/project/create_page')
def create_project_page():
    return render_template('create_project.html')

@bp.route('/project/create', methods=['POST'])
def create_project_route():
    project_name = request.form.get('project_name')
    if not project_name:
        flash('Project name is required.', 'error')
        return redirect(url_for('main.create_project_page'))

    pm = ProjectManager(current_app.config['PROJECT_ROOT_ABS'])

    try:
        name_original, folder_secured, path_abs = pm.create_project(project_name)
        if name_original:
            save_recent_project(name_original, folder_secured, path_abs)
            current_app.config['CURRENT_PROJECT_NAME'] = name_original
            current_app.config['CURRENT_PROJECT_FOLDER'] = folder_secured
            current_app.config['CURRENT_PROJECT_PATH_ABS'] = path_abs
            flash(f'Project "{name_original}" created successfully!', 'success')
            return redirect(url_for('main.home')) # Or a project specific page
        else:
            flash('Error creating project. Please check logs.', 'error')
            return redirect(url_for('main.create_project_page'))
    except ValueError as e:
        flash(str(e), 'error')
        return redirect(url_for('main.create_project_page'))
    except Exception as e:
        flash(f'An unexpected error occurred: {str(e)}', 'error')
        # Log the exception e
        return redirect(url_for('main.create_project_page'))


@bp.route('/project/load_page')
def load_project_page():
    pm = ProjectManager(current_app.config['PROJECT_ROOT_ABS'])
    all_projects = pm.list_projects()
    return render_template('load_project.html', projects=all_projects)

@bp.route('/project/load', methods=['POST'])
def load_project_route():
    project_folder = request.form.get('project_folder')
    if not project_folder:
        flash('No project selected.', 'error')
        return redirect(url_for('main.load_project_page'))

    pm = ProjectManager(current_app.config['PROJECT_ROOT_ABS'])
    metadata = pm.get_project_metadata(project_folder)

    if metadata:
        current_app.config['CURRENT_PROJECT_NAME'] = metadata['project_name_original']
        current_app.config['CURRENT_PROJECT_FOLDER'] = metadata['project_folder_secured']
        current_app.config['CURRENT_PROJECT_PATH_ABS'] = metadata['project_path_abs']
        save_recent_project(
            metadata['project_name_original'],
            metadata['project_folder_secured'],
            metadata['project_path_abs']
        )
        flash(f'Project "{metadata["project_name_original"]}" loaded successfully!', 'success')
        return redirect(url_for('main.home')) # Or a project specific page
    else:
        flash('Error loading project. Metadata not found or invalid.', 'error')
        return redirect(url_for('main.load_project_page'))

@bp.route('/api/projects', methods=['GET'])
def api_list_projects():
    pm = ProjectManager(current_app.config['PROJECT_ROOT_ABS'])
    projects = pm.list_projects()
    return jsonify(projects)
