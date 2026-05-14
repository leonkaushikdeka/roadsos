from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class UserCreate(BaseModel):
    phone: str
    name: Optional[str] = None
    preferred_lang: str = "en"
    ice_contacts: Optional[list[dict]] = None
    blood_group: Optional[str] = None
    allergies: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    phone: Optional[str] = None
    name: Optional[str] = None
    preferred_lang: str
    ice_contacts: list = []
    created_at: datetime
