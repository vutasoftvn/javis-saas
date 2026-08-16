# Import Base
from app.db.base_class import Base

# Import all domain models here for Alembic to auto-generate migrations

from app.modules.iam.models import User, Workspace, WorkspaceMember
from app.modules.vault.models import (
    Brain, VaultDocument, VaultRevision, Attachment, DocumentChunk, ChunkingJob,
    KnowledgeObject, KnowledgeRelation
)
from app.modules.chat.models import ChatSession, ChatMessage, AIRun
from app.modules.tasks.models import Task, TaskDependency, TaskSchedule, Agent
from app.modules.workflows.models import TaskWorkflowBinding, WorkflowRun, WorkflowDefinition, WorkflowVersion, WorkflowStep, WorkflowApproval
from app.modules.strategy.models import (
    StrategyCanvas, StrategyRevision, StrategyFoundation, CoreValue, EvidenceItem, ContextPack,
    ContextPackSource, StrategyAnalysis, PestelItem, SwotItem, TowsOption, StrategicDecision,
    Metric, MetricCheckin, BscScorecard, StrategicObjective, StrategicObjectiveLink,
    OkrCycle, OkrObjective, KeyResult, OkrLink, Project, MvpStage, WorkspaceTemplate, WorkspaceTemplateVersion, CapabilityDefinition, WorkspaceAgent,
    StageRevision, StageServiceAssessment, StageAssignment, StrategyAuditEvent, Initiative, InitiativeKeyResultLink,
    TwelveWeekCycle, WeeklyPlan, WeeklyCommitment, PromptTemplate,
    ProjectClassification, MethodologyPlan, CycleContract, CycleStage, Milestone,
    MilestoneEvidence, GateDecision, AnalysisImport, WeeklyReview, CycleReview, CelebrationRecord,
    Portfolio, PortfolioProject, ProjectPestelImpact, PortfolioSynergy, PortfolioDependency, PortfolioOption,
    FounderProfile, PortfolioCycle, CapacityAllocation, FounderAttentionAllocation,
    NextActionCandidate, NextActionRanking,
    PestelSignal, ModelRunAudit
)







from app.modules.integrations.models import (
    MCPConnection, WorkspaceSecret, Chatbot, ChatbotConversation, Plugin, WorkspacePlugin, Outbox,
    EmailApproval, ZaloQrSession
)
from app.modules.platform.models import WorkspaceDomain, NavigationGroup, NavigationItem, AuditLog, FeatureFlag, RuntimeHeartbeat
from app.modules.platform.deployment_models import Deployment

from app.modules.marketing.models import (
    MarketingContext, MarketingObjective, MarketingCampaign, CampaignAsset,
    MarketingMetric, MetricSnapshot, MarketingExperiment, MarketingLearning,
    SkillRegistry, SkillExecution, PendingApproval,
    MarketingLoop, MarketingDecision, MarketingRecommendation
)
from app.modules.marketing.form_models import (
    FormDefinition, FormSubmission, WebEvent
)
from app.modules.outcomes.models import (
    Outcome, OutcomeRun, RunStep, RunEvent, Artifact
)
from app.modules.devices.models import (
    Device, DeviceCredential, DeveloperJob, JobLease
)
from app.modules.organization.models import (
    Organization, Department, WorkforceMember, DepartmentMembership, AgentRelation
)
from app.modules.realtime.models import RealtimeSession, RealtimeEvent, VoiceUsageRecord
from app.modules.company_runtime.models import (
    WorkReview, Blocker, NeedsYouItem, Handoff, RuntimeCheckpoint,
)
from app.modules.agent_memory.models import (
    AgentMemoryEngine, AgentMemoryScope, MemoryCandidate, MemoryPromotion,
    MemoryEvaluation, MemorySyncRecord, MemoryHealthSnapshot
)
from app.modules.learning.models import Lesson
from app.modules.legal.models import LegalChecklistItem, LegalObligation
from app.modules.sales.models import SalesLead
from app.modules.finance.models import (
    AccountingProfile, AccountingRegulation, AccountingRegulationVersion,
    AccountingBookTemplate, FinancialStatementTemplate, AccountingDocument,
    FinancialTransaction, AccountingRecord, AccountingPeriod, FinanceException,
    FinanceManagementSnapshot,
)

from app.agents.governance.models import (
    AgentRun, AgentEventRecord, AgentToolCall, AgentApproval,
)
from app.agents.execution.models import (
    ExecutionJob, ExecutionStep, SandboxPolicyRecord,
)
from app.agents.proposals.models import AgentProposal
from app.agents.control_plane.models import (
    AgentGoal, AgentPlan, AgentPlanStep, AgentMemoryItem,
)
from app.agents.capabilities.models import CapabilityGrant
from app.core.protected_resources.models import ProtectedResource, ProtectedResourceRevision
from app.agents.learning.models import JobOutcome

# Note: this file must be updated whenever a new model is added


