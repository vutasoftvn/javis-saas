from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Protocol

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agent.assets.contracts import (
    AssetConflictError,
    AssetEvaluationResult,
    AssetImmutableError,
    AssetKind,
    AssetLifecycle,
    AssetNotFoundError,
    AssetOrigin,
    AssetScope,
    PinnedAssetIdentity,
    WorkspaceAssetDraft,
    WorkspaceAssetVersion,
)


def compute_canonical_hash(content: dict[str, Any]) -> str:
    serialized = json.dumps(content, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(serialized.encode('utf-8')).hexdigest()}"


class WorkspaceAssetRepository(Protocol):
    async def create_draft(
        self, workspace_id: str, draft: WorkspaceAssetDraft
    ) -> WorkspaceAssetVersion: ...
    async def clone_to_draft(
        self,
        workspace_id: str,
        source: PinnedAssetIdentity,
        target_scope: AssetScope,
        source_content: dict[str, Any],
        created_by: str,
    ) -> WorkspaceAssetVersion: ...
    async def get_version(
        self, workspace_id: str, asset_id: str, version: str
    ) -> WorkspaceAssetVersion | None: ...
    async def get_latest_version(
        self, workspace_id: str, asset_id: str
    ) -> WorkspaceAssetVersion | None: ...
    async def replace_draft_content(
        self, workspace_id: str, asset_id: str, version: str, content: dict[str, Any]
    ) -> WorkspaceAssetVersion: ...
    async def publish(
        self, workspace_id: str, asset_id: str, version: str, expected_hash: str
    ) -> WorkspaceAssetVersion: ...
    async def record_evaluation(self, evaluation: AssetEvaluationResult) -> None: ...
    async def get_latest_evaluation(
        self, workspace_id: str, asset_id: str, version: str
    ) -> AssetEvaluationResult | None: ...


