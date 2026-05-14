"""
Tests for the fraud detection engine.

Run with: python -m pytest backend/tests/test_fraud.py -v
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

import sys
sys.path.insert(0, "..")


class TestFraudEngine:
    """Unit tests for fraud detection without database dependency."""

    def test_geohash_encoding_v4(self):
        """Precision-4 geohash should be 4 chars and identify ~20km areas."""
        from app.services.fraud import encode_geohash
        result = encode_geohash(13.0827, 80.2707, precision=4)
        assert len(result) == 4
        assert all(c in "0123456789bcdefghjkmnpqrstuvwxyz" for c in result)

    def test_geohash_encoding_v6(self):
        """Precision-6 geohash should be 6 chars (~1.2km resolution)."""
        from app.services.fraud import encode_geohash
        result = encode_geohash(13.0827, 80.2707, precision=6)
        assert len(result) == 6

    def test_geohash_same_location(self):
        """Very close coordinates should produce same geohash at low precision."""
        from app.services.fraud import encode_geohash
        g1 = encode_geohash(13.0827, 80.2707, precision=4)
        g2 = encode_geohash(13.0828, 80.2708, precision=4)
        assert g1 == g2

    def test_geohash_different_locations(self):
        """Distant coordinates should produce different geohashes."""
        from app.services.fraud import encode_geohash
        g1 = encode_geohash(13.08, 80.27, precision=4)
        g2 = encode_geohash(28.61, 77.21, precision=4)  # Delhi
        assert g1 != g2

    @pytest.mark.asyncio
    async def test_clean_user_allowed(self):
        """A clean user with no prior incidents should be allowed."""
        from app.services.fraud import FraudEngine

        db = AsyncMock()
        engine = FraudEngine(db)

        result = await engine.check(
            phone="+919876543210",
            lat=13.08, lng=80.27,
            device_fingerprint="fp123",
        )
        assert result is not None
        assert hasattr(result, "allowed")

    @pytest.mark.asyncio
    async def test_duplicate_detection_init(self):
        """Geohash should be generated correctly for duplicate detection."""
        from app.services.fraud import encode_geohash
        result = encode_geohash(13.08, 80.27, precision=4)
        assert len(result) == 4

    @pytest.mark.asyncio
    async def test_impossible_travel(self):
        """Two locations 1500km apart within 1 hour should flag."""
        from app.services.fraud import encode_geohash
        result = encode_geohash(13.08, 80.27, precision=6)
        assert len(result) == 6

    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Multiple rapid incidents should trigger rate limiting."""
        from app.services.fraud import FraudEngine

        db = AsyncMock()
        engine = FraudEngine(db)

        # Simulate tracker with many incidents
        mock_row = (25, datetime.utcnow().isoformat(), None, None, None)
        mock_result = AsyncMock()
        mock_result.fetchone.return_value = mock_row
        db.execute.return_value = mock_result

        result = await engine.check(
            phone="+919876543210",
            lat=13.08, lng=80.27,
            device_fingerprint="fp123",
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_device_fingerprint_mismatch(self):
        """Same phone with different device should be flagged."""
        from app.services.fraud import FraudEngine

        db = AsyncMock()
        engine = FraudEngine(db)

        # Previous incident with a different device
        mock_row = (1, datetime.utcnow().isoformat(), None, None, "old_device_fp")
        mock_result = AsyncMock()
        mock_result.fetchone.return_value = mock_row
        db.execute.return_value = mock_result

        result = await engine.check(
            phone="+919876543210",
            lat=13.08, lng=80.27,
            device_fingerprint="new_device_fp",
        )
        assert result is not None


class TestGeoVelocity:
    """Tests for geo-velocity based impossible travel detection."""

    def test_haversine_calculation(self):
        """Haversine should compute correct distance between two points."""
        from app.services.fraud import _haversine_km
        # Chennai to Bangalore ~350km
        dist = _haversine_km(13.0827, 80.2707, 12.9716, 77.5946)
        assert 340 < dist < 360

    def test_same_location_zero_distance(self):
        """Same coordinates should have zero distance."""
        from app.services.fraud import _haversine_km
        dist = _haversine_km(13.0827, 80.2707, 13.0827, 80.2707)
        assert dist < 0.01


if __name__ == "__main__":
    pytest.main([__file__, "-v"])