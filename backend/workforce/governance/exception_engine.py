"""Exception Escalation Engine — Phase 6

Phát hiện và leo thang tự động các ngoại lệ trong AI Workforce:
- AGENT_STALL: Run không phản hồi vượt ngưỡng timeout
- BUDGET_OVERFLOW: Chi phí vượt hạn mức
- CONSECUTIVE_ERROR: Nhiều lần lỗi liên tiếp
- STAGE_MISMATCH: Agent thuộc domain bị deemphasized ở stage hiện tại
"""
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from workforce.models import (
    LegacyPlatformAgentRun, AgentBudget, CostLedger, EscalationRecord
)
from core.snowflake import generate_snowflake_id


class ExceptionType(str, Enum):
    AGENT_STALL = "AGENT_STALL"               # Run > timeout_minutes không có step mới
    BUDGET_OVERFLOW = "BUDGET_OVERFLOW"        # Chi phí > AgentBudget.limit_usd
    CONSECUTIVE_ERROR = "CONSECUTIVE_ERROR"    # N lần fail liên tiếp
    STAGE_MISMATCH = "STAGE_MISMATCH"          # Agent domain bị locked ở stage hiện tại


class EscalationTier(str, Enum):
    AUTO_RETRY = "AUTO_RETRY"          # Tier 1: Hệ thống tự retry (transparent)
    LEAD_NOTIFY = "LEAD_NOTIFY"        # Tier 2: Thông báo Team Lead
    FOUNDER_GATE = "FOUNDER_GATE"      # Tier 3: Chặn — Founder phải quyết định


# Mapping exception type → tier mặc định ban đầu
_DEFAULT_TIERS: Dict[ExceptionType, EscalationTier] = {
    ExceptionType.AGENT_STALL: EscalationTier.AUTO_RETRY,
    ExceptionType.BUDGET_OVERFLOW: EscalationTier.FOUNDER_GATE,
    ExceptionType.CONSECUTIVE_ERROR: EscalationTier.LEAD_NOTIFY,
    ExceptionType.STAGE_MISMATCH: EscalationTier.LEAD_NOTIFY,
}

# Số lần AUTO_RETRY tối đa trước khi leo thang lên LEAD_NOTIFY
_MAX_AUTO_RETRY = 2

# Số lần CONSECUTIVE_ERROR ở LEAD_NOTIFY trước khi leo thang lên FOUNDER_GATE
_MAX_LEAD_NOTIFY_CONSECUTIVE = 2

# Ngưỡng stall timeout (phút)
STALL_TIMEOUT_SPECIALIST_MINUTES = 15
STALL_TIMEOUT_CODING_MINUTES = 30


