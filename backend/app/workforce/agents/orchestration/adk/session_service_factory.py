# backend/app/workforce/agents/orchestration/adk/session_service_factory.py
"""Factory cho google.adk.sessions.database_session_service.DatabaseSessionService,
trỏ vào schema `adk_runtime` riêng — cô lập khỏi schema `public` (business data)
vì tên bảng ADK khá generic (sessions, events, app_states, user_states)."""
import os

from google.adk.sessions.database_session_service import DatabaseSessionService

_DEFAULT_SCHEMA = "adk_runtime"


def resolve_adk_runtime_database_url() -> str:
    explicit = os.environ.get("ADK_RUNTIME_DATABASE_URL")
    if explicit:
        return explicit

    base = os.environ.get("DATABASE_URL", "postgresql://javis:javis@localhost:5432/javis")
    if base.startswith("postgres://"):
        base = base.replace("postgres://", "postgresql://", 1)
    if base.startswith("postgresql://"):
        base = base.replace("postgresql://", "postgresql+asyncpg://", 1)
    separator = "&" if "?" in base else "?"
    return f"{base}{separator}options=-csearch_path%3D{_DEFAULT_SCHEMA}"


def build_adk_session_service() -> DatabaseSessionService:
    return DatabaseSessionService(db_url=resolve_adk_runtime_database_url())
