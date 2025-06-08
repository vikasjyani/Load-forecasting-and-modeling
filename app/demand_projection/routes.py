import os
from flask import current_app, flash, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename
from app.demand_projection import bp
from app.utils.file_manager import validate_file_upload


@bp.route('/upload_page')
def upload_page():
    return render_template('upload_demand_data.html')

@bp.route('/upload_demand_file', methods=['POST'])
def upload_demand_file():
    if not current_app.config.get('CURRENT_PROJECT_PATH_ABS'):
        flash('No project is currently loaded. Please load or create a project first.', 'error')
        return redirect(url_for('demand_projection.upload_page'))

    if 'file' not in request.files:
        flash('No file part in the request.', 'error')
        return redirect(url_for('demand_projection.upload_page'))

    file = request.files['file']

    if file.filename == '':
        flash('No selected file.', 'error')
        return redirect(url_for('demand_projection.upload_page'))

    # The real validate_file_upload will be in app.utils.file_manager
    # For now, using the placeholder defined above or will update file_manager.py first
    # and then uncomment the proper import.
    # For now, let's assume validate_file_upload is available from file_manager
    # If it's not, this will cause an error until file_manager.py is updated.
    # To avoid this, I will use the local placeholder for now.

    is_valid, message = validate_file_upload(file, allowed_extensions={'xlsx'})

    if not is_valid:
        flash(message, 'error')
        return redirect(url_for('demand_projection.upload_page'))

    try:
        project_path_abs = current_app.config['CURRENT_PROJECT_PATH_ABS']
        inputs_folder = os.path.join(project_path_abs, 'inputs')
        os.makedirs(inputs_folder, exist_ok=True) # Ensure inputs folder exists

        # Standardized filename
        filename = secure_filename('input_demand_file.xlsx')

        file_path = os.path.join(inputs_folder, filename)
        file.save(file_path)
        flash(f'File "{filename}" uploaded successfully to project inputs.', 'success')
    except Exception as e:
        flash(f'An error occurred while saving the file: {str(e)}', 'error')
        # Log the exception e for debugging
        print(f"Error saving file: {e}")

    return redirect(url_for('demand_projection.upload_page'))
