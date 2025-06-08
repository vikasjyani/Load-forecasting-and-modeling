import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    PROJECT_ROOT_NAME = 'projects'
    PROJECT_ROOT_ABS = os.path.join(BASE_DIR, PROJECT_ROOT_NAME)
    USER_DATA_DIR_NAME = 'users'
    USER_DATA_DIR_ABS = os.path.join(BASE_DIR, USER_DATA_DIR_NAME)
    CURRENT_PROJECT_NAME = None
    CURRENT_PROJECT_FOLDER = None
    CURRENT_PROJECT_PATH_ABS = None
    CELERY_BROKER_URL = 'redis://localhost:6379/0'  # Placeholder
    CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'  # Placeholder
