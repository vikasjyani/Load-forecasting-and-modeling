from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import List, Optional, Any
from pathlib import Path
import os

# Define paths at module level to avoid issues with `Settings()` recursion in default_factory
_CONFIG_FILE_PATH = Path(__file__).resolve()
_APP_DIR_PATH = _CONFIG_FILE_PATH.parent  # .../app
_PROJECT_DIR_PATH = _APP_DIR_PATH.parent    # .../fastapi-energy-platform (assuming this is the project root)
_PROJECT_PARENT_DIR_PATH = _PROJECT_DIR_PATH.parent # Directory containing the project directory

# Default paths based on the new structure
DEFAULT_PROJECT_DATA_ROOT: Path = _PROJECT_PARENT_DIR_PATH / "data" / "projects"
DEFAULT_LOGS_DIR: Path = _PROJECT_DIR_PATH / "logs" # e.g., fastapi-energy-platform/logs
DEFAULT_TEMP_UPLOAD_DIR: Path = _PROJECT_DIR_PATH / "temp_uploads" # e.g., fastapi-energy-platform/temp_uploads
DEFAULT_GLOBAL_FEATURES_CONFIG: Path = _APP_DIR_PATH / "data" / "admin" / "features_config.json" # e.g., fastapi-energy-platform/app/data/admin/features_config.json


class Settings(BaseSettings):
    """
    Application settings, loaded from environment variables and/or .env file.
    """
    APP_NAME: str = Field("FastAPI Energy Platform", description="The name of the application.")
    APP_VERSION: str = Field("0.1.0", description="The version of the application.")
    APP_DESCRIPTION: Optional[str] = Field("A FastAPI platform for energy analysis and forecasting.", description="A brief description of the application.")
    API_V1_PREFIX: str = Field("/api/v1", description="The prefix for version 1 of the API.")

    # Logging configuration
    LOG_LEVEL: str = Field("INFO", description="Logging level (e.g., DEBUG, INFO, WARNING, ERROR, CRITICAL).")

    # Application root directory, useful for deriving other paths
    APP_ROOT: Path = _APP_DIR_PATH # Expose _APP_DIR_PATH as settings.APP_ROOT

    PROJECT_DATA_ROOT: Path = Field(
        default_factory=lambda: DEFAULT_PROJECT_DATA_ROOT,
        description="The root directory for storing all project-related data and files. "
                    "It's highly recommended to set this via an environment variable for production deployments."
    )

    # CORS (Cross-Origin Resource Sharing)
    ALLOWED_ORIGINS: List[str] = Field(default=["http://localhost", "http://localhost:3000", "http://localhost:5173"], description="List of allowed origins for CORS.")

    # PyPSA Specific Settings
    PYPSA_NETWORK_CACHE_SIZE: int = Field(default=3, ge=1, le=10, description="Maximum number of PyPSA networks to keep in in-memory cache.")

    # Paths that AdminService and other services might use, derived from module-level constants
    GLOBAL_FEATURES_CONFIG_PATH: Path = Field(default_factory=lambda: DEFAULT_GLOBAL_FEATURES_CONFIG)
    LOG_DIR: Path = Field(default_factory=lambda: DEFAULT_LOGS_DIR) # Renamed from LOGS_DIR for consistency with admin_service
    TEMP_UPLOAD_DIR: Path = Field(default_factory=lambda: DEFAULT_TEMP_UPLOAD_DIR)

    # Pydantic settings configuration
    model_config = SettingsConfigDict(
        env_file=".env",  # Load .env file if it exists
        env_file_encoding='utf-8',
        extra='ignore',  # Ignore extra fields from .env or environment
        case_sensitive=False # Environment variable names are case-insensitive by default on some systems
    )

    def __init__(self, **values: Any):
        super().__init__(**values)
        # Ensure project data root directory exists after initialization
        # This is a side effect, consider if it's best here or in app startup.
        # For now, it's convenient for development.
        if not self.PROJECT_DATA_ROOT.exists():
            try:
                self.PROJECT_DATA_ROOT.mkdir(parents=True, exist_ok=True)
                print(f"Created project data root directory: {self.PROJECT_DATA_ROOT}")
            except Exception as e:
                print(f"Warning: Could not create project data root directory {self.PROJECT_DATA_ROOT}: {e}")
        elif not os.access(str(self.PROJECT_DATA_ROOT), os.W_OK):
             print(f"Warning: Project data root directory {self.PROJECT_DATA_ROOT} is not writable.")


# Instantiate settings
# This instance will be imported by other modules.
settings = Settings()

# For debugging or verification during startup:
# print(f"Loading configuration for app: {settings.APP_NAME} v{settings.APP_VERSION}")
# print(f"Project data root: {settings.PROJECT_DATA_ROOT}")
# print(f"Log level: {settings.LOG_LEVEL}")

# Ensure necessary imports are available if this file is run directly (though it shouldn't be)
from typing import Any # Add this if not already present from pydantic or other imports
from pathlib import Path # Add this if not already present

# A check to ensure PROJECT_DATA_ROOT is correctly resolved, especially if default is used.
if settings.PROJECT_DATA_ROOT == DEFAULT_PROJECT_DATA_ROOT: # Compare with the module-level constant
    print(f"Using default project data root: {settings.PROJECT_DATA_ROOT}")
    if not settings.PROJECT_DATA_ROOT.is_absolute():
        print(f"Warning: Default project data root '{settings.PROJECT_DATA_ROOT}' is not an absolute path. "
              "This might lead to unexpected behavior depending on the working directory. "
              "Consider setting PROJECT_DATA_ROOT environment variable to an absolute path.")

print("Configuration loaded successfully.")
# Remove the initial print statement from the old file
# print("Loading configuration...")
