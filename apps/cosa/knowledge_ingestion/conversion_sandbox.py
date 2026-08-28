"""Document conversion sandbox abstraction and implementations.

Trừu tượng hóa interface chuyển đổi tài liệu:
- Protocol định nghĩa async contract
- In-process test implementation (gọi converter trực tiếp, không isolation)
- Production readiness guard (fail-closed nếu không đủ điều kiện)
"""

from __future__ import annotations

import os
from typing import Optional, Protocol, runtime_checkable

from apps.cosa.knowledge_ingestion.contracts import (
    CONVERTER_PACKAGE_SPEC,
    FailureCode,
    QUARANTINE_PREFIX,
    knowledge_ingestion_enabled,
)
from apps.cosa.knowledge_ingestion.markitdown_converter import (
    ConversionResult,
    SafeMarkItDownConverter,
)
from apps.cosa.knowledge_ingestion.preflight import ValidatedDocument
from apps.cosa.knowledge_ingestion.scanner import (
    DocumentMalwareScanner,
    assert_production_scanner_ready,
)

__all__ = [
    "DocumentConversionSandbox",
    "InProcessConversionSandbox",
    "assert_production_conversion_ready",
    "assert_production_ingestion_ready",
]


def _attested(env_name: str) -> bool:
    return os.environ.get(env_name, "").strip().lower() in ("true", "1", "yes")


def assert_production_ingestion_ready(environment: str = "development") -> None:
    """Cổng khởi động (image entrypoint / worker start) cho toàn pipeline ingestion.

    Chỉ kiểm tra các điều kiện dựa trên ENVIRONMENT + biến môi trường deploy —
    KHÔNG nhận instance scanner/sandbox (việc đó do `assert_production_conversion_ready`
    làm tại thời điểm xử lý job). Fail-closed: bất kỳ điều kiện nào thiếu → raise.

    Kiểm tra:
      1. Feature flag bật tường minh.
      2. Storage prefix policy: prefix quarantine hợp lệ, không path traversal.
      3. Scanner backend deploy KHÔNG phải fake/none.
      4. Sandbox backend deploy KHÔNG phải inprocess/none.
      5. Attestation egress-deny + resource-limits có mặt.
      6. Converter spec deploy khớp bản pin (chặn markitdown[all] / plugins).
    """
    if environment != "production":
        return

    if not knowledge_ingestion_enabled():
        raise RuntimeError(
            "assert_production_ingestion_ready: KNOWLEDGE_INGESTION_ENABLED chưa bật — "
            "pipeline phải được bật tường minh trước khi image sẵn sàng"
        )

    prefix = os.environ.get("KNOWLEDGE_INGESTION_QUARANTINE_PREFIX", QUARANTINE_PREFIX)
    if not prefix.endswith("/") or ".." in prefix or prefix.startswith("/"):
        raise RuntimeError(
            f"assert_production_ingestion_ready: storage prefix policy không hợp lệ: {prefix!r}"
        )

    scanner_backend = os.environ.get("KNOWLEDGE_INGESTION_SCANNER_BACKEND", "").strip().lower()
    if scanner_backend in ("", "fake", "none", "test"):
        raise RuntimeError(
            "assert_production_ingestion_ready: KNOWLEDGE_INGESTION_SCANNER_BACKEND phải trỏ "
            "scanner thật (không fake/none)"
        )

    sandbox_backend = os.environ.get("KNOWLEDGE_INGESTION_SANDBOX_BACKEND", "").strip().lower()
    if sandbox_backend in ("", "inprocess", "in_process", "none", "test"):
        raise RuntimeError(
            "assert_production_ingestion_ready: KNOWLEDGE_INGESTION_SANDBOX_BACKEND phải trỏ "
            "sandbox cô lập thật (không inprocess/none)"
        )

    if not _attested("KNOWLEDGE_INGESTION_EGRESS_DENY_ATTESTED"):
        raise RuntimeError(
            "assert_production_ingestion_ready: thiếu KNOWLEDGE_INGESTION_EGRESS_DENY_ATTESTED"
        )
    if not _attested("KNOWLEDGE_INGESTION_RESOURCE_LIMITS_ATTESTED"):
        raise RuntimeError(
            "assert_production_ingestion_ready: thiếu KNOWLEDGE_INGESTION_RESOURCE_LIMITS_ATTESTED"
        )

    deployed_spec = os.environ.get("KNOWLEDGE_INGESTION_CONVERTER_SPEC", "").strip()
    if deployed_spec != CONVERTER_PACKAGE_SPEC:
        raise RuntimeError(
            "assert_production_ingestion_ready: KNOWLEDGE_INGESTION_CONVERTER_SPEC "
            f"({deployed_spec!r}) không khớp bản pin {CONVERTER_PACKAGE_SPEC!r}"
        )


