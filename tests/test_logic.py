import os
import sys
from pathlib import Path

# Force offscreen platform for Qt BEFORE any PyQt imports
os.environ["QT_QPA_PLATFORM"] = "offscreen"

# Ensure the project root is in sys.path so we can import cursor_hud
root_dir = str(Path(__file__).parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from cursor_hud import _safe_int, decode_jwt, parse_data, usd  # noqa: E402


def test_decode_jwt_invalid():
    """Verify that invalid tokens return an empty dict instead of crashing."""
    assert decode_jwt("invalid.token.here") == {}
    assert decode_jwt("") == {}


def test_usd_format():
    """Verify currency formatting logic."""
    assert usd(100) == "$1.00"
    assert usd(1250) == "$12.50"
    assert usd(0) == "$0.00"


def test_safe_int():
    """Verify robust integer conversion."""
    assert _safe_int("100") == 100
    assert _safe_int(None) == 0
    assert _safe_int("abc", default=5) == 5


def test_parse_data_minimal():
    """Verify the core data model parsing with minimal valid input."""
    raw = {
        "summary": {
            "billingCycleStart": "2026-03-01T00:00:00Z",
            "billingCycleEnd": "2026-03-31T00:00:00Z",
            "membershipType": "pro",
            "individualUsage": {
                "plan": {
                    "used": 100,
                    "limit": 500,
                    "breakdown": {"included": 100, "bonus": 0},
                },
                "onDemand": {"used": 0},
            },
        },
        "profile": {"name": "Test", "email": "test@example.com"},
        "email": "test@example.com",
    }
    parsed = parse_data(raw)
    assert parsed["credit"]["budget_total"] == 500
    assert parsed["credit"]["budget_remain"] == 400
    assert parsed["is_free"] is False
