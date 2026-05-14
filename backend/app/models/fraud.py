"""
Fraud & abuse tracking models.

Records suspicious activity, threat scores, and incident fingerprints
to prevent false SOS abuse and protect emergency resources.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Float, JSON, BigInteger, Integer, ForeignKey, Boolean, Index
from sqlalchemy.dialects.postgresql import INET, UUID
from app.database import Base


class AbuseTracker(Base):
    """
    Tracks devices / phone numbers that have triggered false or suspicious incidents.
    """
    __tablename__ = "abuse_trackers"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    phone = Column(String(20), nullable=True, index=True)
    device_fingerprint = Column(String(128), nullable=True, index=True)
    ip_address = Column(INET, nullable=True)

    incident_count = Column(Integer, default=0)
    false_positive_count = Column(Integer, default=0)
    threat_score = Column(Float, default=0.0)  # 0.0 (clean) to 100.0 (banned)

    is_banned = Column(Boolean, default=False)
    banned_until = Column(DateTime, nullable=True)
    ban_reason = Column(String(500), nullable=True)

    last_incident_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_abuse_phone_fp", "phone", "device_fingerprint"),
        Index("idx_abuse_threat", "threat_score"),
    )


class IncidentFingerprint(Base):
    """
    Stores a hash of incident characteristics to detect duplicates
    (same GPS cluster, same time window, same caller).
    """
    __tablename__ = "incident_fingerprints"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    incident_id = Column(String, ForeignKey("incidents.id"), nullable=True, index=True)
    fingerprint_hash = Column(String(128), nullable=False, index=True)  # SHA-256 hex digest
    location_grid = Column(String(20), nullable=True)  # Geohash prefix (6-char)
    caller_phone = Column(String(20), nullable=True)
    incident_started_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_finger_hash", "fingerprint_hash"),
        Index("idx_finger_grid_time", "location_grid", "incident_started_at"),
    )


class FraudAlert(Base):
    """
    Alerts generated when fraud patterns are detected.
    """
    __tablename__ = "fraud_alerts"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    incident_id = Column(String, ForeignKey("incidents.id"), nullable=True)
    tracker_id = Column(String, ForeignKey("abuse_trackers.id"), nullable=True)
    alert_type = Column(String(40), nullable=False)  # 'rate_limit', 'duplicate', 'geo_velocity', 'pattern_match'
    severity = Column(String(10), nullable=False)    # 'low', 'medium', 'high', 'critical'
    description = Column(String(500), nullable=True)
    evidence = Column(JSON, default=dict)            # Supporting data for review
    reviewed = Column(Boolean, default=False)
    reviewed_by = Column(String, nullable=True)
    action_taken = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class RateLimitBucket(Base):
    """
    Sliding-window rate limit tracking per user/device/IP.
    """
    __tablename__ = "rate_limit_buckets"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    bucket_key = Column(String(128), nullable=False, index=True)  # "phone:xxx" / "device:xxx" / "ip:xxx"
    request_times = Column(JSON, default=list)  # List of ISO timestamps
    reset_at = Column(DateTime, nullable=True)
    is_blocked = Column(Boolean, default=False)
    blocked_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)