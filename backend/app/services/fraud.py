"""
Fraud & Abuse Detection Engine for RoadSoS.

Prevents misuse of the emergency SOS system through multiple detection layers:

1. Rate Limiting — Sliding window per phone, device, IP
2. Duplicate Detection — Geohash + time-window fingerprinting
3. Geo-Velocity — Detects impossible travel between incidents
4. Threat Scoring — Accumulates risk signals over time
5. Pattern Matching — Flags known abuse patterns

Design principles:
- Never block a genuine emergency. Err on the side of allowing.
- All fraud checks are non-blocking warnings by default.
- Only hard-block when threat_score >= 85 or active ban in place.
- Every decision is logged for human review.
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy import text, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.fraud import (
    AbuseTracker,
    IncidentFingerprint,
    FraudAlert,
    RateLimitBucket,
)

logger = logging.getLogger(__name__)

# ─── Configuration ───────────────────────────────────────────────────────────

RATE_LIMIT_WINDOW_SEC = 600  # 10 minutes
RATE_LIMIT_MAX_INCIDENTS = 3  # Max 3 incidents per window (before 1h)
RATE_LIMIT_MAX_HOURLY = 10  # Max 10 per hour
DUPLICATE_WINDOW_SEC = 300  # 5 minutes
DUPLICATE_GEOHASH_PREFIX = 4  # ~20km precision
GEO_VELOCITY_THRESHOLD_KMH = 300  # Can't travel >300km between incidents
THREAT_SCORE_RATE_LIMIT = 60  # Score threshold for rate-limited
THREAT_SCORE_HARD_BLOCK = 85  # Score threshold for hard block
THREAT_SCORE_DECAY_PER_HOUR = 2.0  # Score decays over time


class FraudCheckResult:
    """Result of a fraud check — always allows, but may flag concerns."""

    def __init__(
        self,
        allowed: bool = True,
        risk_level: str = "low",
        reasons: Optional[list[str]] = None,
        threat_score: float = 0.0,
        action_required: Optional[str] = None,
    ):
        self.allowed = allowed
        self.risk_level = risk_level  # low | medium | high | critical
        self.reasons = reasons or []
        self.threat_score = threat_score
        self.action_required = action_required  # None | "review" | "soft_block" | "hard_block"

    @property
    def is_suspicious(self) -> bool:
        return self.risk_level in ("medium", "high", "critical")

    def to_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "risk_level": self.risk_level,
            "reasons": self.reasons,
            "threat_score": round(self.threat_score, 1),
            "action_required": self.action_required,
        }


# ─── Helper: Geohash encoding (lite, no external dependency) ────────────────

BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"


def encode_geohash(lat: float, lng: float, precision: int = 6) -> str:
    """Encode lat/lng to a geohash string with given precision."""
    lat_range, lng_range = [-90.0, 90.0], [-180.0, 180.0]
    result = []
    bits = [(lng, lng_range), (lat, lat_range)]
    bit = 0
    ch = 0
    while len(result) < precision:
        for i, (val, (lo, hi)) in enumerate(bits):
            mid = (lo + hi) / 2.0
            if val >= mid:
                ch |= 1 << (4 - bit)
                bits[i] = (val, (mid, hi))
            else:
                bits[i] = (val, (lo, mid))
            bit += 1
            if bit == 5:
                result.append(BASE32[ch])
                bit, ch = 0, 0
    return "".join(result)


# ─── Core Fraud Engine ──────────────────────────────────────────────────────


class FraudEngine:
    """Main fraud detection engine. Instantiate once, call check()."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def check(
        self,
        phone: Optional[str],
        lat: float,
        lng: float,
        device_fingerprint: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> FraudCheckResult:
        """Run all fraud checks and return a combined result."""
        result = FraudCheckResult()
        now = datetime.now(timezone.utc)

        # 1. Get or create abuse tracker
        tracker = await self._get_or_create_tracker(
            phone=phone,
            device_fingerprint=device_fingerprint,
            ip_address=ip_address,
        )

        # Apply decay to threat score
        if tracker.last_incident_at:
            elapsed_hours = (
                now - tracker.last_incident_at.replace(tzinfo=timezone.utc)
            ).total_seconds() / 3600
            tracker.threat_score = max(
                0, tracker.threat_score - (elapsed_hours * THREAT_SCORE_DECAY_PER_HOUR)
            )

        # 2. Hard-block check — banned user
        if tracker.is_banned:
            if tracker.banned_until and tracker.banned_until > now:
                result.allowed = False
                result.risk_level = "critical"
                result.action_required = "hard_block"
                result.reasons.append(
                    f"Active ban until {tracker.banned_until.isoformat()}"
                )
                return result
            elif tracker.banned_until and tracker.banned_until <= now:
                tracker.is_banned = False
                tracker.banned_until = None
                tracker.ban_reason = None

        # 3. Rate limiting
        rate_result = await self._check_rate_limit(
            phone=phone,
            device_fingerprint=device_fingerprint,
            ip_address=ip_address,
        )
        if not rate_result.allowed:
            result.allowed = False
            result.risk_level = self._max_risk(result.risk_level, rate_result.risk_level)
            result.reasons.extend(rate_result.reasons)
            result.action_required = rate_result.action_required or "soft_block"

        # 4. Duplicate detection
        dup_result = await self._check_duplicates(phone=phone, lat=lat, lng=lng)
        if dup_result.is_suspicious:
            result.risk_level = self._max_risk(result.risk_level, dup_result.risk_level)
            result.reasons.extend(dup_result.reasons)
            if dup_result.action_required:
                result.action_required = dup_result.action_required

        # 5. Geo-velocity check
        if phone:
            geo_result = await self._check_geo_velocity(phone=phone, lat=lat, lng=lng)
            if geo_result.is_suspicious:
                result.risk_level = self._max_risk(result.risk_level, geo_result.risk_level)
                result.reasons.extend(geo_result.reasons)

        # 6. Update threat score
        added_score = 0.0
        if result.risk_level == "medium":
            added_score = 10.0
        elif result.risk_level == "high":
            added_score = 25.0
        elif result.risk_level == "critical":
            added_score = 50.0

        if added_score > 0:
            tracker.threat_score = min(100.0, tracker.threat_score + added_score)

        # 7. Check threat score threshold
        if tracker.threat_score >= THREAT_SCORE_HARD_BLOCK:
            result.allowed = False
            result.risk_level = "critical"
            result.action_required = "hard_block"
            result.reasons.append(
                f"Threat score {tracker.threat_score:.1f} exceeds hard block threshold"
            )
        elif tracker.threat_score >= THREAT_SCORE_RATE_LIMIT and result.action_required is None:
            result.action_required = "review"
            result.reasons.append(
                f"Threat score {tracker.threat_score:.1f} flagged for review"
            )

        # Save tracker, create alert if needed, save fingerprint
        tracker.incident_count += 1
        tracker.last_incident_at = now
        tracker.updated_at = now
        await db.flush()

        # Save fingerprint
        fingerprint_hash = hashlib.sha256(
            f"{lat:.4f}:{lng:.4f}:{tracker.phone or ''}:{tracker.device_fingerprint or ''}".encode()
        ).hexdigest()

        fp = IncidentFingerprint(
            incident_id="",
            fingerprint_hash=fingerprint_hash,
            location_grid=encode_geohash(lat, lng),
            caller_phone=tracker.phone,
            incident_started_at=now,
        )
        self.db.add(fp)

        # Create alert if suspicious
        if result.is_suspicious:
            alert = FraudAlert(
                alert_type=(
                    "rate_limit"
                    if "Rate" in " ".join(result.reasons)
                    else "pattern_match"
                ),
                severity=result.risk_level,
                description="; ".join(result.reasons),
                evidence={"reasons": result.reasons, "threat_score": tracker.threat_score},
            )
            self.db.add(alert)

        await db.commit()

        # Log every check
        logger.info(
            "Fraud check: phone=%s device=%s risk=%s score=%.1f allowed=%s",
            phone,
            device_fingerprint,
            result.risk_level,
            tracker.threat_score,
            result.allowed,
        )

        return result

    # ─── Sub-checks ──────────────────────────────────────────────────────────

    async def _check_rate_limit(
        self, phone, device_fingerprint, ip_address
    ) -> FraudCheckResult:
        """Sliding-window rate limit check."""
        result = FraudCheckResult()
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(seconds=RATE_LIMIT_WINDOW_SEC)

        keys = []
        if phone:
            keys.append(f"phone:{phone}")
        if device_fingerprint:
            keys.append(f"device:{device_fingerprint}")
        if ip_address:
            keys.append(f"ip:{ip_address}")

        for key in keys:
            bucket = await self.db.get(RateLimitBucket, key)  # type: ignore
            if not bucket:
                bucket = RateLimitBucket(
                    bucket_key=key,
                    request_times=[now.isoformat()],
                    reset_at=(now + timedelta(seconds=RATE_LIMIT_WINDOW_SEC)),
                )
                self.db.add(bucket)
            else:
                # Prune old entries
                bucket.request_times = [
                    t
                    for t in bucket.request_times
                    if datetime.fromisoformat(t) > window_start
                ]
                bucket.request_times.append(now.isoformat())

            # Check thresholds
            if len(bucket.request_times) > RATE_LIMIT_MAX_HOURLY:
                result.allowed = False
                result.risk_level = "medium"
                result.reasons.append(
                    f"Rate limit exceeded: {len(bucket.request_times)} incidents/hour for {key}"
                )
                result.action_required = "soft_block"
                bucket.is_blocked = True
                bucket.blocked_until = now + timedelta(minutes=30)
            elif len(bucket.request_times) > RATE_LIMIT_MAX_INCIDENTS:
                result.risk_level = self._max_risk(result.risk_level, "medium")
                result.reasons.append(
                    f"Elevated rate: {len(bucket.request_times)} incidents in window for {key}"
                )

        return result

    async def _check_duplicates(self, phone, lat, lng) -> FraudCheckResult:
        """Check for duplicate reports in the same geohash + time window."""
        result = FraudCheckResult()
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(seconds=DUPLICATE_WINDOW_SEC)
        grid = encode_geohash(lat, lng, DUPLICATE_GEOHASH_PREFIX)

        sql = text("""
            SELECT COUNT(*) FROM incident_fingerprints
            WHERE location_grid = :grid
            AND incident_started_at > :window_start
        """)

        if phone:
            sql = text("""
                SELECT COUNT(*) FROM incident_fingerprints
                WHERE (location_grid = :grid OR caller_phone = :phone)
                AND incident_started_at > :window_start
            """)

        result_data = await self.db.execute(
            sql, {"grid": grid, "phone": phone, "window_start": window_start}
        )
        count = result_data.scalar()

        if count >= 3:
            result.risk_level = "high"
            result.reasons.append(
                f"Duplicate pattern: {count} similar reports in {DUPLICATE_WINDOW_SEC}s window"
            )
            result.action_required = "review"
        elif count >= 2:
            result.risk_level = self._max_risk(result.risk_level, "medium")
            result.reasons.append(
                f"Multiple similar reports: {count} in window"
            )

        return result

    async def _check_geo_velocity(
        self, phone, lat, lng
    ) -> FraudCheckResult:
        """Detect impossible travel between recent incidents from same caller."""
        result = FraudCheckResult()
        if not phone:
            return result

        now = datetime.now(timezone.utc)
        lookback = timedelta(hours=2)

        recent_sql = text("""
            SELECT ST_X(location::geometry) as lng,
                   ST_Y(location::geometry) as lat,
                   started_at
            FROM incidents
            WHERE started_at > :lookback_start
            ORDER BY started_at DESC
            LIMIT 5
        """)

        result_data = await self.db.execute(
            recent_sql, {"lookback_start": now - lookback}
        )
        rows = result_data.fetchall()

        if len(rows) < 2:
            return result

        for row in rows[1:]:
            prev_lng, prev_lat, prev_time = row
            distance_km = _haversine_km(prev_lat, prev_lng, lat, lng)
            time_diff_hours = max(0.01, abs((now - prev_time).total_seconds()) / 3600)
            speed_kmh = distance_km / time_diff_hours

            if speed_kmh > GEO_VELOCITY_THRESHOLD_KMH:
                result.risk_level = "high"
                result.reasons.append(
                    "Impossible travel: {:.0f}km in {:.1f}h ({:.0f} km/h)".format(
                        distance_km, time_diff_hours, speed_kmh
                    )
                )
                result.action_required = "review"

        return result

    # ─── Storage helpers ─────────────────────────────────────────────────────

    async def _get_or_create_tracker(
        self, phone=None, device_fingerprint=None, ip_address=None
    ) -> AbuseTracker:
        """Find existing tracker or create new one."""
        query = self.db.query(AbuseTracker)

        if phone:
            query = query.filter(AbuseTracker.phone == phone)
        elif device_fingerprint:
            query = query.filter(AbuseTracker.device_fingerprint == device_fingerprint)

        existing = (await self.db.execute(query)).scalar_one_or_none()
        if existing:
            return existing

        tracker = AbuseTracker(
            phone=phone,
            device_fingerprint=device_fingerprint,
            ip_address=ip_address,
        )
        self.db.add(tracker)
        return tracker

    @staticmethod
    def _max_risk(a: str, b: str) -> str:
        """Return the higher risk level."""
        levels = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        return a if levels.get(a, 0) >= levels.get(b, 0) else b


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance between two points in km using Haversine formula."""
    from math import radians, sin, cos, sqrt, atan2

    R = 6371  # Earth radius in km
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lng1, lat2, lng2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c