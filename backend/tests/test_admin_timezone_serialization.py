"""UTC timestamps must be explicitly zoned to prevent a 7-hour Admin UI shift."""
from datetime import datetime, timezone, timedelta

from bson import ObjectId

from app.modules.admin.audit import _serialize as serialize_audit
from app.modules.admin.registrations import _serialize as serialize_registration


def test_registration_timestamps_are_utc_aware_even_from_pymongo_naive():
    raw = datetime(2026, 10, 29, 12, 59, 0)
    output = serialize_registration({"_id": ObjectId(), "status": "approved", "created_at": raw, "reviewed_at": raw})
    assert output["created_at"] == '2026-10-29T12:59:00+00:00'
    assert output["reviewed_at"] == '2026-10-29T12:59:00+00:00'
    assert datetime.fromisoformat(output["created_at"]).astimezone(timezone(timedelta(hours=7))).hour == 19


def test_audit_timestamps_are_utc_aware_and_convert_offsets():
    raw = datetime(2026, 10, 29, 19, 59, 0, tzinfo=timezone(timedelta(hours=7)))
    output = serialize_audit({"_id": ObjectId(), "created_at": raw})
    assert output["created_at"] == '2026-10-29T12:59:00+00:00'
    assert serialize_audit({"_id": ObjectId(), "created_at": raw.replace(tzinfo=None)})["created_at"] == '2026-10-29T19:59:00+00:00'
