# utils/constants.py
"""
Shared constants for the KSEB Energy Futures Platform
"""

# COVID years for exclusion in forecasting
COVID_YEARS = [2021, 2022]

# Default forecast parameters
DEFAULT_TARGET_YEAR = 2037
DEFAULT_START_YEAR = 2006
DEFAULT_WINDOW_SIZE = 10

# File extensions and limits
ALLOWED_EXTENSIONS = {'xlsx', 'csv', 'json'}
MAX_FILE_SIZE = 200 * 1024 * 1024  # 200MB

# Unit conversion factors (base unit: kWh)
UNIT_FACTORS = {
    'TWh': 1000000000,
    'GWh': 1000000,
    'MWh': 1000,
    'kWh': 1
}

# Model types
FORECAST_MODELS = ['MLR', 'SLR', 'WAM', 'TimeSeries']

# Project structure - This might be managed differently in FastAPI (e.g. dynamic paths)
# Consider if this is still needed or how it translates.
PROJECT_STRUCTURE = {
    'inputs': {},
    'results': {
        'demand_projection': {},
        'load_profiles': {},
        'PyPSA_Modeling': {},
        'Pypsa_results': {}
    },
    'logs': {},
    'config': {}
}

# File templates - Paths might need to be relative to a base resource/template directory
TEMPLATE_FILES = {
    'input_demand_file.xlsx': 'input_demand_file.xlsx',
    'load_curve_template.xlsx': 'load_curve_template.xlsx',
    'pypsa_input_template.xlsx': 'pypsa_input_template.xlsx',
    'load_profile.xlsx': 'load_profile.xlsx'
    # Note: 'input_demand_file.xlsx' was listed twice in the original
}

# Excel sheet names
REQUIRED_SHEETS = {
    'INPUTS': 'Inputs',
    'RESULTS': 'Results',
    'CORRELATIONS': 'Correlations',
    'TEST_RESULTS': 'Test Results',
    'INDEPENDENT_PARAMS': 'Independent Parameters',
    'MAIN': 'main',
    'ECONOMIC_INDICATORS': 'Economic_Indicators'
}

# API response status - FastAPI typically uses HTTP status codes directly.
# This mapping might be useful for internal logic or specific response structures.
API_STATUS = {
    'SUCCESS': 'success',
    'ERROR': 'error',
    'WARNING': 'warning',
    'INFO': 'info'
}

# Forecast job statuses
JOB_STATUS = {
    'STARTING': 'starting',
    'RUNNING': 'running',
    'COMPLETED': 'completed',
    'FAILED': 'failed',
    'CANCELLED': 'cancelled',
    'QUEUED': 'queued'
}

# Time limits (in seconds)
MAX_JOB_RUNTIME = 3600  # 1 hour
CLEANUP_INTERVAL = 300  # 5 minutes
POLLING_INTERVAL = 2500  # 2.5 seconds (consider if this is frontend or backend concern)
MAX_POLLING_RETRIES = 10 # (consider if this is frontend or backend concern)
JOB_TIMEOUT = 1800  # 30 minutes

# Correlation strength thresholds
CORRELATION_THRESHOLDS = {
    'STRONG': 0.7,
    'MODERATE': 0.4,
    'WEAK': 0.0
}

# Chart colors for sectors - MOVED to frontend constants.js
# SECTOR_COLORS = [...]

# Model colors for charts - MOVED to frontend constants.js
# MODEL_COLORS = { ... }

# Validation rules
VALIDATION_RULES = {
    'MIN_DATA_POINTS': 2,
    'MIN_TRAINING_SIZE': 0.7, # Percentage
    'MIN_WINDOW_SIZE': 2,
    'MAX_WINDOW_SIZE': 50,
    'MAX_INDEPENDENT_VARS': 20,
    'MIN_YEAR': 1990,
    'MAX_YEAR': 2100
}

# Default configuration - These should ideally be managed by app.config.py using Pydantic BaseSettings
DEFAULT_CONFIG = {
    'FY_START_MONTH': 4,
    'EXCLUDE_COVID': True,
    'DEFAULT_MODELS': ['WAM'],
    'AUTO_SAVE': True, # This might be a per-user or per-project setting
    'DEBUG_MODE': False, # Controlled by FastAPI/Uvicorn settings usually
    'LOG_LEVEL': 'INFO' # Controlled by logging configuration usually
}

# Path constants - These need to be re-evaluated for a FastAPI structure.
# Paths for user data, templates etc. should be configurable (e.g. via config.py)
# and not hardcoded as string literals relative to where the script *might* be run.
# Example:
# from pathlib import Path
# BASE_DIR = Path(__file__).resolve().parent.parent # This would be app/
# PROJECT_DATA_ROOT = BASE_DIR / "data" / "projects" # Example
DEFAULT_PATHS = {
    'PROJECT_ROOT': 'projects', # Relative path, needs context.
    'TEMPLATE_FOLDER': 'static/templates', # Old static path, for FastAPI this would be different
    'UPLOAD_FOLDER': 'static/user_uploads', # Old static path
    'LOGS_FOLDER': 'logs' # Relative path for logs
}

# Error messages - Useful for consistent API error responses
ERROR_MESSAGES = {
    'NO_PROJECT': 'Please select or create a project first.',
    'FILE_NOT_FOUND': 'Required file not found.',
    'INVALID_FILE': 'Invalid file format or content.',
    'PROCESSING_ERROR': 'Error processing data.',
    'VALIDATION_FAILED': 'Data validation failed.',
    'UNAUTHORIZED': 'Unauthorized access.'
}

# Success messages - Useful for consistent API success responses
SUCCESS_MESSAGES = {
    'PROJECT_CREATED': 'Project created successfully.',
    'PROJECT_LOADED': 'Project loaded successfully.',
    'FILE_UPLOADED': 'File uploaded successfully.',
    'DATA_PROCESSED': 'Data processed successfully.',
    'FORECAST_COMPLETED': 'Forecast completed successfully.'
}

print("Defining constants... (merged from old_constants.py)")
