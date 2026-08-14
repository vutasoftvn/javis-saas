from datetime import datetime, timedelta

from sqlalchemy import text

from app.core.snowflake import generate_snowflake_id


WORKER_COMPONENT = "agent-worker"
HEARTBEAT_INTERVAL_SECONDS = 5
HEARTBEAT_MAX_AGE_SECONDS = 15


def get_worker_health(engine) -> tuple[bool, str]:
    try:
        with engine.connect() as conn:
            last_seen_at = conn.execute(
                text(
                    "SELECT last_seen_at FROM runtime_heartbeats "
                    "WHERE component = :component"
                ),
                {"component": WORKER_COMPONENT},
            ).scalar()
    except Exception:
        return False, "error"

    if last_seen_at is None:
        return False, "missing"
    if datetime.utcnow() - last_seen_at > timedelta(seconds=HEARTBEAT_MAX_AGE_SECONDS):
        return False, "stale"
    return True, "ok"


def record_worker_heartbeat(db) -> None:
    now = datetime.utcnow()
    db.execute(
        text(
            "INSERT INTO runtime_heartbeats "
            "(id, component, last_seen_at, created_at, updated_at) "
            "VALUES (:id, :component, :last_seen_at, :created_at, :updated_at) "
            "ON CONFLICT (component) DO UPDATE SET "
            "last_seen_at = EXCLUDED.last_seen_at, "
            "updated_at = EXCLUDED.updated_at"
        ),
        {
            "id": generate_snowflake_id(),
            "component": WORKER_COMPONENT,
            "last_seen_at": now,
            "created_at": now,
            "updated_at": now,
        },
    )
    db.commit()
