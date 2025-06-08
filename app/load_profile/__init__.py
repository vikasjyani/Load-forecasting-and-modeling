from flask import Blueprint

bp = Blueprint('load_profile', __name__, template_folder='templates', url_prefix='/load_profile')

from app.load_profile import routes # Import routes after bp is defined