@runtime_checkable
class DocumentConversionSandbox(Protocol):
    """Process boundary for sandboxed document conversion.

    async def run(
        document: ValidatedDocument,
        content: bytes,
        converter_profile: str
    ) -> ConversionResult
    """

    async def run(
        self,
        document: ValidatedDocument,
        content: bytes,
        converter_profile: str,
    ) -> ConversionResult:
        """Execute conversion in isolation.

        Args:
            document: Validated document metadata
            content: Raw document bytes
            converter_profile: Converter profile identifier (e.g. "markitdown-safe-v1")

        Returns:
            ConversionResult with markdown or failure_code
        """
        ...


class InProcessConversionSandbox:
    """Test-only, in-process conversion sandbox.

    Calls SafeMarkItDownConverter directly without OS-level isolation.
    This is fine for unit tests but MUST NOT be used in production.
    Real isolation is provided by the separate Docker image (Dockerfile.ingestion-worker).

    Việc cô lập thực tế do Docker image riêng (Dockerfile.ingestion-worker)
    cấp — không phải Python code.
    """

    def __init__(self):
        """Initialize test converter."""
        self._converter = SafeMarkItDownConverter()

    async def run(
        self,
        document: ValidatedDocument,
        content: bytes,
        converter_profile: str,
    ) -> ConversionResult:
        """Execute conversion in-process (test-only).

        Kiểm tra converter_profile khớp với converter hiện tại.
        """
        if converter_profile != "markitdown-safe-v1":
            return ConversionResult(
                markdown=None,
                title=None,
                package="markitdown",
                version="0.1.7",
                converter_profile=converter_profile,
                output_sha256=None,
                warnings=[],
                failure_code="conversion_parser_error",
            )

        # Call converter directly (no real isolation)
        return self._converter.convert(document, content)


def assert_production_conversion_ready(
    sandbox: DocumentConversionSandbox | None,
    scanner: Optional[DocumentMalwareScanner],
    environment: str = "development",
) -> None:
    """Validate production-readiness of conversion sandbox.

    Composes scanner readiness check (Task 3) with sandbox checks:
    - Non-production: passes immediately
    - Production: all of:
      a. Sandbox is NOT InProcessConversionSandbox (test-only)
      b. Scanner is production-ready (via composed assert_production_scanner_ready)
      c. Resource limits attestation present (env var)
      d. Egress-deny attestation present (env var)

    Tăng nếu không đủ điều kiện.
    Kiểm tra thất bại ngay nếu environment="production" và bất kỳ điều kiện nào không đúng.

    Args:
        sandbox: The conversion sandbox instance to check (can be None)
        scanner: The malware scanner instance to check (can be None; None in production will raise)
        environment: Current environment ("development", "production", etc.)

    Raises:
        RuntimeError if production checks fail
    """
    if environment != "production":
        # Non-production: minimal checks
        return

    # Production environment: strict checks
    if sandbox is None:
        raise RuntimeError(
            "assert_production_conversion_ready: sandbox is None in production"
        )

    # Check 1: Sandbox must NOT be test-only in-process implementation
    if isinstance(sandbox, InProcessConversionSandbox):
        raise RuntimeError(
            "assert_production_conversion_ready: "
            "InProcessConversionSandbox is test-only and not allowed in production"
        )

    # Check 2: Compose scanner readiness check from Task 3
    # This call will raise if scanner is None or fake in production
    assert_production_scanner_ready(scanner, environment)

    # Check 3: Resource limits attestation must be present
    resource_limits_attested = os.environ.get(
        "KNOWLEDGE_INGESTION_RESOURCE_LIMITS_ATTESTED", ""
    ).lower() in ("true", "1", "yes")
    if not resource_limits_attested:
        raise RuntimeError(
            "assert_production_conversion_ready: "
            "KNOWLEDGE_INGESTION_RESOURCE_LIMITS_ATTESTED not set; "
            "orchestrator must enforce CPU/memory/PID/time limits"
        )

    # Check 4: Egress-deny attestation must be present
    egress_deny_attested = os.environ.get(
        "KNOWLEDGE_INGESTION_EGRESS_DENY_ATTESTED", ""
    ).lower() in ("true", "1", "yes")
    if not egress_deny_attested:
        raise RuntimeError(
            "assert_production_conversion_ready: "
            "KNOWLEDGE_INGESTION_EGRESS_DENY_ATTESTED not set; "
            "orchestrator must enforce network egress-deny policy"
        )
