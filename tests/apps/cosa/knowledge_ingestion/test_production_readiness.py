"""Release-readiness gate: assert_production_ingestion_ready.

Cổng khởi động image/worker — fail-closed. Chỉ dựa trên ENVIRONMENT + biến môi
trường deploy (không nhận instance). Non-production luôn pass; production đòi đủ
mọi điều kiện.
"""

from __future__ import annotations

import pytest

from apps.cosa.knowledge_ingestion.contracts import CONVERTER_PACKAGE_SPEC
from apps.cosa.knowledge_ingestion.conversion_sandbox import (
    assert_production_ingestion_ready,
)


_PROD_ENV = {
    "KNOWLEDGE_INGESTION_ENABLED": "true",
    "KNOWLEDGE_INGESTION_QUARANTINE_PREFIX": "quarantine/",
    "KNOWLEDGE_INGESTION_SCANNER_BACKEND": "clamav",
    "KNOWLEDGE_INGESTION_SANDBOX_BACKEND": "gvisor-pod",
    "KNOWLEDGE_INGESTION_EGRESS_DENY_ATTESTED": "true",
    "KNOWLEDGE_INGESTION_RESOURCE_LIMITS_ATTESTED": "true",
    "KNOWLEDGE_INGESTION_CONVERTER_SPEC": CONVERTER_PACKAGE_SPEC,
}


def _apply(monkeypatch, env: dict) -> None:
    for k in (
        "KNOWLEDGE_INGESTION_ENABLED",
        "KNOWLEDGE_INGESTION_QUARANTINE_PREFIX",
        "KNOWLEDGE_INGESTION_SCANNER_BACKEND",
        "KNOWLEDGE_INGESTION_SANDBOX_BACKEND",
        "KNOWLEDGE_INGESTION_EGRESS_DENY_ATTESTED",
        "KNOWLEDGE_INGESTION_RESOURCE_LIMITS_ATTESTED",
        "KNOWLEDGE_INGESTION_CONVERTER_SPEC",
    ):
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)


def test_non_production_passes_even_with_nothing_configured(monkeypatch):
    _apply(monkeypatch, {})
    assert_production_ingestion_ready("development")
    assert_production_ingestion_ready("staging")
    assert_production_ingestion_ready("test")


def test_production_with_full_valid_env_passes(monkeypatch):
    _apply(monkeypatch, _PROD_ENV)
    assert_production_ingestion_ready("production")


def test_production_rejects_when_feature_flag_off(monkeypatch):
    _apply(monkeypatch, {**_PROD_ENV, "KNOWLEDGE_INGESTION_ENABLED": "false"})
    with pytest.raises(RuntimeError, match="KNOWLEDGE_INGESTION_ENABLED"):
        assert_production_ingestion_ready("production")


def test_production_rejects_fake_scanner_backend(monkeypatch):
    _apply(monkeypatch, {**_PROD_ENV, "KNOWLEDGE_INGESTION_SCANNER_BACKEND": "fake"})
    with pytest.raises(RuntimeError, match="SCANNER_BACKEND"):
        assert_production_ingestion_ready("production")


def test_production_rejects_inprocess_sandbox_backend(monkeypatch):
    _apply(monkeypatch, {**_PROD_ENV, "KNOWLEDGE_INGESTION_SANDBOX_BACKEND": "inprocess"})
    with pytest.raises(RuntimeError, match="SANDBOX_BACKEND"):
        assert_production_ingestion_ready("production")


def test_production_rejects_missing_egress_attestation(monkeypatch):
    env = {**_PROD_ENV}
    env.pop("KNOWLEDGE_INGESTION_EGRESS_DENY_ATTESTED")
    _apply(monkeypatch, env)
    with pytest.raises(RuntimeError, match="EGRESS_DENY_ATTESTED"):
        assert_production_ingestion_ready("production")


def test_production_rejects_missing_resource_limits_attestation(monkeypatch):
    env = {**_PROD_ENV}
    env.pop("KNOWLEDGE_INGESTION_RESOURCE_LIMITS_ATTESTED")
    _apply(monkeypatch, env)
    with pytest.raises(RuntimeError, match="RESOURCE_LIMITS_ATTESTED"):
        assert_production_ingestion_ready("production")


def test_production_rejects_converter_spec_drift(monkeypatch):
    _apply(
        monkeypatch,
        {**_PROD_ENV, "KNOWLEDGE_INGESTION_CONVERTER_SPEC": "markitdown[all]==0.1.7"},
    )
    with pytest.raises(RuntimeError, match="CONVERTER_SPEC"):
        assert_production_ingestion_ready("production")


def test_production_rejects_path_traversal_storage_prefix(monkeypatch):
    _apply(
        monkeypatch,
        {**_PROD_ENV, "KNOWLEDGE_INGESTION_QUARANTINE_PREFIX": "quarantine/../"},
    )
    with pytest.raises(RuntimeError, match="storage prefix"):
        assert_production_ingestion_ready("production")


def test_production_rejects_absolute_storage_prefix(monkeypatch):
    _apply(
        monkeypatch,
        {**_PROD_ENV, "KNOWLEDGE_INGESTION_QUARANTINE_PREFIX": "/quarantine/"},
    )
    with pytest.raises(RuntimeError, match="storage prefix"):
        assert_production_ingestion_ready("production")
