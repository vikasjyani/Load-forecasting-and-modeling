from flask import Blueprint

bp = Blueprint('demand_projection', __name__, template_folder='templates', url_prefix='/demand_projection')

from app.demand_projection import routes # Import routes after bp is defined
