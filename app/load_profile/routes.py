from flask import render_template, current_app, flash # Added current_app and flash for context
from app.load_profile import bp

@bp.route('/')
def index(): # Renamed from dashboard to index
    # Example of how you might check for a current project, similar to other modules
    if not current_app.config.get('CURRENT_PROJECT_PATH_ABS'):
        flash('No project is currently loaded. Please load or create a project first to use this module.', 'warning')
    return render_template('load_profile_dashboard.html')