class InMemoryWorkspaceAssetRepository:
    def __init__(self) -> None:
        # key: (workspace_id, asset_id, version)
        self._versions: dict[tuple[str, str, str], WorkspaceAssetVersion] = {}
        # key: (workspace_id, asset_id, version) -> list of evaluations
        self._evaluations: dict[tuple[str, str, str], list[AssetEvaluationResult]] = {}

    async def create_draft(
        self, workspace_id: str, draft: WorkspaceAssetDraft
    ) -> WorkspaceAssetVersion:
        key = (workspace_id, draft.asset_id, draft.version)
        definition_hash = compute_canonical_hash(draft.content)

        version = WorkspaceAssetVersion(
            workspace_id=workspace_id,
            asset_id=draft.asset_id,
            kind=draft.kind,
            version=draft.version,
            definition_hash=definition_hash,
            content_json=draft.content,
            lifecycle=AssetLifecycle.DRAFT,
            scope=draft.scope,
            created_by=draft.created_by,
            origin=draft.origin,
            created_at=datetime.utcnow(),
        )
        self._versions[key] = version
        return version

    async def clone_to_draft(
        self,
        workspace_id: str,
        source: PinnedAssetIdentity,
        target_scope: AssetScope,
        source_content: dict[str, Any],
        created_by: str,
    ) -> WorkspaceAssetVersion:
        clone_asset_id = f"clone.{source.asset_id}"
        clone_version = "0.1.0"
        definition_hash = compute_canonical_hash(source_content)

        origin = AssetOrigin(
            kind="CLONE",
            asset_id=source.asset_id,
            version=source.version,
            definition_hash=source.definition_hash,
        )

        version = WorkspaceAssetVersion(
            workspace_id=workspace_id,
            asset_id=clone_asset_id,
            kind=source.kind,
            version=clone_version,
            definition_hash=definition_hash,
            content_json=source_content,
            lifecycle=AssetLifecycle.DRAFT,
            scope=target_scope,
            created_by=created_by,
            origin=origin,
            created_at=datetime.utcnow(),
        )
        self._versions[(workspace_id, clone_asset_id, clone_version)] = version
        return version

    async def get_version(
        self, workspace_id: str, asset_id: str, version: str
    ) -> WorkspaceAssetVersion | None:
        return self._versions.get((workspace_id, asset_id, version))

    async def get_latest_version(
        self, workspace_id: str, asset_id: str
    ) -> WorkspaceAssetVersion | None:
        candidates = [
            v
            for (ws, a_id, _), v in self._versions.items()
            if ws == workspace_id and a_id == asset_id
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda x: x.created_at)

    async def replace_draft_content(
        self, workspace_id: str, asset_id: str, version: str, content: dict[str, Any]
    ) -> WorkspaceAssetVersion:
        key = (workspace_id, asset_id, version)
        item = self._versions.get(key)
        if not item:
            raise AssetNotFoundError(
                f"Asset version {asset_id}:{version} not found in workspace {workspace_id}"
            )

        if item.lifecycle not in (AssetLifecycle.DRAFT, AssetLifecycle.CANDIDATE):
            raise AssetImmutableError(
                f"Cannot mutate content of asset in lifecycle {item.lifecycle.value}"
            )

        new_hash = compute_canonical_hash(content)
        updated = WorkspaceAssetVersion(
            workspace_id=item.workspace_id,
            asset_id=item.asset_id,
            kind=item.kind,
            version=item.version,
            definition_hash=new_hash,
            content_json=content,
            lifecycle=item.lifecycle,
            scope=item.scope,
            created_by=item.created_by,
            origin=item.origin,
            evaluation_summary=item.evaluation_summary,
            created_at=item.created_at,
        )
        self._versions[key] = updated
        return updated

    async def publish(
        self, workspace_id: str, asset_id: str, version: str, expected_hash: str
    ) -> WorkspaceAssetVersion:
        latest = self._versions.get((workspace_id, asset_id, version))
        if not latest:
            raise AssetNotFoundError(
                f"Asset version {asset_id}:{version} not found in workspace {workspace_id}"
            )
        if latest.definition_hash != expected_hash:
            raise AssetConflictError(
                f"expected_hash mismatch: expected {expected_hash}, found {latest.definition_hash}"
            )

        if latest.lifecycle == AssetLifecycle.PUBLISHED:
            return latest

        published = WorkspaceAssetVersion(
            workspace_id=latest.workspace_id,
            asset_id=latest.asset_id,
            kind=latest.kind,
            version=latest.version,
            definition_hash=latest.definition_hash,
            content_json=latest.content_json,
            lifecycle=AssetLifecycle.PUBLISHED,
            scope=latest.scope,
            created_by=latest.created_by,
            origin=latest.origin,
            evaluation_summary=latest.evaluation_summary,
            created_at=latest.created_at,
            published_at=datetime.utcnow(),
        )
        self._versions[(workspace_id, asset_id, version)] = published
        return published

    async def record_evaluation(self, evaluation: AssetEvaluationResult) -> None:
        key = (evaluation.workspace_id, evaluation.asset_id, evaluation.version)
        if key not in self._evaluations:
            self._evaluations[key] = []
        self._evaluations[key].append(evaluation)

        # Cập nhật evaluation summary vào version
        version = self._versions.get(key)
        if version:
            version.evaluation_summary = {
                "status": evaluation.status,
                "evaluation_id": evaluation.evaluation_id,
                "evaluated_at": evaluation.evaluated_at.isoformat(),
            }

    async def get_latest_evaluation(
        self, workspace_id: str, asset_id: str, version: str
    ) -> AssetEvaluationResult | None:
        evals = self._evaluations.get((workspace_id, asset_id, version), [])
        if not evals:
            return None
        return sorted(evals, key=lambda e: e.evaluated_at, reverse=True)[0]


class PostgresWorkspaceAssetRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create_draft(
        self, workspace_id: str, draft: WorkspaceAssetDraft
    ) -> WorkspaceAssetVersion:
        definition_hash = compute_canonical_hash(draft.content)
        async with self._session_factory() as session:
            # 1. Upsert workspace_assets
            stmt_asset = text(
                """
                INSERT INTO agent.workspace_assets (
                    workspace_id, asset_id, kind, name, description, scope_kind, project_id,
                    origin_kind, origin_asset_id, origin_version, origin_definition_hash,
                    current_draft_version, created_by, created_at, updated_at
                ) VALUES (
                    :ws_id, :asset_id, :kind, :name, :description, :scope_kind, :project_id,
                    :origin_kind, :origin_asset_id, :origin_version, :origin_def_hash,
                    :draft_ver, :created_by, now(), now()
                )
                ON CONFLICT (workspace_id, asset_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    current_draft_version = EXCLUDED.current_draft_version,
                    updated_at = now()
                """
            )
            await session.execute(
                stmt_asset,
                {
                    "ws_id": workspace_id,
                    "asset_id": draft.asset_id,
                    "kind": draft.kind.value,
                    "name": draft.name,
                    "description": draft.description,
                    "scope_kind": draft.scope.kind,
                    "project_id": draft.scope.project_id,
                    "origin_kind": draft.origin.kind if draft.origin else "SCRATCH",
                    "origin_asset_id": draft.origin.asset_id if draft.origin else None,
                    "origin_version": draft.origin.version if draft.origin else None,
                    "origin_def_hash": draft.origin.definition_hash if draft.origin else None,
                    "draft_ver": draft.version,
                    "created_by": draft.created_by,
                },
            )

            # 2. Insert version
            stmt_ver = text(
                """
                INSERT INTO agent.workspace_asset_versions (
                    workspace_id, asset_id, version, definition_hash, content_json,
                    lifecycle, scope_kind, project_id, origin_json, created_by, created_at
                ) VALUES (
                    :ws_id, :asset_id, :ver, :def_hash, :content,
                    'DRAFT', :scope_kind, :project_id, :origin_json, :created_by, now()
                )
                """
            )
            origin_dict = (
                {
                    "kind": draft.origin.kind,
                    "asset_id": draft.origin.asset_id,
                    "version": draft.origin.version,
                    "definition_hash": draft.origin.definition_hash,
                }
                if draft.origin
                else None
            )

            await session.execute(
                stmt_ver,
                {
                    "ws_id": workspace_id,
                    "asset_id": draft.asset_id,
                    "ver": draft.version,
                    "def_hash": definition_hash,
                    "content": json.dumps(draft.content),
                    "scope_kind": draft.scope.kind,
                    "project_id": draft.scope.project_id,
                    "origin_json": json.dumps(origin_dict) if origin_dict else None,
                    "created_by": draft.created_by,
                },
            )
            await session.commit()

        return WorkspaceAssetVersion(
            workspace_id=workspace_id,
            asset_id=draft.asset_id,
            kind=draft.kind,
            version=draft.version,
            definition_hash=definition_hash,
            content_json=draft.content,
            lifecycle=AssetLifecycle.DRAFT,
            scope=draft.scope,
            created_by=draft.created_by,
            origin=draft.origin,
            created_at=datetime.utcnow(),
        )

    async def clone_to_draft(
        self,
        workspace_id: str,
        source: PinnedAssetIdentity,
        target_scope: AssetScope,
        source_content: dict[str, Any],
        created_by: str,
    ) -> WorkspaceAssetVersion:
        clone_asset_id = f"clone.{source.asset_id}"
        clone_version = "0.1.0"
        origin = AssetOrigin(
            kind="CLONE",
            asset_id=source.asset_id,
            version=source.version,
            definition_hash=source.definition_hash,
        )
        draft = WorkspaceAssetDraft(
            asset_id=clone_asset_id,
            kind=source.kind,
            version=clone_version,
            name=f"Clone of {source.asset_id}",
            description=f"Cloned from {source.asset_id} v{source.version}",
            content=source_content,
            scope=target_scope,
            created_by=created_by,
            origin=origin,
        )
        return await self.create_draft(workspace_id, draft)

    def _row_to_version(self, row: Any) -> WorkspaceAssetVersion:
        origin = None
        if row["origin_json"]:
            raw_origin = (
                row["origin_json"]
                if isinstance(row["origin_json"], dict)
                else json.loads(row["origin_json"])
            )
            origin = AssetOrigin(
                kind=raw_origin.get("kind", "CLONE"),
                asset_id=raw_origin.get("asset_id", ""),
                version=raw_origin.get("version", ""),
                definition_hash=raw_origin.get("definition_hash", ""),
            )

        raw_content = row["content_json"]
        content = raw_content if isinstance(raw_content, dict) else json.loads(raw_content)

        scope = AssetScope(kind=row["scope_kind"], project_id=row["project_id"])
        eval_summary = row["evaluation_summary"]
        if eval_summary and isinstance(eval_summary, str):
            eval_summary = json.loads(eval_summary)

        return WorkspaceAssetVersion(
            workspace_id=row["workspace_id"],
            asset_id=row["asset_id"],
            kind=AssetKind(row["kind"]),
            version=row["version"],
            definition_hash=row["definition_hash"],
            content_json=content,
            lifecycle=AssetLifecycle(row["lifecycle"]),
            scope=scope,
            created_by=row["created_by"],
            origin=origin,
            evaluation_summary=eval_summary,
            created_at=row["created_at"],
            published_at=row["published_at"],
        )

    async def get_version(
        self, workspace_id: str, asset_id: str, version: str
    ) -> WorkspaceAssetVersion | None:
        async with self._session_factory() as session:
            stmt = text(
                """
                SELECT v.workspace_id, v.asset_id, a.kind, v.version, v.definition_hash, v.content_json,
                       lifecycle, scope_kind, project_id, origin_json, evaluation_summary,
                       created_by, created_at, published_at
                FROM agent.workspace_asset_versions v
                INNER JOIN agent.workspace_assets a
                    ON a.workspace_id = v.workspace_id AND a.asset_id = v.asset_id
                WHERE v.workspace_id = :ws_id AND v.asset_id = :asset_id AND v.version = :ver
                """
            )
            res = await session.execute(
                stmt, {"ws_id": workspace_id, "asset_id": asset_id, "ver": version}
            )
            row = res.mappings().first()
            if not row:
                return None
            return self._row_to_version(row)

    async def get_latest_version(
        self, workspace_id: str, asset_id: str
    ) -> WorkspaceAssetVersion | None:
        async with self._session_factory() as session:
            stmt = text(
                """
                SELECT v.workspace_id, v.asset_id, a.kind, v.version, v.definition_hash, v.content_json,
                       lifecycle, scope_kind, project_id, origin_json, evaluation_summary,
                       created_by, created_at, published_at
                FROM agent.workspace_asset_versions v
                INNER JOIN agent.workspace_assets a
                    ON a.workspace_id = v.workspace_id AND a.asset_id = v.asset_id
                WHERE v.workspace_id = :ws_id AND v.asset_id = :asset_id
                ORDER BY v.created_at DESC
                LIMIT 1
                """
            )
            res = await session.execute(stmt, {"ws_id": workspace_id, "asset_id": asset_id})
            row = res.mappings().first()
            if not row:
                return None
            return self._row_to_version(row)

    async def replace_draft_content(
        self, workspace_id: str, asset_id: str, version: str, content: dict[str, Any]
    ) -> WorkspaceAssetVersion:
        current = await self.get_version(workspace_id, asset_id, version)
        if not current:
            raise AssetNotFoundError(f"Asset version {asset_id}:{version} not found")
        if current.lifecycle not in (AssetLifecycle.DRAFT, AssetLifecycle.CANDIDATE):
            raise AssetImmutableError(
                f"Cannot mutate content of asset in lifecycle {current.lifecycle.value}"
            )

        new_hash = compute_canonical_hash(content)
        async with self._session_factory() as session:
            stmt = text(
                """
                UPDATE agent.workspace_asset_versions
                SET content_json = :content, definition_hash = :def_hash
                WHERE workspace_id = :ws_id AND asset_id = :asset_id AND version = :ver
                """
            )
            await session.execute(
                stmt,
                {
                    "ws_id": workspace_id,
                    "asset_id": asset_id,
                    "ver": version,
                    "content": json.dumps(content),
                    "def_hash": new_hash,
                },
            )
            await session.commit()

        current.content_json = content
        current.definition_hash = new_hash
        return current

    async def publish(
        self, workspace_id: str, asset_id: str, version: str, expected_hash: str
    ) -> WorkspaceAssetVersion:
        async with self._session_factory() as session:
            stmt = text(
                """
                SELECT definition_hash, lifecycle
                FROM agent.workspace_asset_versions
                WHERE workspace_id = :ws_id AND asset_id = :asset_id AND version = :ver
                """
            )
            res = await session.execute(
                stmt, {"ws_id": workspace_id, "asset_id": asset_id, "ver": version}
            )
            row = res.mappings().first()
            if not row:
                raise AssetNotFoundError(f"Asset {asset_id} not found in workspace {workspace_id}")

            if row["definition_hash"] != expected_hash:
                raise AssetConflictError(
                    f"expected_hash mismatch: expected {expected_hash}, found {row['definition_hash']}"
                )

            stmt_update = text(
                """
                UPDATE agent.workspace_asset_versions
                SET lifecycle = 'PUBLISHED', published_at = now()
                WHERE workspace_id = :ws_id AND asset_id = :asset_id AND version = :ver
                """
            )
            await session.execute(
                stmt_update, {"ws_id": workspace_id, "asset_id": asset_id, "ver": version}
            )

            stmt_asset_update = text(
                """
                UPDATE agent.workspace_assets
                SET published_version = :ver, updated_at = now()
                WHERE workspace_id = :ws_id AND asset_id = :asset_id
                """
            )
            await session.execute(
                stmt_asset_update, {"ws_id": workspace_id, "asset_id": asset_id, "ver": version}
            )
            await session.commit()

        updated = await self.get_version(workspace_id, asset_id, version)
        assert updated is not None
        return updated

    async def record_evaluation(self, evaluation: AssetEvaluationResult) -> None:
        async with self._session_factory() as session:
            stmt_eval = text(
                """
                INSERT INTO agent.asset_evaluations (
                    evaluation_id, workspace_id, asset_id, version, definition_hash,
                    status, structural_result, negative_policy_result, scenario_suite_result,
                    evidence_refs, cost_latency_summary, evaluator_version, evaluated_at
                ) VALUES (
                    :eval_id, :ws_id, :asset_id, :ver, :def_hash,
                    :status, :struct_res, :neg_res, :scen_res,
                    :ev_refs, :cost_summary, :eval_ver, now()
                )
                """
            )
            await session.execute(
                stmt_eval,
                {
                    "eval_id": evaluation.evaluation_id,
                    "ws_id": evaluation.workspace_id,
                    "asset_id": evaluation.asset_id,
                    "ver": evaluation.version,
                    "def_hash": evaluation.definition_hash,
                    "status": evaluation.status,
                    "struct_res": json.dumps(evaluation.structural_result),
                    "neg_res": json.dumps(evaluation.negative_policy_result),
                    "scen_res": json.dumps(evaluation.scenario_suite_result),
                    "ev_refs": json.dumps(evaluation.evidence_refs),
                    "cost_summary": json.dumps(evaluation.cost_latency_summary),
                    "eval_ver": evaluation.evaluator_version,
                },
            )

            summary = {
                "status": evaluation.status,
                "evaluation_id": evaluation.evaluation_id,
                "evaluated_at": evaluation.evaluated_at.isoformat(),
            }
            stmt_ver = text(
                """
                UPDATE agent.workspace_asset_versions
                SET evaluation_summary = :summary
                WHERE workspace_id = :ws_id AND asset_id = :asset_id AND version = :ver
                """
            )
            await session.execute(
                stmt_ver,
                {
                    "ws_id": evaluation.workspace_id,
                    "asset_id": evaluation.asset_id,
                    "ver": evaluation.version,
                    "summary": json.dumps(summary),
                },
            )
            await session.commit()

    async def get_latest_evaluation(
        self, workspace_id: str, asset_id: str, version: str
    ) -> AssetEvaluationResult | None:
        async with self._session_factory() as session:
            stmt = text(
                """
                SELECT evaluation_id, workspace_id, asset_id, version, definition_hash,
                       status, structural_result, negative_policy_result, scenario_suite_result,
                       evidence_refs, cost_latency_summary, evaluator_version, evaluated_at
                FROM agent.asset_evaluations
                WHERE workspace_id = :ws_id AND asset_id = :asset_id AND version = :ver
                ORDER BY evaluated_at DESC
                LIMIT 1
                """
            )
            res = await session.execute(
                stmt, {"ws_id": workspace_id, "asset_id": asset_id, "ver": version}
            )
            row = res.mappings().first()
            if not row:
                return None

            return AssetEvaluationResult(
                evaluation_id=row["evaluation_id"],
                workspace_id=row["workspace_id"],
                asset_id=row["asset_id"],
                version=row["version"],
                definition_hash=row["definition_hash"],
                status=row["status"],
                structural_result=row["structural_result"]
                if isinstance(row["structural_result"], dict)
                else json.loads(row["structural_result"]),
                negative_policy_result=row["negative_policy_result"]
                if isinstance(row["negative_policy_result"], dict)
                else json.loads(row["negative_policy_result"]),
                scenario_suite_result=row["scenario_suite_result"]
                if isinstance(row["scenario_suite_result"], dict)
                else json.loads(row["scenario_suite_result"]),
                evidence_refs=row["evidence_refs"]
                if isinstance(row["evidence_refs"], list)
                else json.loads(row["evidence_refs"]),
                cost_latency_summary=row["cost_latency_summary"]
                if isinstance(row["cost_latency_summary"], dict)
                else json.loads(row["cost_latency_summary"]),
                evaluator_version=row["evaluator_version"],
                evaluated_at=row["evaluated_at"],
            )
