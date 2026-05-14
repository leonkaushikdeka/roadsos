from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class NearbyServicesRequest(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    radius_km: float = Field(default=25, ge=1, le=200)
    service_types: Optional[list[str]] = None
    min_trauma_grade: Optional[int] = None


class ServiceDetail(BaseModel):
    id: str
    name: str
    service_type: str
    trauma_grade: Optional[int] = None
    distance_km: float
    eta_min: int
    phone: Optional[str] = None
    address: Optional[str] = None
    has_icu: bool = False
    has_ventilator: bool = False
    available_beds: Optional[int] = None
    capacity: dict = {}


class NearbyServicesResponse(BaseModel):
    services: list[ServiceDetail]
    total: int


class ServiceStatusResponse(BaseModel):
    service_id: str
    service_name: str
    available_beds: Optional[int] = None
    available_icu_beds: Optional[int] = None
    ambulances_available: Optional[int] = None
    avg_wait_min: Optional[int] = None
    status: str
    last_updated: Optional[datetime] = None
