# backend/app/workforce/agents/orchestration/adk/session_service_factory.py
"""Factory cho google.adk.sessions.database_session_service.DatabaseSessionService,
trỏ vào schema `adk_runtime` riêng — cô lập khỏi schema `public` (business data)
vì tên bảng ADK khá generic (sessions, events, app_states, user_states)."""
from datetime import date, datetime
import json
import os
from typing import Any

from google.adk.sessions.database_session_service import DatabaseSessionService

_DEFAULT_SCHEMA = "adk_runtime"


def _json_dumps(obj: Any) -> str:
    def _default(o: Any) -> Any:
        if isinstance(o, (datetime, date)):
            return o.isoformat()
        return str(o)

    return json.dumps(obj, default=_default)


def resolve_adk_runtime_database_url() -> str:
    explicit = os.environ.get("ADK_RUNTIME_DATABASE_URL")
    if explicit:
        return explicit

    base = os.environ.get("DATABASE_URL", "postgresql://javis:javis@localhost:5432/javis")
    if base.startswith("postgres://"):
        base = base.replace("postgres://", "postgresql://", 1)
    if base.startswith("postgresql://"):
        base = base.replace("postgresql://", "postgresql+asyncpg://", 1)
    return base


def build_adk_session_service() -> DatabaseSessionService:
    db_url = resolve_adk_runtime_database_url()
    connect_args = {"server_settings": {"search_path": _DEFAULT_SCHEMA}}
    return DatabaseSessionService(
        db_url=db_url,
        connect_args=connect_args,
        json_serializer=_json_dumps,
    )
