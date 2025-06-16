from flask import render_template, current_app, flash
from app.pypsa_modeling import bp

@bp.route('/')
def index(): # Renaming to 'index' for consistency with url_for
    if not current_app.config.get('CURRENT_PROJECT_PATH_ABS'):
        flash('No project is currently loaded. Please load or create a project first to use this module.', 'warning')
    return render_template('pypsa_dashboard.html')
