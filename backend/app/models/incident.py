import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, JSON, ARRAY, Float, ForeignKey, Text, Boolean, BigInteger
from app.database import Base


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    initiated_by = Column(String, ForeignKey("users.id"), nullable=True)
    session_id = Column(String(40), unique=True, nullable=True, index=True)

    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    plus_code = Column(String(20), nullable=True)
    what3words = Column(String(60), nullable=True)
    location_accuracy_m = Column(Float, nullable=True)
    location_source = Column(String(20), default="gps")

    severity = Column(String(10), nullable=True)
    severity_confidence = Column(Float, nullable=True)
    victim_count = Column(Integer, default=1)
    mechanism = Column(String(100), nullable=True)

    started_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)
    ambulance_eta_min = Column(Integer, nullable=True)
    hospital_eta_min = Column(Integer, nullable=True)

    dispatched_services = Column(JSON, default=list)
    notified_contacts = Column(JSON, default=list)
    triage_transcript = Column(JSON, default=list)
    photos = Column(JSON, default=list)
    audio_clips = Column(JSON, default=list)

    channel = Column(String(20), default="pwa")
    language = Column(String(8), default="en")
    mode = Column(String(10), default="bystander")

    status = Column(String(20), default="active", index=True)
    human_escalated = Column(Boolean, default=False)
    fraud_metadata = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


class TriageEntry(Base):
    __tablename__ = "triage_entries"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String, ForeignKey("incidents.id"), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=True)
    intent = Column(String(40), nullable=True)
    step = Column(String(40), nullable=True)
    confidence = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class DispatchAudit(Base):
    __tablename__ = "dispatch_audit"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    incident_id = Column(String, ForeignKey("incidents.id"), nullable=False)
    decision = Column(JSON, nullable=False)
    llm_confidence = Column(Float, nullable=True)
    human_override = Column(Boolean, default=False)
    decided_at = Column(DateTime, default=datetime.utcnow)
