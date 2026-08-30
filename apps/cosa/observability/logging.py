from __future__ import annotations

import contextvars
import datetime
import json
import logging
import re
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from apps.cosa.observability.otel import get_current_span_id, get_current_trace_id

__all__ = [
    "JSONLogFormatter",
    "RedactingFilter",
    "clear_log_context",
    "log_context",
    "redact_sensitive_text",
    "set_log_context",
    "setup_logging",
]

# Context variables for correlation
_RUN_ID_VAR: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "cosa_log_run_id", default=None
)
_WORKSPACE_ID_VAR: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "cosa_log_workspace_id", default=None
)

# Patterns for secret redaction
SENSITIVE_PATTERNS = [
    # API keys (OpenAI / DeepSeek / General sk- keys)
    re.compile(
        r"(?i)(?:api[_-]?key|secret|token|password|authorization)[\s:=]+['\"]?([a-zA-Z0-9_\-\.]{8,})['\"]?"
    ),
    re.compile(r"sk-[a-zA-Z0-9_\-]{20,}"),
    # Bearer tokens
    re.compile(r"(?i)bearer\s+([a-zA-Z0-9_\-\.]{16,})"),
    # Postgres DSNs: postgres://user:pass@host:port/db or postgresql+asyncpg://...
    re.compile(r"(postgres(?:ql)?(?:\+[a-zA-Z0-9]+)?://[^:]+:)([^@]+)(@[^\s\"']+)"),
]


def redact_sensitive_text(text: str) -> str:
    """Loại bỏ các thông tin nhạy cảm (API keys, DSN credentials, Bearer tokens) khỏi chuỗi text."""
    if not text:
        return text

    # Redact connection strings preserving protocol and host
    text = re.sub(
        r"(postgres(?:ql)?(?:\+[a-zA-Z0-9]+)?://[^:]+:)([^@]+)(@[^\s\"']+)",
        r"\1[REDACTED]\3",
        text,
    )

    # Redact sk- keys
    text = re.sub(r"sk-[a-zA-Z0-9_\-]{20,}", "[REDACTED_API_KEY]", text)

    # Redact Bearer tokens
    text = re.sub(r"(?i)bearer\s+[a-zA-Z0-9_\-\.]{16,}", "Bearer [REDACTED]", text)

    # Redact common key=value patterns
    def _replace_kv(m: re.Match) -> str:
        full = m.group(0)
        secret = m.group(1)
        return full.replace(secret, "[REDACTED]")

    text = re.sub(
        r"(?i)(?:api[_-]?key|client_secret|password)[\s:=]+['\"]?([a-zA-Z0-9_\-\.]{8,})['\"]?",
        _replace_kv,
        text,
    )

    # Redact email and phone PII
    text = re.sub(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", "[EMAIL_REDACTED]", text)
    text = re.sub(
        r"(?:\+84|0)(?:3[2-9]|5[689]|7[06-9]|8[1-9]|9[0-9])[0-9]{7}", "[PHONE_REDACTED]", text
    )

    return text


def set_log_context(run_id: str | None = None, workspace_id: str | None = None) -> None:
    """Gán correlation context (run_id, workspace_id) cho scope hiện tại."""
    if run_id is not None:
        _RUN_ID_VAR.set(run_id)
    if workspace_id is not None:
        _WORKSPACE_ID_VAR.set(workspace_id)


def clear_log_context() -> None:
    """Xóa correlation context của scope hiện tại."""
    _RUN_ID_VAR.set(None)
    _WORKSPACE_ID_VAR.set(None)


@contextmanager
def log_context(
    run_id: str | None = None,
    workspace_id: str | None = None,
) -> Iterator[None]:
    """Context manager gán correlation context và tự động phục hồi sau khi thoát."""
    token_run = _RUN_ID_VAR.set(run_id) if run_id is not None else None
    token_ws = _WORKSPACE_ID_VAR.set(workspace_id) if workspace_id is not None else None
    try:
        yield
    finally:
        if token_run is not None:
            _RUN_ID_VAR.reset(token_run)
        if token_ws is not None:
            _WORKSPACE_ID_VAR.reset(token_ws)


class RedactingFilter(logging.Filter):
    """Logging filter áp dụng redaction cho message và args."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact_sensitive_text(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: redact_sensitive_text(str(v)) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, (list, tuple)):
                record.args = tuple(
                    redact_sensitive_text(str(a)) if isinstance(a, str) else a for a in record.args
                )
        return True


STANDARD_LOGRECORD_ATTRS = frozenset(
    {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
        "taskName",
    }
)

ALLOWED_LOG_METADATA_KEYS = frozenset(
    {
        "run_id",
        "workspace_id",
        "trace_id",
        "span_id",
        "event_type",
        "capability_id",
        "tool_call_id",
        "checkpoint_ref",
        "decision",
        "reason_code",
        "snapshot_hash",
        "policy_snapshot_hash",
        "provider_model_ref",
        "delegation_jti",
        "duration_ms",
        "status",
    }
)


class JSONLogFormatter(logging.Formatter):
    """Formatter chuyển đổi LogRecord thành JSON có cấu trúc thống nhất:
    ts, level, msg, service, run_id, workspace_id, trace_id, span_id, logger.
    Áp dụng allowlist serialization: loại bỏ hoàn toàn các metadata keys không được phép.
    """

    def __init__(self, service_name: str = "cosa-service") -> None:
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        # Base message format with standard args interpolation
        try:
            msg_text = record.getMessage()
        except Exception:
            msg_text = str(record.msg)

        msg_text = redact_sensitive_text(msg_text)

        log_data: dict[str, Any] = {
            "ts": datetime.datetime.now(datetime.UTC).isoformat(),
            "level": record.levelname,
            "msg": msg_text,
            "service": self.service_name,
            "logger": record.name,
        }

        # Inject context variables
        run_id = _RUN_ID_VAR.get()
        if run_id:
            log_data["run_id"] = run_id

        workspace_id = _WORKSPACE_ID_VAR.get()
        if workspace_id:
            log_data["workspace_id"] = workspace_id

        # Inject OTel trace correlation
        trace_id = get_current_trace_id()
        if trace_id:
            log_data["trace_id"] = trace_id

        span_id = get_current_span_id()
        if span_id:
            log_data["span_id"] = span_id

        # Allowlist serialization for extra attributes on record
        for key, value in record.__dict__.items():
            if key in STANDARD_LOGRECORD_ATTRS or key in log_data:
                continue
            if key in ALLOWED_LOG_METADATA_KEYS:
                log_data[key] = (
                    redact_sensitive_text(str(value)) if isinstance(value, str) else value
                )

        if record.exc_info:
            log_data["exception"] = redact_sensitive_text(self.formatException(record.exc_info))

        return json.dumps(log_data, default=str)


def setup_logging(
    service_name: str = "cosa-service",
    log_level: str = "INFO",
    json_format: bool = True,
) -> None:
    """Cấu hình logging tập trung: gắn RedactingFilter và JSONLogFormatter cho root logger."""
    level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(level)
    stream_handler.addFilter(RedactingFilter())

    if json_format:
        stream_handler.setFormatter(JSONLogFormatter(service_name=service_name))
    else:
        stream_handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%SZ",
            )
        )

    root_logger.addHandler(stream_handler)
