from __future__ import annotations

import json
from typing import Any, Optional, Protocol, runtime_checkable

from sqlalchemy import text

from agent_core.evals.artifacts import EvalCaseResult, EvalRun, EvalSuite
from agent_core.governance.contracts import PinnedSpecIdentity
from agent_core.registry.repository import SpecVersionHashConflictError

__all__ = ["EvalRepository", "InMemoryEvalRepository", "PostgresEvalRepository"]


@runtime_checkable
class EvalRepository(Protocol):
    """Protocol cho persistence Eval artifact (EvalSuite/EvalRun/
    EvalCaseResult) theo agent_evals.* (migration 008 + 013, Wave M3)."""

    async def publish_suite(self, suite: EvalSuite) -> EvalSuite: ...
    async def get_suite(self, suite_id: str, version: str) -> Optional[EvalSuite]: ...
    async def create_run(self, run: EvalRun) -> EvalRun: ...
    async def update_run_status(
        self, run_id: str, status: str, pass_rate: Optional[float] = None
    ) -> EvalRun: ...
    async def get_run(self, run_id: str) -> Optional[EvalRun]: ...
    async def record_case_result(self, result: EvalCaseResult) -> EvalCaseResult: ...
    async def list_case_results(self, eval_run_id: str) -> list[EvalCaseResult]: ...


class InMemoryEvalRepository:
    """In-memory implementation — chỉ dùng test/local dev, không dùng
    production (không durable qua restart)."""

    def __init__(self) -> None:
        self._suites: dict[tuple[str, str], EvalSuite] = {}
        self._runs: dict[str, EvalRun] = {}
        self._results: dict[str, list[EvalCaseResult]] = {}

    async def publish_suite(self, suite: EvalSuite) -> EvalSuite:
        pinned = suite.with_hash() if suite.definition_hash is None else suite
        key = (pinned.id, pinned.version)
        existing = self._suites.get(key)
        if existing is not None:
            if existing.definition_hash != pinned.definition_hash:
                raise SpecVersionHashConflictError(
                    "eval_suite", pinned.id, pinned.version, existing.definition_hash, pinned.definition_hash
                )
            return existing.model_copy(deep=True)
        stored = pinned.model_copy(deep=True)
        self._suites[key] = stored
        return stored.model_copy(deep=True)

    async def get_suite(self, suite_id: str, version: str) -> Optional[EvalSuite]:
        r = self._suites.get((suite_id, version))
        return r.model_copy(deep=True) if r else None

    async def create_run(self, run: EvalRun) -> EvalRun:
        stored = run.model_copy(deep=True)
        self._runs[stored.run_id] = stored
        self._results[stored.run_id] = []
        return stored.model_copy(deep=True)

    async def update_run_status(
        self, run_id: str, status: str, pass_rate: Optional[float] = None
    ) -> EvalRun:
        existing = self._runs[run_id]
        updated = existing.model_copy(update={"status": status, "pass_rate": pass_rate})
        self._runs[run_id] = updated
        return updated.model_copy(deep=True)

    async def get_run(self, run_id: str) -> Optional[EvalRun]:
        r = self._runs.get(run_id)
        return r.model_copy(deep=True) if r else None

    async def record_case_result(self, result: EvalCaseResult) -> EvalCaseResult:
        stored = result.model_copy(deep=True)
        self._results.setdefault(stored.eval_run_id, []).append(stored)
        return stored.model_copy(deep=True)

    async def list_case_results(self, eval_run_id: str) -> list[EvalCaseResult]:
        return [r.model_copy(deep=True) for r in self._results.get(eval_run_id, [])]


