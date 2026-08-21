# Import Base
from app.db.base_class import Base

# Import all domain models here for Alembic to auto-generate migrations

from app.platform.auth.models import User, Workspace, WorkspaceMember
from app.platform.vault.models import (
    Brain, VaultDocument, VaultRevision, Attachment, DocumentChunk, ChunkingJob,
    KnowledgeObject, KnowledgeRelation
)
from app.workforce.chat.models import ChatSession, ChatMessage, AIRun
from core.organization.models import OperatingUnit, Offering
from core.tasks.models import Task, TaskDependency, TaskSchedule
from app.founder_os.tasks.models import Agent
from app.integrations.workflows.models import TaskWorkflowBinding, WorkflowRun, WorkflowDefinition, WorkflowVersion, WorkflowStep, WorkflowApproval
from core.strategy.models import (
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







from app.integrations.channels.models import (
    MCPConnection, WorkspaceSecret, Chatbot, ChatbotConversation, Plugin, WorkspacePlugin, Outbox,
    EmailApproval, ZaloQrSession
)
from app.platform.core.models import WorkspaceDomain, NavigationGroup, NavigationItem, AuditLog, FeatureFlag, RuntimeHeartbeat
from app.platform.core.deployment_models import Deployment
from app.platform.sync.models import PlatformOutbox, PlatformInbox, LocalEntitlementSnapshot

from core.marketing.models import (
    MarketingContext, MarketingObjective, MarketingCampaign, CampaignAsset,
    MarketingMetric, MetricSnapshot, MarketingExperiment, MarketingLearning,
    SkillRegistry, SkillExecution, PendingApproval,
    MarketingLoop, MarketingDecision, MarketingRecommendation
)
from core.marketing.models_validation import (
    KnowledgeStatement, Assumption, Evidence, CanvasRevision,
    CustomerInterview, MarketingAttribution
)
from core.validation.models import (
    ValidationSession, StructuredClaim, FieldRevision, ValidationAssumption,
    ValidationHypothesis, ValidationExperiment, ValidationEvidence,
    ValidationReview, ValidationDecision, DimensionState, ProjectStageHistory
)
from core.marketing.form_models import (
    FormDefinition, FormSubmission, WebEvent
)
from app.founder_os.outcomes.models import (
    Outcome, OutcomeRun, RunStep, RunEvent, Artifact
)
from app.integrations.devices.models import (
    Device, DeviceCredential, DeveloperJob, JobLease
)
from app.platform.organization.models import (
    Organization, Department, WorkforceMember, DepartmentMembership, AgentRelation, WorkforceRelation
)
from app.integrations.realtime.models import RealtimeSession, RealtimeEvent, VoiceUsageRecord
from app.platform.license.models import (
    WorkReview, Blocker, NeedsYouItem, Handoff, RuntimeCheckpoint,
)
from agent_runtime.memory.models import (
    AgentMemoryEngine, AgentMemoryScope, MemoryCandidate, MemoryPromotion,
    MemoryEvaluation, MemorySyncRecord, MemoryHealthSnapshot
)
from core.learning.models import Lesson
from core.legal.models import LegalChecklistItem, LegalObligation
from core.sales.models import SalesLead
from core.finance.models import (
    AccountingProfile, AccountingRegulation, AccountingRegulationVersion,
    AccountingBookTemplate, FinancialStatementTemplate, AccountingDocument,
    FinancialTransaction, AccountingRecord, AccountingPeriod, FinanceException,
    FinanceManagementSnapshot,
)

from agent_runtime.sessions.models import AgentRun
from agent_runtime.events.models import AgentEventRecord
from agent_runtime.permissions.models import AgentToolCall, AgentApproval
from agent_runtime.sandbox.models import ExecutionJob, ExecutionStep, SandboxPolicyRecord
from app.workforce.agents.proposals.models import AgentProposal
from app.workforce.agents.control_plane.models import (
    AgentGoal, AgentPlan, AgentPlanStep,
)
from app.workforce.agents.capabilities.models import CapabilityGrant
from app.core.protected_resources.models import ProtectedResource, ProtectedResourceRevision

from app.workforce.agents.learning.models import JobOutcome
from app.workforce.agents.delegation.models import DelegationJob
from app.workforce.agents.orchestration.runtime_session_models import RuntimeSession


from app.workforce.automation.models import (
    AutomationCallback,
    AutomationDefinition,
    AutomationRun,
)

from app.platform.policy_funding.models import (
    SourceDocument, SourceSnapshot, PolicyProgram, ProgramRound,
    EligibilityRule, ProjectStageAssessment, TrlAssessment, FundingNeed,
    ProjectProgramMatch, EligibilityEvaluation, MissingRequirement,
    Application, ApplicationSection, FundingAward, ComplianceObligation,
    CostAllocation, AdminPolicyInbox
)

from app.workforce.skills.models import SkillRegistryItem, SkillTrajectoryCandidate
from app.platform.tech_radar.models import TechnologyRadarItem

from app.workforce.models import (
    AgentDefinition, ToolDefinition, AgentToolPermission,
    PlatformPromptTemplate, PlatformPromptVersion, PlatformSecretRef,
    LegacyPlatformAgentRun as PlatformAgentRun, AgentStep as PlatformAgentStep,
    FounderDecision, AgentAlias, EscalationRecord,
)
from app.business.packs.models import (
    BusinessPackModel, BusinessAssetOverrideModel,
    LegalSourceRecord, LegalAnnotationRecord,
)

# Note: this file must be updated whenever a new model is added

from app.workforce.extensions.models import ExtensionRegistration
