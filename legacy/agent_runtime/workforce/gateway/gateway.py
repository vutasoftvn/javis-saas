import time
from typing import Dict, Any, Optional, Callable, Awaitable
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from workforce.identity.context import ExecutionContext
from workforce.models import AgentToolPermission, ToolDefinition
from workforce.registry.tool_registry import ToolRegistryService
from workforce.gateway.policy import RiskPolicyEvaluator, PolicyEvaluationResult
from workforce.gateway.secret_broker import SecretBroker
from workforce.gateway.approval import ApprovalService, ApprovalTicket
from workforce.tools.transports import (
    BaseToolAdapter, LocalToolAdapter, MCPToolAdapter,
    A2AToolAdapter, N8nToolAdapter, SandboxToolAdapter
)


class PermissionDeniedError(Exception):
    pass


class ApprovalRequiredError(Exception):
    def __init__(self, ticket: ApprovalTicket):
        self.ticket = ticket
        super().__init__(f"Tool execution paused for approval: ticket_id={ticket.id}")


class AgentGateway:
    """COSA Agent Gateway: Điểm kiểm soát tập trung duy nhất cho mọi Tool Execution."""

    def __init__(
        self,
        db: AsyncSession,
        tool_registry: ToolRegistryService,
        secret_broker: Optional[SecretBroker] = None,
        approval_service: Optional[ApprovalService] = None,
    ):
        self.db = db
        self.tool_registry = tool_registry
        self.secret_broker = secret_broker or SecretBroker(db)
        self.approval_service = approval_service or ApprovalService()
        self._handlers: Dict[str, Callable[[ExecutionContext, Dict[str, Any]], Awaitable[Any]]] = {}

        # Khởi tạo các Transport Adapters
        self.adapters: Dict[str, BaseToolAdapter] = {
            "local": LocalToolAdapter(),
            "mcp": MCPToolAdapter(),
            "a2a": A2AToolAdapter(),
            "n8n": N8nToolAdapter(),
            "sandbox": SandboxToolAdapter(),
        }

    def register_handler(
        self,
        tool_key: str,
        handler: Callable[[ExecutionContext, Dict[str, Any]], Awaitable[Any]]
    ):
        """Đăng ký hàm thực thi nội bộ cho tool_key."""
        self._handlers[tool_key] = handler

    async def execute(
        self,
        context: ExecutionContext,
        tool: str,
        args: Dict[str, Any],
        bypass_approval_check: bool = False,
    ) -> Any:
        """Thực thi tool có bảo vệ: Identity -> Permission -> Risk Policy -> Secret -> Dispatch -> Audit."""
        start_time = time.time()

        # 1. Tra cứu định nghĩa Tool
        tool_def = await self.tool_registry.get_tool_by_key(tool, context.workspace_id)
        if not tool_def:
            # Fallback tra cứu không theo workspace_id (global default)
            tool_def = await self.tool_registry.get_tool_by_key(tool, None)

        tool_risk_level = tool_def.risk_level if tool_def else 0
        requires_appr_flag = tool_def.requires_approval if tool_def else False

        # 2. Kiểm tra Ma trận phân quyền (Agent <-> Tool)
        if tool_def:
            stmt = select(AgentToolPermission).where(
                and_(
                    AgentToolPermission.agent_id == context.agent_id,
                    AgentToolPermission.tool_id == tool_def.id,
                )
            )
            if context.workspace_id:
                stmt = stmt.where(AgentToolPermission.workspace_id == context.workspace_id)
            res = await self.db.execute(stmt)
            perm = res.scalars().first()
            if perm is not None and not perm.allow_execute:
                raise PermissionDeniedError(
                    f"Agent '{context.agent_key}' is not authorized to execute tool '{tool}'"
                )
            if perm is not None and perm.requires_approval:
                requires_appr_flag = True

        # 3. Đánh giá Risk Policy (R0..R4)
        policy_res: PolicyEvaluationResult = RiskPolicyEvaluator.evaluate(
            tool_risk_level=tool_risk_level,
            requires_approval_flag=requires_appr_flag,
            agent_role=context.agent_key
        )

        if policy_res.requires_approval and not bypass_approval_check:
            ticket = await self.approval_service.create_approval_request(
                context=context,
                tool_key=tool,
                args=args,
                risk_level=policy_res.risk_level,
                reason=policy_res.reason
            )
            raise ApprovalRequiredError(ticket)

        # 4. Tìm handler thực thi hoặc ủy quyền cho Transport Adapter
        handler = self._handlers.get(tool)
        if handler:
            import inspect
            if inspect.iscoroutinefunction(handler):
                result = await handler(context, args)
            else:
                res = handler(context, args)
                if inspect.isawaitable(res):
                    result = await res
                else:
                    result = res
        else:
            transport = tool_def.transport if tool_def else "local"
            adapter = self.adapters.get(transport, self.adapters["local"])
            config = tool_def.config_jsonb if tool_def else {}
            result = await adapter.execute(context, tool, args, config=config)

        return result