class PostgresEvalRepository:
    """PostgreSQL implementation — persist vào agent_evals.suites/runs/
    results (migration 008 + 013)."""

    def __init__(self, db_session_factory: Any) -> None:
        if db_session_factory is None:
            raise ValueError("PostgresEvalRepository requires a valid db_session_factory.")
        self._session_factory = db_session_factory

    async def publish_suite(self, suite: EvalSuite) -> EvalSuite:
        pinned = suite.with_hash() if suite.definition_hash is None else suite
        existing = await self.get_suite(pinned.id, pinned.version)
        if existing is not None:
            if existing.definition_hash != pinned.definition_hash:
                raise SpecVersionHashConflictError(
                    "eval_suite", pinned.id, pinned.version, existing.definition_hash, pinned.definition_hash
                )
            return existing

        async with self._session_factory() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO agent_evals.suites (
                        suite_id, name, target_kind, target_id, description, version, definition_hash, content
                    ) VALUES (
                        :suite_id, :name, :target_kind, :target_id, :description, :version, :definition_hash, :content
                    )
                    ON CONFLICT (suite_id) DO NOTHING
                    """
                ),
                {
                    "suite_id": pinned.id,
                    "name": pinned.name or pinned.id,
                    "target_kind": pinned.target_kind,
                    "target_id": pinned.target_id,
                    "description": pinned.description,
                    "version": pinned.version,
                    "definition_hash": pinned.definition_hash,
                    "content": json.dumps(pinned.model_dump(mode="json")),
                },
            )
            await session.commit()

        stored = await self.get_suite(pinned.id, pinned.version)
        if stored is not None:
            if stored.definition_hash != pinned.definition_hash:
                raise SpecVersionHashConflictError(
                    "eval_suite", pinned.id, pinned.version, stored.definition_hash, pinned.definition_hash
                )
            return stored

        # Không tìm thấy sau INSERT: suite_id (PK) đã bị chiếm bởi 1 version
        # KHÁC của cùng suite — agent_evals.suites hiện chỉ giữ 1 row/suite_id
        # (giới hạn đã biết của Wave M3, xem "Sau khi hoàn thành plan này"
        # cuối file — hỗ trợ nhiều version cùng tồn tại cần đổi PK, ngoài
        # phạm vi Task 5). Raise rõ ràng thay vì âm thầm coi publish thành
        # công trong khi không ghi được gì.
        raise RuntimeError(
            f"EvalSuite '{pinned.id}' đã publish với version khác trong "
            f"agent_evals.suites — bảng này hiện chỉ giữ 1 version/suite_id."
        )

    async def get_suite(self, suite_id: str, version: str) -> Optional[EvalSuite]:
        async with self._session_factory() as session:
            res = await session.execute(
                text(
                    """
                    SELECT suite_id, name, target_kind, target_id, description, version, definition_hash, content
                    FROM agent_evals.suites
                    WHERE suite_id = :suite_id AND version = :version
                    """
                ),
                {"suite_id": suite_id, "version": version},
            )
            row = res.mappings().first()
            if row is None:
                return None
            content = row["content"]
            if content is not None:
                # content JSONB đã có toàn bộ field (case_ids/scorer_version/
                # pass_thresholds/metadata) — ưu tiên reconstruct từ đây để
                # đúng tuyệt đối với definition_hash đã lưu.
                if isinstance(content, str):
                    content = json.loads(content)
                return EvalSuite(**content)
            # Fallback cho row cũ (publish trước khi content column tồn tại) —
            # chỉ tái tạo được identity, không tái tạo được case_ids/config.
            return EvalSuite(
                id=row["suite_id"],
                version=row["version"],
                target_kind=row["target_kind"],
                target_id=row["target_id"],
                name=row["name"] or "",
                description=row["description"] or "",
                definition_hash=row["definition_hash"],
            )

    async def create_run(self, run: EvalRun) -> EvalRun:
        async with self._session_factory() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO agent_evals.runs (
                        eval_run_id, suite_id, target_kind, target_id, target_version, target_definition_hash,
                        suite_version, suite_definition_hash, status, pass_rate, started_at
                    ) VALUES (
                        :eval_run_id, :suite_id, :target_kind, :target_id, :target_version, :target_definition_hash,
                        :suite_version, :suite_definition_hash, :status, :pass_rate, :started_at
                    )
                    """
                ),
                {
                    "eval_run_id": run.run_id,
                    "suite_id": run.suite_ref.spec_id if run.suite_ref else None,
                    "target_kind": run.target_ref.spec_kind,
                    "target_id": run.target_ref.spec_id,
                    "target_version": run.target_ref.spec_version,
                    "target_definition_hash": run.target_ref.definition_hash,
                    "suite_version": run.suite_ref.spec_version if run.suite_ref else None,
                    "suite_definition_hash": run.suite_ref.definition_hash if run.suite_ref else None,
                    "status": run.status,
                    "pass_rate": run.pass_rate,
                    "started_at": run.started_at,
                },
            )
            await session.commit()
        return run

    async def update_run_status(
        self, run_id: str, status: str, pass_rate: Optional[float] = None
    ) -> EvalRun:
        async with self._session_factory() as session:
            await session.execute(
                text(
                    """
                    UPDATE agent_evals.runs
                    SET status = :status, pass_rate = :pass_rate,
                        completed_at = CASE WHEN CAST(:status AS VARCHAR) IN ('completed', 'failed') THEN NOW() ELSE completed_at END
                    WHERE eval_run_id = :run_id
                    """
                ),
                {"run_id": run_id, "status": status, "pass_rate": pass_rate},
            )
            await session.commit()
        updated = await self.get_run(run_id)
        if updated is None:
            raise ValueError(f"EvalRun '{run_id}' not found after update")
        return updated

    async def get_run(self, run_id: str) -> Optional[EvalRun]:
        async with self._session_factory() as session:
            res = await session.execute(
                text(
                    """
                    SELECT eval_run_id, target_kind, target_id, target_version, target_definition_hash,
                           suite_id, suite_version, suite_definition_hash, status, pass_rate, started_at, completed_at
                    FROM agent_evals.runs
                    WHERE eval_run_id = :run_id
                    """
                ),
                {"run_id": run_id},
            )
            row = res.mappings().first()
            if row is None:
                return None
            suite_ref = None
            if row["suite_version"] and row["suite_definition_hash"]:
                suite_ref = PinnedSpecIdentity(
                    spec_kind="eval_suite",
                    spec_id=row["suite_id"],
                    spec_version=row["suite_version"],
                    definition_hash=row["suite_definition_hash"],
                )
            return EvalRun(
                run_id=row["eval_run_id"],
                target_ref=PinnedSpecIdentity(
                    spec_kind=row["target_kind"],
                    spec_id=row["target_id"],
                    spec_version=row["target_version"] or "",
                    definition_hash=row["target_definition_hash"] or "",
                ),
                suite_ref=suite_ref,
                status=row["status"],
                pass_rate=row["pass_rate"],
                started_at=row["started_at"],
                completed_at=row["completed_at"],
            )

    async def record_case_result(self, result: EvalCaseResult) -> EvalCaseResult:
        async with self._session_factory() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO agent_evals.results (
                        result_id, eval_run_id, case_id, passed, score, details, error_message, evaluated_at
                    ) VALUES (
                        :result_id, :eval_run_id, :case_id, :passed, :score, :details, :error_message, :evaluated_at
                    )
                    """
                ),
                {
                    "result_id": result.result_id,
                    "eval_run_id": result.eval_run_id,
                    "case_id": result.case_id,
                    "passed": result.passed,
                    "score": result.score,
                    "details": result.details,
                    "error_message": result.error,
                    "evaluated_at": result.evaluated_at,
                },
            )
            await session.commit()
        return result

    async def list_case_results(self, eval_run_id: str) -> list[EvalCaseResult]:
        async with self._session_factory() as session:
            res = await session.execute(
                text(
                    """
                    SELECT result_id, eval_run_id, case_id, passed, score, details, error_message, evaluated_at
                    FROM agent_evals.results
                    WHERE eval_run_id = :eval_run_id
                    ORDER BY evaluated_at ASC
                    """
                ),
                {"eval_run_id": eval_run_id},
            )
            return [
                EvalCaseResult(
                    result_id=r["result_id"],
                    eval_run_id=r["eval_run_id"],
                    case_id=r["case_id"],
                    passed=r["passed"],
                    score=r["score"],
                    details=r["details"] or "",
                    error=r["error_message"],
                    evaluated_at=r["evaluated_at"],
                )
                for r in res.mappings().all()
            ]
