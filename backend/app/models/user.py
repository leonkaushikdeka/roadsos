import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, JSON, Boolean
from geoalchemy2 import Geography
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    phone = Column(String(20), unique=True, nullable=True, index=True)
    name = Column(String(100), nullable=True)
    preferred_lang = Column(String(8), default="en")
    ice_contacts = Column(JSON, default=list)
    blood_group = Column(String(4), nullable=True)
    allergies = Column(String(500), nullable=True)
    medical_conditions = Column(String(500), nullable=True)
    default_location = Column(Geography(geometry_type="POINT", srid=4326), nullable=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
