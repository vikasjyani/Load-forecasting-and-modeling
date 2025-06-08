from flask import Flask
from flask_socketio import SocketIO # Added import
from celery import Celery # Added import
import os
from config import Config

# Initialize extensions globally but configure them within create_app
# These are initialized here so they can be imported by other modules if necessary,
# e.g., tasks.py for Celery.
celery = Celery(__name__, broker=Config.CELERY_BROKER_URL, backend=Config.CELERY_RESULT_BACKEND)
socketio = SocketIO()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure project root and user data directories exist
    # Also ensure the default user data path exists for user_settings
    os.makedirs(app.config['PROJECT_ROOT_ABS'], exist_ok=True)
    default_user_data_path = os.path.join(app.config['USER_DATA_DIR_ABS'], 'default')
    os.makedirs(default_user_data_path, exist_ok=True) # Ensures users/default exists

    # Configure extensions with the app instance
    celery.conf.update(
        broker_url=app.config['CELERY_BROKER_URL'],
        result_backend=app.config['CELERY_RESULT_BACKEND']
        # Add other Celery configurations from app.config if needed
    )
    # In a real setup, you might have a more complex Celery setup,
    # but this aligns with celery.init_app(app) pattern by updating conf.
    # A common pattern is also to have a celery_app.py and import it.
    # For now, this simple configuration update is fine.

    socketio.init_app(app)

    # Register blueprints
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    from app.demand_projection import bp as demand_projection_bp
    app.register_blueprint(demand_projection_bp)

    from app.load_profile import bp as load_profile_bp
    app.register_blueprint(load_profile_bp)

    from app.pypsa_modeling import bp as pypsa_modeling_bp
    app.register_blueprint(pypsa_modeling_bp)

    from app.admin import bp as admin_bp
    app.register_blueprint(admin_bp)

    @app.context_processor
    def inject_project_details():
        return dict(
            current_project_name_g=app.config.get('CURRENT_PROJECT_NAME'),
            current_project_folder_g=app.config.get('CURRENT_PROJECT_FOLDER'),
            current_project_path_abs_g=app.config.get('CURRENT_PROJECT_PATH_ABS')
        )

    return app
