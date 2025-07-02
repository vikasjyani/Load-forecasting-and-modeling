"""
Pydantic models related to authentication and authorization.

Note: Authentication and authorization are currently out of scope
as per project requirements. This file is a placeholder.
"""
from pydantic import BaseModel

# No models defined here for now.
# If basic user identification (e.g., for logging) is needed later
# without full auth, models can be added here.

# Example (if needed later for simple API key identification):
# class APIKeyUser(BaseModel):
#     client_id: str
#     project_name: Optional[str] = None
pass
