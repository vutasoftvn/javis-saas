"""Workforce Domain — AI Workforce Control Plane

Cung cấp các thành phần quản trị AI Agent:
- Registry & Org Chart
- Runtime Adapters (Claude, Gemini, DeepSeek, Ollama, HTTP)
- Skills Registry (SKILL.md file parser & on-demand injection)
- Governance (Permission Engine, Human Gate, Budget, Cost Ledger)
- Automation (EventBus, Heartbeat, Routines)
- Work Products & Decision Records
"""

from app.workforce.models import (
    AgentDefinition, AgentHierarchy, ToolDefinition, PlatformToolVersion,
    AgentToolPermission, UnifiedPermission, ApprovalRequest, AgentBudget,
    CostLedger, PlatformPromptTemplate, PlatformPromptVersion, PlatformSecretRef,
    AgentRun, AgentStep, AgentHeartbeat, AgentRoutine, RoutineExecution,
    WorkProduct, DecisionRecord
)
from app.workforce.skills.skill_loader import DynamicSkillLoader, PhysicalSkillDocument
from app.workforce.governance.permission_engine import UnifiedPermissionEngine
from app.workforce.governance.approval_service import ApprovalInboxService
from app.workforce.governance.budget_service import BudgetingEngine
from app.workforce.governance.cost_ledger_service import CostLedgerService
from app.workforce.dispatcher.task_dispatcher import AgentTaskDispatcher
from app.workforce.dispatcher.runner import AgentRunnerService

__all__ = [
    "AgentDefinition",
    "AgentHierarchy",
    "ToolDefinition",
    "PlatformToolVersion",
    "AgentToolPermission",
    "UnifiedPermission",
    "ApprovalRequest",
    "AgentBudget",
    "CostLedger",
    "PlatformPromptTemplate",
    "PlatformPromptVersion",
    "PlatformSecretRef",
    "AgentRun",
    "AgentStep",
    "AgentHeartbeat",
    "AgentRoutine",
    "RoutineExecution",
    "WorkProduct",
    "DecisionRecord",
    "DynamicSkillLoader",
    "PhysicalSkillDocument",
    "UnifiedPermissionEngine",
    "ApprovalInboxService",
    "BudgetingEngine",
    "CostLedgerService",
    "AgentTaskDispatcher",
    "AgentRunnerService",
]
