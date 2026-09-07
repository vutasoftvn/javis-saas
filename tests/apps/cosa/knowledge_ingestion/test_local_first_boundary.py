"""Task 1 — khóa ranh giới local-first cho document ingestion orchestration.

ADR-LOCAL-FIRST-001: `services/cosa` orchestrates document ingestion trên
Workspace Runtime Node (execution plane) — không bao giờ được âm thầm fallback
sang Platform Control Plane URL (`COSA_PLATFORM_CONTROL_PLANE_URL`, dùng cho
identity/license/connector policy).
"""

from __future__ import annotations

from apps.cosa.knowledge_ingestion.control_plane_client import LocalDocumentIngestionClient


def test_local_ingestion_client_uses_execution_plane(monkeypatch):
    monkeypatch.setenv("COSA_EXECUTION_PLANE_URL", "http://workspace.local:4001")
    monkeypatch.setenv("COSA_PLATFORM_CONTROL_PLANE_URL", "https://platform.example")
    client = LocalDocumentIngestionClient()
    assert client.base_url == "http://workspace.local:4001"


def test_platform_url_is_never_used_for_document_ingestion(monkeypatch):
    monkeypatch.delenv("COSA_EXECUTION_PLANE_URL", raising=False)
    monkeypatch.setenv("COSA_PLATFORM_CONTROL_PLANE_URL", "https://platform.example")
    assert "platform.example" not in LocalDocumentIngestionClient().base_url


def test_explicit_execution_plane_url_overrides_env(monkeypatch):
    monkeypatch.setenv("COSA_EXECUTION_PLANE_URL", "http://env-value:4001")
    client = LocalDocumentIngestionClient(execution_plane_url="http://explicit-value:4001")
    assert client.base_url == "http://explicit-value:4001"