class ExceptionEscalationEngine:
    """
    Engine phát hiện và leo thang exception trong AI Workforce.

    Được gọi bởi:
    1. Background watchdog (worker_main.py) mỗi 5 phút để scan stall + budget overflow
    2. Task Dispatcher khi phát hiện consecutive errors
    3. Stage-Aware Workforce Service khi phát hiện stage mismatch
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ---------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------

    async def detect_and_escalate_stall(
        self,
        workspace_id: Optional[int] = None,
        stall_timeout_minutes: int = STALL_TIMEOUT_SPECIALIST_MINUTES,
    ) -> List[Dict[str, Any]]:
        """
        Scan tất cả AgentRun đang chạy → phát hiện stall → tạo EscalationRecord.

        Returns: Danh sách escalation records vừa tạo (dạng dict).
        """
        cutoff_time = datetime.utcnow() - timedelta(minutes=stall_timeout_minutes)

        stmt = select(LegacyPlatformAgentRun).where(
            and_(
                LegacyPlatformAgentRun.status == "running",
                LegacyPlatformAgentRun.started_at <= cutoff_time,
            )
        )
        if workspace_id is not None:
            stmt = stmt.where(LegacyPlatformAgentRun.workspace_id == workspace_id)

        res = await self.db.execute(stmt)
        stalled_runs: List[LegacyPlatformAgentRun] = list(res.scalars().all())

        escalations = []
        for run in stalled_runs:
            # Kiểm tra nếu đã có OPEN escalation cho run này
            existing = await self._get_open_escalation_for_run(run.id, ExceptionType.AGENT_STALL)
            if existing:
                # Nếu đã AUTO_RETRY đủ lần → leo thang lên LEAD_NOTIFY
                await self._maybe_upgrade_tier(existing)
                continue

            # Xác định timeout phù hợp theo agent_type
            elapsed_minutes = int((datetime.utcnow() - run.started_at).total_seconds() / 60)

            record = await self._create_escalation(
                exception_type=ExceptionType.AGENT_STALL,
                tier=EscalationTier.AUTO_RETRY,
                agent_key=run.agent_key,
                workspace_id=run.workspace_id or workspace_id,
                run_id=run.id,
                details={
                    "stall_timeout_minutes": stall_timeout_minutes,
                    "elapsed_minutes": elapsed_minutes,
                    "run_started_at": run.started_at.isoformat(),
                },
            )
            escalations.append(self._record_to_dict(record))

        return escalations

    async def detect_and_escalate_budget_overflow(
        self,
        workspace_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Scan AgentBudget so với CostLedger → phát hiện vượt hạn mức → FOUNDER_GATE.

        Returns: Danh sách escalation records vừa tạo.
        """
        stmt = select(AgentBudget)
        if workspace_id is not None:
            stmt = stmt.where(AgentBudget.workspace_id == workspace_id)
        res = await self.db.execute(stmt)
        budgets: List[AgentBudget] = list(res.scalars().all())

        escalations = []
        for budget in budgets:
            if budget.spent_usd <= budget.limit_usd:
                continue

            # Kiểm tra đã có FOUNDER_GATE OPEN chưa
            existing = await self._get_open_escalation_for_agent(
                budget.agent_key,
                ExceptionType.BUDGET_OVERFLOW,
                workspace_id,
            )
            if existing:
                continue

            record = await self._create_escalation(
                exception_type=ExceptionType.BUDGET_OVERFLOW,
                tier=EscalationTier.FOUNDER_GATE,
                agent_key=budget.agent_key,
                workspace_id=budget.workspace_id or workspace_id,
                run_id=None,
                details={
                    "limit_usd": budget.limit_usd,
                    "spent_usd": float(budget.spent_usd),
                    "overflow_usd": float(budget.spent_usd - budget.limit_usd),
                    "cycle_type": budget.cycle_type,
                },
            )
            escalations.append(self._record_to_dict(record))

        return escalations

    async def create_consecutive_error_escalation(
        self,
        agent_key: str,
        run_id: int,
        error_count: int,
        workspace_id: Optional[int] = None,
        stage_code: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Tạo hoặc leo thang CONSECUTIVE_ERROR escalation.

        Gọi từ AgentRunnerService khi phát hiện nhiều lần fail liên tiếp.
        """
        existing = await self._get_open_escalation_for_agent(
            agent_key, ExceptionType.CONSECUTIVE_ERROR, workspace_id
        )

        if existing:
            upgraded = await self._maybe_upgrade_tier(existing, error_count=error_count)
            return self._record_to_dict(upgraded)

        # Tier ban đầu phụ thuộc số lần lỗi
        tier = EscalationTier.LEAD_NOTIFY if error_count < _MAX_LEAD_NOTIFY_CONSECUTIVE + 1 else EscalationTier.FOUNDER_GATE

        record = await self._create_escalation(
            exception_type=ExceptionType.CONSECUTIVE_ERROR,
            tier=tier,
            agent_key=agent_key,
            workspace_id=workspace_id,
            run_id=run_id,
            stage_code=stage_code,
            details={
                "error_count": error_count,
                "error_message": error_message or "",
            },
        )
        return self._record_to_dict(record)

    async def create_stage_mismatch_escalation(
        self,
        agent_key: str,
        agent_name: str,
        stage_code: str,
        workspace_id: Optional[int] = None,
        deemphasized_domains: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Tạo STAGE_MISMATCH LEAD_NOTIFY khi agent thuộc domain bị deemphasized
        được kích hoạt ở stage không phù hợp.
        """
        # Tránh tạo duplicate trong cùng stage
        existing = await self._get_open_escalation_for_agent(
            agent_key, ExceptionType.STAGE_MISMATCH, workspace_id
        )
        if existing and existing.stage_code == stage_code:
            return self._record_to_dict(existing)

        record = await self._create_escalation(
            exception_type=ExceptionType.STAGE_MISMATCH,
            tier=EscalationTier.LEAD_NOTIFY,
            agent_key=agent_key,
            workspace_id=workspace_id,
            run_id=None,
            stage_code=stage_code,
            details={
                "agent_name": agent_name,
                "stage_code": stage_code,
                "deemphasized_domains": deemphasized_domains or [],
                "note": f"Agent '{agent_name}' kích hoạt ở stage {stage_code} nhưng domain của agent bị deemphasized theo Stage Policy.",
            },
        )
        return self._record_to_dict(record)

    async def resolve_escalation(
        self,
        escalation_id: int,
        action: str,
        comment: Optional[str] = None,
        resolved_by: Optional[str] = None,
        workspace_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Resolve một escalation với action cụ thể.

        Args:
            escalation_id: ID của EscalationRecord
            action: 'retry' | 'reassign' | 'force_approve' | 'dismiss' | 'increase_budget'
            comment: Ghi chú của người resolve
            resolved_by: User ID hoặc tên người resolve
            workspace_id: Dùng để xác minh quyền

        Returns: Dict của EscalationRecord đã cập nhật

        Raises: ValueError nếu không tìm thấy hoặc đã resolved
        """
        stmt = select(EscalationRecord).where(EscalationRecord.id == escalation_id)
        if workspace_id is not None:
            stmt = stmt.where(EscalationRecord.workspace_id == workspace_id)
        res = await self.db.execute(stmt)
        record = res.scalars().first()

        if not record:
            raise ValueError(f"Escalation #{escalation_id} không tìm thấy")
        if record.status != "OPEN":
            raise ValueError(f"Escalation #{escalation_id} đã được xử lý (status={record.status})")

        valid_actions = {"retry", "reassign", "force_approve", "dismiss", "increase_budget", "block_permanently"}
        if action not in valid_actions:
            raise ValueError(f"Action '{action}' không hợp lệ. Dùng một trong: {valid_actions}")

        record.status = "RESOLVED"
        record.resolution_action = action
        record.resolution_comment = comment
        record.resolved_by = str(resolved_by) if resolved_by else None
        record.resolved_at = datetime.utcnow()

        self.db.add(record)
        return self._record_to_dict(record)

    async def list_active_escalations(
        self,
        workspace_id: Optional[int] = None,
        status: Optional[str] = "OPEN",
        exception_type: Optional[str] = None,
        tier: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Danh sách escalation records, mặc định chỉ OPEN."""
        stmt = select(EscalationRecord).order_by(desc(EscalationRecord.created_at))

        filters = []
        if workspace_id is not None:
            filters.append(EscalationRecord.workspace_id == workspace_id)
        if status:
            filters.append(EscalationRecord.status == status)
        if exception_type:
            filters.append(EscalationRecord.exception_type == exception_type)
        if tier:
            filters.append(EscalationRecord.tier == tier)
        if filters:
            stmt = stmt.where(and_(*filters))

        stmt = stmt.limit(limit)
        res = await self.db.execute(stmt)
        records = list(res.scalars().all())

        return [self._record_to_dict(r) for r in records]

    # ---------------------------------------------------------------
    # Private helpers
    # ---------------------------------------------------------------

    async def _create_escalation(
        self,
        exception_type: ExceptionType,
        tier: EscalationTier,
        agent_key: str,
        workspace_id: Optional[int],
        run_id: Optional[int] = None,
        stage_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> EscalationRecord:
        record = EscalationRecord(
            id=generate_snowflake_id(),
            exception_type=exception_type.value,
            tier=tier.value,
            agent_key=agent_key,
            workspace_id=workspace_id,
            run_id=run_id,
            stage_code=stage_code,
            details_jsonb=details or {},
            status="OPEN",
            created_at=datetime.utcnow(),
        )
        self.db.add(record)
        return record

    async def _get_open_escalation_for_run(
        self, run_id: int, exception_type: ExceptionType
    ) -> Optional[EscalationRecord]:
        stmt = select(EscalationRecord).where(
            and_(
                EscalationRecord.run_id == run_id,
                EscalationRecord.exception_type == exception_type.value,
                EscalationRecord.status == "OPEN",
            )
        )
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def _get_open_escalation_for_agent(
        self,
        agent_key: str,
        exception_type: ExceptionType,
        workspace_id: Optional[int],
    ) -> Optional[EscalationRecord]:
        filters = [
            EscalationRecord.agent_key == agent_key,
            EscalationRecord.exception_type == exception_type.value,
            EscalationRecord.status == "OPEN",
        ]
        if workspace_id is not None:
            filters.append(EscalationRecord.workspace_id == workspace_id)
        stmt = select(EscalationRecord).where(and_(*filters))
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def _maybe_upgrade_tier(
        self,
        record: EscalationRecord,
        error_count: Optional[int] = None,
    ) -> EscalationRecord:
        """Leo thang tier nếu đủ điều kiện."""
        details = dict(record.details_jsonb or {})

        if record.tier == EscalationTier.AUTO_RETRY.value:
            # Tăng retry_count
            retry_count = details.get("retry_count", 0) + 1
            details["retry_count"] = retry_count

            if retry_count >= _MAX_AUTO_RETRY:
                record.tier = EscalationTier.LEAD_NOTIFY.value
                details["upgrade_reason"] = f"Đã retry {retry_count} lần không thành công → leo thang LEAD_NOTIFY"

        elif record.tier == EscalationTier.LEAD_NOTIFY.value:
            if error_count is not None and error_count > _MAX_LEAD_NOTIFY_CONSECUTIVE + 1:
                record.tier = EscalationTier.FOUNDER_GATE.value
                details["upgrade_reason"] = f"Liên tiếp {error_count} lỗi → leo thang FOUNDER_GATE"

        record.details_jsonb = details
        record.updated_at = datetime.utcnow()
        self.db.add(record)
        return record

    def _record_to_dict(self, record: EscalationRecord) -> Dict[str, Any]:
        return {
            "id": record.id,
            "exception_type": record.exception_type,
            "tier": record.tier,
            "agent_key": record.agent_key,
            "run_id": record.run_id,
            "workspace_id": record.workspace_id,
            "stage_code": record.stage_code,
            "details": record.details_jsonb or {},
            "status": record.status,
            "resolution_action": record.resolution_action,
            "resolution_comment": getattr(record, "resolution_comment", None),
            "resolved_by": record.resolved_by,
            "resolved_at": record.resolved_at.isoformat() if record.resolved_at else None,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "updated_at": record.updated_at.isoformat() if getattr(record, "updated_at", None) else None,
        }
