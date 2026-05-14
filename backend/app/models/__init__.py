from app.models.user import User
from app.models.emergency_service import EmergencyService, ServiceStatus
from app.models.incident import Incident, TriageEntry, DispatchAudit
from app.models.protocol import ProtocolChunk
from app.models.fraud import AbuseTracker, IncidentFingerprint, FraudAlert, RateLimitBucket

all_models = [
    User, EmergencyService, ServiceStatus,
    Incident, TriageEntry, DispatchAudit, ProtocolChunk,
    AbuseTracker, IncidentFingerprint, FraudAlert, RateLimitBucket,
]
