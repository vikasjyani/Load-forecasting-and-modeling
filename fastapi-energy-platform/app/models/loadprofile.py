from pydantic import BaseModel

class LoadProfile(BaseModel):
    id: int
    name: str
    data: list[float]

class LoadProfileAnalysis(BaseModel):
    id: int
    profile_id: int
    result: dict
