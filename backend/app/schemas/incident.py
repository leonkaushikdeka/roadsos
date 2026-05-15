from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime


class IncidentInitiateRequest(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    location_accuracy_m: Optional[float] = None
    location_source: str = "gps"
    channel: str = "pwa"
    language: str = "en"
    mode: str = "bystander"
    plus_code: Optional[str] = None
    phone: Optional[str] = None
    victim_count: Optional[int] = 1
    initial_statement: Optional[str] = None


class IncidentInitiateResponse(BaseModel):
    incident_id: str
    session_id: str
    triage_state: str
    first_question: str
    language: str


class TriageRequest(BaseModel):
    incident_id: str
    answer: str
    session_id: Optional[str] = None


class TriageResponse(BaseModel):
    incident_id: str
    next_question: Optional[str] = None
    instruction: Optional[str] = None
    severity: Optional[str] = None
    severity_confidence: Optional[float] = None
    triage_complete: bool = False
    dispatch_options: Optional[dict] = None
    session_complete: bool = False


class DispatchRequest(BaseModel):
    incident_id: str
    service_id: str
    confirm: bool = True


class DispatchResponse(BaseModel):
    incident_id: str
    service_id: str
    service_name: str
    eta_min: int
    status: str
    message: str


class IncidentStatusResponse(BaseModel):
    incident_id: str
    status: str
    severity: Optional[str] = None
    victim_count: Optional[int] = None
    dispatched_services: list[dict] = []
    dispatch_options: Optional[dict] = None
    ambulance_eta_min: Optional[int] = None
    hospital_eta_min: Optional[int] = None
    triage_transcript: list[dict] = []
    started_at: datetime
    closed_at: Optional[datetime] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
