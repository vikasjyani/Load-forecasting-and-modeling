from flask import render_template, current_app, flash # current_app and flash might be used later
from app.admin import bp

@bp.route('/')
def index():
    # Add any specific logic for the admin dashboard here if needed
    # For example, checking user roles if authentication is implemented.
    # flash("Welcome to the Admin Panel!", "info") # Example flash message
    return render_template('admin_dashboard.html')
