from fastapi import APIRouter

router = APIRouter()

@router.post("/token")
async def login():
    return {"message": "Login"}
