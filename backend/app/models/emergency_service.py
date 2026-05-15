import uuid
from datetime import datetime
from sqlalchemy import Column, String, SmallInteger, Boolean, DateTime, JSON, Float, ForeignKey, PrimaryKeyConstraint
from app.database import Base


class EmergencyService(Base):
    __tablename__ = "emergency_services"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200), nullable=False)
    service_type = Column(String(20), nullable=False, index=True)
    sub_type = Column(String(40), nullable=True)
    trauma_grade = Column(SmallInteger, nullable=True)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    address = Column(String(500), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(40), nullable=True)
    country = Column(String(40), default="India")
    phone = Column(String(20), nullable=True)
    alternate_phone = Column(String(20), nullable=True)
    capacity = Column(JSON, default=dict)
    has_icu = Column(Boolean, default=False)
    has_ventilator = Column(Boolean, default=False)
    has_blood_bank = Column(Boolean, default=False)
    has_trauma_team = Column(Boolean, default=False)
    is_24x7 = Column(Boolean, default=True)
    verified = Column(Boolean, default=False)
    last_verified_at = Column(DateTime, nullable=True)
    source = Column(String(40), default="osm")
    created_at = Column(DateTime, default=datetime.utcnow)


class ServiceStatus(Base):
    __tablename__ = "service_status"

    service_id = Column(String, ForeignKey("emergency_services.id"), primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, primary_key=True)
    available_beds = Column(SmallInteger, default=0)
    available_icu_beds = Column(SmallInteger, default=0)
    available_ventilators = Column(SmallInteger, default=0)
    avg_wait_min = Column(SmallInteger, nullable=True)
    ambulances_available = Column(SmallInteger, nullable=True)
    status = Column(String(20), default="unknown")
