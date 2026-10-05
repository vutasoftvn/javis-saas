"""Kho báo cáo kiểm tra tiêu chí hoàn thành (Verifier, Dự án B).

`create_if_absent` idempotent theo `(workspace_id, run_id)`: trả bản đã có nếu trùng
(kể cả khi hai lời gọi chạy song song).
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Protocol

from pydantic import BaseModel, Field
from sqlalchemy import text


class VerificationReport(BaseModel):
    report_id: str
    workspace_id: str
    project_id: str | None = None
    task_id: str
    run_id: str
    verifier_run_id: str | None = None
    verdict: str
    mode: str
    criteria_results: list[dict[str, Any]] = Field(default_factory=list)
    criteria_hash: str
    output_hash: str
    created_at: datetime


class VerificationReportRepository(Protocol):
    async def create_if_absent(self, report: VerificationReport) -> VerificationReport: ...

    async def get_for_run(self, workspace_id: str, run_id: str) -> VerificationReport | None: ...

    async def list_for_task(
        self, workspace_id: str, task_id: str, limit: int = 20
    ) -> list[VerificationReport]: ...


class InMemoryVerificationReportRepository:
    def __init__(self) -> None:
        self._by_run: dict[tuple[str, str], VerificationReport] = {}

    async def create_if_absent(self, report: VerificationReport) -> VerificationReport:
        key = (report.workspace_id, report.run_id)
        existing = self._by_run.get(key)
        if existing is not None:
            return existing
        self._by_run[key] = report
        return report

    async def get_for_run(self, workspace_id: str, run_id: str) -> VerificationReport | None:
        return self._by_run.get((workspace_id, run_id))

    async def list_for_task(
        self, workspace_id: str, task_id: str, limit: int = 20
    ) -> list[VerificationReport]:
        rows = [
            r
            for r in self._by_run.values()
            if r.workspace_id == workspace_id and r.task_id == task_id
        ]
        rows.sort(key=lambda r: r.created_at, reverse=True)
        return rows[:limit]


_COLUMNS = """report_id, workspace_id, project_id, task_id, run_id, verifier_run_id, verdict,
               mode, criteria_results, criteria_hash, output_hash, created_at"""

_INSERT = text(
    """
    INSERT INTO agent.verification_reports
      (report_id, workspace_id, project_id, task_id, run_id, verifier_run_id, verdict, mode,
       criteria_results, criteria_hash, output_hash, created_at)
    VALUES (:report_id, :workspace_id, :project_id, :task_id, :run_id, :verifier_run_id, :verdict, :mode,
            CAST(:criteria_results AS jsonb), :criteria_hash, :output_hash, :created_at)
    ON CONFLICT (workspace_id, run_id) DO NOTHING
    """
)

_SELECT_FOR_RUN = text(
    f"""
    SELECT {_COLUMNS}
    FROM agent.verification_reports
    WHERE workspace_id = :workspace_id AND run_id = :run_id
    """
)

_SELECT_FOR_TASK = text(
    f"""
    SELECT {_COLUMNS}
    FROM agent.verification_reports
    WHERE workspace_id = :workspace_id AND task_id = :task_id
    ORDER BY created_at DESC
    LIMIT :limit
    """
)


def _row_to_report(row: Any) -> VerificationReport:
    """Truy vấn `text()` thô có thể trả jsonb dạng chuỗi — parse phòng thủ."""
    data = dict(row)
    if isinstance(data.get("criteria_results"), str):
        data["criteria_results"] = json.loads(data["criteria_results"])
    return VerificationReport(**data)


class PostgresVerificationReportRepository:
    def __init__(self, session_factory: Any) -> None:
        if session_factory is None:
            raise ValueError("PostgresVerificationReportRepository requires a session_factory")
        self._session_factory = session_factory

    async def create_if_absent(self, report: VerificationReport) -> VerificationReport:
        params = report.model_dump()
        params["criteria_results"] = json.dumps(report.criteria_results, ensure_ascii=False)
        async with self._session_factory() as session:
            await session.execute(_INSERT, params)
            await session.commit()
            row = (
                (
                    await session.execute(
                        _SELECT_FOR_RUN,
                        {"workspace_id": report.workspace_id, "run_id": report.run_id},
                    )
                )
                .mappings()
                .first()
            )
        if row is None:  # pragma: no cover - unreachable after insert/conflict
            return report
        return _row_to_report(row)

    async def get_for_run(self, workspace_id: str, run_id: str) -> VerificationReport | None:
        async with self._session_factory() as session:
            row = (
                (
                    await session.execute(
                        _SELECT_FOR_RUN, {"workspace_id": workspace_id, "run_id": run_id}
                    )
                )
                .mappings()
                .first()
            )
        return None if row is None else _row_to_report(row)

    async def list_for_task(
        self, workspace_id: str, task_id: str, limit: int = 20
    ) -> list[VerificationReport]:
        async with self._session_factory() as session:
            rows = (
                (
                    await session.execute(
                        _SELECT_FOR_TASK,
                        {"workspace_id": workspace_id, "task_id": task_id, "limit": limit},
                    )
                )
                .mappings()
                .all()
            )
        return [_row_to_report(r) for r in rows]
