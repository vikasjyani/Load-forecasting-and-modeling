from flask import Blueprint

bp = Blueprint('admin', __name__, template_folder='templates', url_prefix='/admin')

from app.admin import routes # Import routes after bp is defined
