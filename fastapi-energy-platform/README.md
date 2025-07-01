# FastAPI Energy Platform Backend

This directory contains the backend service for the Energy Platform, built with FastAPI.

## Project Structure

```
fastapi-energy-platform/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py              # Configuration settings
│   ├── dependencies.py        # Dependency injection
│   ├── middleware.py          # Custom middleware
│   │
│   ├── api/                   # API routes
│   │   ├── __init__.py
│   │   ├── v1/                # API version 1
│   │   │   ├── __init__.py
│   │   │   ├── admin.py       # Admin routes
│   │   │   ├── auth.py        # Authentication
│   │   │   └── ...            # Other route modules
│   │   └── router.py          # Main API router (aggregates v1, v2, etc.)
│   │
│   ├── models/                # Pydantic models for request/response validation
│   │   ├── __init__.py
│   │   └── ...
│   │
│   ├── services/              # Business logic
│   │   ├── __init__.py
│   │   └── ...
│   │
│   ├── core/                  # Core utilities (DB, security, etc.)
│   │   ├── __init__.py
│   │   └── ...
│   │
│   └── utils/                 # General utilities
│       ├── __init__.py
│       └── ...
│
├── models/                    # ML/Analysis models and related code (e.g., forecasting)
│   ├── __init__.py
│   └── ...
│
├── tests/                     # Tests for the application
│   ├── __init__.py
│   ├── test_api/
│   ├── test_services/
│   └── conftest.py            # Pytest configuration
│
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Docker configuration for the backend
├── docker-compose.yml         # Docker Compose for multi-container setup (backend, db, etc.)
└── README.md                  # This file
```

## Setup and Running

### Prerequisites
- Python 3.8+
- Docker (optional, for containerized deployment)
- pip (Python package installer)

### Local Development (without Docker)

1.  **Create a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the application:**
    The `main.py` file uses `uvicorn` to serve the application.
    ```bash
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    ```
    The `--reload` flag enables auto-reloading on code changes. The application will be available at `http://localhost:8000`.

### With Docker

1.  **Build and run using Docker Compose:**
    This is the recommended way if you plan to use other services like a database.
    ```bash
    docker-compose up --build
    ```
    The application will be available at `http://localhost:8000` (or as configured in `docker-compose.yml`).

2.  **Build and run using Docker directly (for the backend only):**
    ```bash
    docker build -t fastapi-energy-backend .
    docker run -p 8000:80 fastapi-energy-backend
    ```

## API Documentation

Once the application is running, API documentation (Swagger UI) is automatically available at `http://localhost:8000/docs`.
Alternative ReDoc documentation is at `http://localhost:8000/redoc`.

## Testing

Tests are located in the `tests/` directory and use `pytest`.

1.  **Install test dependencies (if not already installed):**
    You might need to add `pytest` and other testing libraries to `requirements.txt` or a `requirements-dev.txt`.
    ```bash
    pip install pytest httpx # httpx for async testing
    ```

2.  **Run tests:**
    Navigate to the `fastapi-energy-platform` directory.
    ```bash
    pytest
    ```

## Environment Variables

Configuration can be managed via environment variables (e.g., for database URLs, secret keys). These can be defined in a `.env` file (and loaded using a library like `python-dotenv` in `config.py`) or set directly in your environment/`docker-compose.yml`.

Example (`.env` file - make sure to add `.env` to `.gitignore`):
```
DATABASE_URL="postgresql://user:password@localhost:5432/energydb"
SECRET_KEY="your_very_secret_key"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

Refer to `app/config.py` for how these variables are loaded and used.
