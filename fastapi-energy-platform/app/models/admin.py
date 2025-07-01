from pydantic import BaseModel

class Admin(BaseModel):
    id: int
    username: str
