from pydantic import BaseModel

class DemandProjection(BaseModel):
    id: int
    timestamp: str
    value: float

class DemandVisualization(BaseModel):
    id: int
    type: str
    data: dict
