from pydantic import BaseModel


class ConstellationRequest(BaseModel):
    constellation: str
    date: str
    time: str
    latitude: float
    longitude: float


class ConstellationResponse(BaseModel):
    constellation: str
    observable: bool
    altitude: float
    azimuth: float
    direction: str