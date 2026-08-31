"""Guard: CI phải chạy full AgentOS application unit suite (apps/cosa), không
chỉ subset agent. Nếu ai đó xoá hoặc đổi tên job này khỏi quality.yml, test
này fail để ngăn suite bị âm thầm bỏ ra khỏi gate bắt buộc."""
from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
WORKFLOW = REPO / ".github/workflows/quality.yml"


def test_quality_workflow_runs_full_apps_cosa_unit_suite() -> None:
    workflow = WORKFLOW.read_text()
    assert "make apps-cosa-test" in workflow
