from flask import Blueprint

bp = Blueprint('main', __name__, template_folder='templates', url_prefix='/')

from app.main import routes  # Import routes after bp is defined to avoid circular dependency
