from __future__ import annotations


class GovernanceStoreConfigurationError(Exception):
    """Raised when a GovernanceStateStore implementation is improperly
    configured (vd thiếu db_session_factory) — cùng mẫu với
    agentos/memory/exceptions.py::ConfigurationError."""
