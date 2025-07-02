import logging
import sys
from app.config import settings # Import your application settings

# Standard log format
LOG_FORMAT = "%(asctime)s - %(levelname)s - [%(name)s] - [%(filename)s:%(lineno)d] - (%(process)d) - %(threadName)s - %(message)s"
# Simpler format for production if preferred:
# LOG_FORMAT_PROD = "%(asctime)s - %(levelname)s - [%(name)s] - %(message)s"

# JSON logging (optional, requires python-json-logger)
# from pythonjsonlogger import jsonlogger
# class CustomJsonFormatter(jsonlogger.JsonFormatter):
#     def add_fields(self, log_record, record, message_dict):
#         super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
#         if not log_record.get('timestamp'):
#             log_record['timestamp'] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
#         if log_record.get('level'):
#             log_record['level'] = log_record['level'].upper()
#         else:
#             log_record['level'] = record.levelname

def setup_logging():
    """
    Configures the application's logging system.
    Sets the log level from application settings and applies a standard format.
    """
    log_level_str = settings.LOG_LEVEL.upper()
    log_level = getattr(logging, log_level_str, logging.INFO) # Default to INFO if invalid

    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove any existing handlers from the root logger to avoid duplicate logs
    # This is important if this function might be called multiple times or if uvicorn adds its own.
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # Configure a stream handler (console output)
    console_handler = logging.StreamHandler(sys.stdout) # Use sys.stdout for compatibility (e.g. Docker logs)
    formatter = logging.Formatter(LOG_FORMAT)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level) # Set level on handler as well

    root_logger.addHandler(console_handler)

    # Configure logging for specific libraries if needed (e.g., uvicorn, sqlalchemy)
    # Example: Quieten uvicorn access logs if they are too verbose or handled by our middleware log
    # logging.getLogger("uvicorn.access").setLevel(logging.WARNING) # Or propagate=False and handle elsewhere
    logging.getLogger("uvicorn.access").handlers.clear() # Remove default uvicorn access handler if our middleware logs requests
    logging.getLogger("uvicorn.access").propagate = True # Let our root handler catch it if needed, or set specific handler

    logging.getLogger("uvicorn.error").setLevel(log_level) # Ensure uvicorn errors also respect our level
    logging.getLogger("uvicorn.error").propagate = True


    # If using JSON logging:
    # logHandler = logging.StreamHandler()
    # formatter = CustomJsonFormatter('%(timestamp)s %(level)s %(name)s %(message)s')
    # logHandler.setFormatter(formatter)
    # root_logger.addHandler(logHandler)
    # root_logger.setLevel(log_level)

    # Log that logging has been configured
    # Use a distinct logger name for this initial message if desired
    # init_logger = logging.getLogger(f"{settings.APP_NAME}.init")
    # init_logger.info(f"Logging configured. Level: {log_level_str}. Format: Standard Text.")
    # Or just use the root logger:
    logging.info(f"Logging configured by application. Level: {log_level_str}. Root logger handlers: {root_logger.handlers}")


# Call setup_logging here if you want it to be configured as soon as this module is imported.
# However, it's often better to call it explicitly from main.py or your app factory
# to ensure settings are fully loaded and to have more control over initialization order.
# For this project, we will call it from main.py.

print("Logging module (app/core/logging.py) loaded. Call setup_logging() to initialize.")
# Remove old print statement
# print("Defining logging configuration...")
