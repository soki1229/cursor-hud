import pytest
import json
from cursor_hud import parse_data, decode_jwt, usd, _safe_int

def test_decode_jwt_invalid():
    assert decode_jwt("invalid.token.here") == {}

def test_usd_format():
    assert usd(100) == "$1.00"
    assert usd(1250) == "$12.50"
    assert usd(0) == "$0.00"

def test_safe_int():
    assert _safe_int("100") == 100
    assert _safe_int(None) == 0
    assert _safe_int("abc", default=5) == 5

def test_parse_data_basic():
    # Mock minimal summary and profile
    raw = {
        "summary": {
            "billingCycleStart": "2026-03-01T00:00:00Z",
            "billingCycleEnd": "2026-03-31T00:00:00Z",
            "membershipType": "pro",
            "individualUsage": {
                "plan": {
                    "used": 100,
                    "limit": 500,
                    "breakdown": {"included": 100, "bonus": 0}
                },
                "onDemand": {"used": 0}
            }
        },
        "profile": {
            "name": "Test User",
            "email": "test@example.com",
            "email_verified": True
        },
        "email": "test@example.com",
        "fetched_at": "2026-03-31T12:00:00Z"
    }
    
    parsed = parse_data(raw)
    
    assert parsed["profile"]["name"] == "Test User"
    assert parsed["credit"]["incl_used"] == 100
    assert parsed["credit"]["budget_total"] == 500
    assert parsed["credit"]["budget_remain"] == 400
    assert parsed["is_free"] is False
    assert parsed["is_team"] is False

def test_parse_data_free_plan():
    raw = {
        "summary": {
            "membershipType": "free",
        },
        "profile": {},
        "email": "free@example.com"
    }
    parsed = parse_data(raw)
    assert parsed["is_free"] is True
