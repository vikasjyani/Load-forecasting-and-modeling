from flask import Flask
from flask_socketio import SocketIO
from celery import Celery
import os
import logging
from logging.handlers import RotatingFileHandler
# logging.Formatter is not directly imported, accessed via logging.Formatter
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

    # Logging Configuration
    # Ensure BASE_DIR is available in app.config, it's set in Config class
    base_dir = app.config.get('BASE_DIR', os.path.abspath(os.path.dirname(os.path.dirname(__file__)))) # Fallback for BASE_DIR
    logs_dir = os.path.join(base_dir, 'logs')
    if not os.path.exists(logs_dir):
        try:
            os.makedirs(logs_dir)
        except OSError as e:
            # Handle error if logs directory cannot be created, e.g., log to stderr
            app.logger.error(f"Could not create logs directory: {logs_dir}. Error: {e}")


    log_formatter = logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    )

    # File Handler (Rotating)
    # Ensure LOG_FILE path is absolute or correctly relative to a known base directory
    log_file_config_path = app.config.get('LOG_FILE', 'app.log') # Default to app.log in current dir if not set
    if not os.path.isabs(log_file_config_path):
        log_file_path = os.path.join(base_dir, log_file_config_path)
    else:
        log_file_path = log_file_config_path

    # Ensure the directory for the log file exists
    log_file_dir = os.path.dirname(log_file_path)
    if not os.path.exists(log_file_dir):
        try:
            os.makedirs(log_file_dir)
        except OSError as e:
            app.logger.error(f"Could not create directory for log file: {log_file_dir}. Error: {e}")


    if os.path.exists(log_file_dir) and os.access(log_file_dir, os.W_OK): # Check if log file dir is writable
        file_handler = RotatingFileHandler(
            log_file_path,
            maxBytes=app.config.get('LOG_ROTATING_FILE_MAX_BYTES', 1024*1024*10), # 10MB default
            backupCount=app.config.get('LOG_ROTATING_FILE_BACKUP_COUNT', 5)
        )
        file_handler.setFormatter(log_formatter)
        file_handler.setLevel(getattr(logging, app.config.get('LOG_LEVEL_FILE', 'INFO').upper(), logging.INFO))
        app.logger.addHandler(file_handler)
    else:
        app.logger.warning(f"Log file directory {log_file_dir} is not writable or does not exist. File logging disabled.")


    # Stream Handler (Console) - only if configured or in debug mode
    if app.config.get('LOG_TO_STDOUT', app.debug):
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(log_formatter)
        stream_handler.setLevel(getattr(logging, app.config.get('LOG_LEVEL_STDOUT', 'DEBUG').upper(), logging.DEBUG))
        app.logger.addHandler(stream_handler)

    # Set overall app logger level
    # This should be the lowest level of its handlers to allow handlers to filter effectively
    app.logger.setLevel(logging.DEBUG)
    # Remove Flask's default handler if it was added to avoid duplicate console logs with custom StreamHandler
    # This check is important: app.logger.handlers might be empty if Flask hasn't added one yet.
    if len(app.logger.handlers) > 1 and isinstance(app.logger.handlers[0], logging.StreamHandler) and app.logger.handlers[0].formatter is None:
         # Heuristic: Flask's default handler is often a StreamHandler without a specific formatter set early on
         # Or, if we know Flask adds one by default and we always add ours, remove it.
         # For a more robust way: Flask's default handler is usually added when app.run(debug=True) is called
         # or if app.debug is True. It logs to stderr.
         # If we add our own stream handler, we might get duplicates if Flask also adds one.
         # A common pattern is to clear existing handlers if taking full control:
         # for handler in app.logger.handlers[:]:
         #    app.logger.removeHandler(handler)
         # Then add file_handler and stream_handler.
         # For now, we assume this configuration happens early enough.
         # If duplicate console logs are observed, explicitly removing default handlers would be the fix.
         pass


    app.logger.info("KSEB Platform logging initialized.")
    if os.path.exists(log_file_dir) and os.access(log_file_dir, os.W_OK) :
      app.logger.info(f"Log file: {log_file_path}")
    # End Logging Configuration

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
