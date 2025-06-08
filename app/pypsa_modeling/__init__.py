from flask import Blueprint

bp = Blueprint('pypsa_modeling', __name__, template_folder='templates', url_prefix='/pypsa_modeling')

from app.pypsa_modeling import routes # Import routes after bp is defined
