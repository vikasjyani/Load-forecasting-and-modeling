from pydantic import BaseModel

class CoreModel(BaseModel):
    id: int
    name: str
