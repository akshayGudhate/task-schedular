from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import structlog

from app.db.database import get_connection
from app.models.task import RecurrenceType

log = structlog.get_logger()

# staggered so all 4 fire within the first 2 minutes — easy to demo end-to-end
_TASKS = [
    {
        "name":        "Send Welcome Email",
        "webhook_url": "http://executor:8090/send-welcome",
        "payload":     {"email": "newuser@example.com", "template": "welcome"},
        "recurrence":  RecurrenceType.NONE.value,
        "delay_s":     30,
    },
    {
        "name":        "Notify Admin on New Signup",
        "webhook_url": "http://executor:8090/notify-admin",
        "payload":     {"user": "newuser@example.com"},
        "recurrence":  RecurrenceType.NONE.value,
        "delay_s":     60,
    },
    {
        "name":        "Daily Summary Report",
        "webhook_url": "http://executor:8090/daily-report",
        "payload":     {},
        "recurrence":  RecurrenceType.DAILY.value,
        "delay_s":     90,
    },
    {
        "name":        "Security Alert Notification",
        "webhook_url": "http://executor:8090/security-alert",
        "payload":     {"severity": "high"},
        "recurrence":  RecurrenceType.NONE.value,
        "delay_s":     120,
    },
]


async def seed() -> None:
    async with get_connection() as conn:
        count = await conn.fetchval("SELECT COUNT(*) FROM tasks")
        if count > 0:
            return  # idempotent — skip if data already exists from a previous run

        now = datetime.now(timezone.utc)
        for task in _TASKS:
            await conn.execute(
                """
                INSERT INTO tasks (name, execution_time, webhook_url, payload, recurrence, max_retries)
                VALUES ($1, $2, $3, $4::jsonb, $5::recurrence_type, 3)
                """,
                task["name"],
                now + timedelta(seconds=task["delay_s"]),
                task["webhook_url"],
                json.dumps(task["payload"]),
                task["recurrence"],
            )

        log.info("db.seeded", count=len(_TASKS))
