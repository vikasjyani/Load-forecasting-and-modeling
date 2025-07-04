from fastapi import APIRouter

router = APIRouter(
    tags=["Authentication (Placeholder)"],
)

@router.post("/token", summary="Placeholder Login Endpoint")
async def login():
    """
    Placeholder for a login endpoint.
    Currently, this application does not implement actual user authentication
    or role-based access control, as per project requirements.
    This endpoint is defined to fulfill the router structure but performs no
    authentication operations.
    """
    return {"message": "This is a placeholder login endpoint. No authentication is performed."}

# Further notes:
# If any form of user identification were needed for non-auth purposes (e.g., user preferences
# without login), it would be handled via client-provided identifiers or other mechanisms,
# not traditional token-based authentication. The `projects` API currently uses a
# fixed "global_user" ID for features like recent project lists.
