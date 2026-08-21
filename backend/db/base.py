# Import Base
from db.base_class import Base

# Import all domain models here for Alembic to auto-generate migrations

from platform_core.auth.models import User, Workspace, WorkspaceMember
from platform_core.vault.models import (
    Brain, VaultDocument, VaultRevision, Attachment, DocumentChunk, ChunkingJob,
    KnowledgeObject, KnowledgeRelation
)
from workforce.chat.models import ChatSession, ChatMessage, AIRun
from business_core.organization.models import OperatingUnit, Offering
from business_core.tasks.models import Task, TaskDependency, TaskSchedule
from founder_os.tasks.models import Agent
from integrations.workflows.models import TaskWorkflowBinding, WorkflowRun, WorkflowDefinition, WorkflowVersion, WorkflowStep, WorkflowApproval
from business_core.strategy.models import (
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







from integrations.channels.models import (
    MCPConnection, WorkspaceSecret, Chatbot, ChatbotConversation, Plugin, WorkspacePlugin, Outbox,
    EmailApproval, ZaloQrSession
)
from platform_core.core.models import WorkspaceDomain, NavigationGroup, NavigationItem, AuditLog, FeatureFlag, RuntimeHeartbeat
from platform_core.core.deployment_models import Deployment
from platform_core.sync.models import PlatformOutbox, PlatformInbox, LocalEntitlementSnapshot

from business_core.marketing.models import (
    MarketingContext, MarketingObjective, MarketingCampaign, CampaignAsset,
    MarketingMetric, MetricSnapshot, MarketingExperiment, MarketingLearning,
    SkillRegistry, SkillExecution, PendingApproval,
    MarketingLoop, MarketingDecision, MarketingRecommendation
)
from business_core.marketing.models_validation import (
    KnowledgeStatement, Assumption, Evidence, CanvasRevision,
    CustomerInterview, MarketingAttribution
)
from business_core.validation.models import (
    ValidationSession, StructuredClaim, FieldRevision, ValidationAssumption,
    ValidationHypothesis, ValidationExperiment, ValidationEvidence,
    ValidationReview, ValidationDecision, DimensionState, ProjectStageHistory
)
from business_core.marketing.form_models import (
    FormDefinition, FormSubmission, WebEvent
)
from founder_os.outcomes.models import (
    Outcome, OutcomeRun, RunStep, RunEvent, Artifact
)
from integrations.devices.models import (
    Device, DeviceCredential, DeveloperJob, JobLease
)
from platform_core.organization.models import (
    Organization, Department, WorkforceMember, DepartmentMembership, AgentRelation, WorkforceRelation
)
from integrations.realtime.models import RealtimeSession, RealtimeEvent, VoiceUsageRecord
from platform_core.license.models import (
    WorkReview, Blocker, NeedsYouItem, Handoff, RuntimeCheckpoint,
)
from agent_runtime.memory.models import (
    AgentMemoryEngine, AgentMemoryScope, MemoryCandidate, MemoryPromotion,
    MemoryEvaluation, MemorySyncRecord, MemoryHealthSnapshot
)
from business_core.learning.models import Lesson
from business_core.legal.models import LegalChecklistItem, LegalObligation
from business_core.sales.models import SalesLead
from business_core.finance.models import (
    AccountingProfile, AccountingRegulation, AccountingRegulationVersion,
    AccountingBookTemplate, FinancialStatementTemplate, AccountingDocument,
    FinancialTransaction, AccountingRecord, AccountingPeriod, FinanceException,
    FinanceManagementSnapshot,
)

from agent_runtime.sessions.models import AgentRun
from agent_runtime.events.models import AgentEventRecord
from agent_runtime.permissions.models import AgentToolCall, AgentApproval
from agent_runtime.sandbox.models import ExecutionJob, ExecutionStep, SandboxPolicyRecord
from workforce.agents.proposals.models import AgentProposal
from workforce.agents.control_plane.models import (
    AgentGoal, AgentPlan, AgentPlanStep,
)
from workforce.agents.capabilities.models import CapabilityGrant
from core.protected_resources.models import ProtectedResource, ProtectedResourceRevision

from workforce.agents.learning.models import JobOutcome
from workforce.agents.delegation.models import DelegationJob
from workforce.agents.orchestration.runtime_session_models import RuntimeSession
from workforce.agents.orchestration.mission_resume_models import MissionResumeJob



from workforce.automation.models import (
    AutomationCallback,
    AutomationDefinition,
    AutomationRun,
)

from platform_core.policy_funding.models import (
    SourceDocument, SourceSnapshot, PolicyProgram, ProgramRound,
    EligibilityRule, ProjectStageAssessment, TrlAssessment, FundingNeed,
    ProjectProgramMatch, EligibilityEvaluation, MissingRequirement,
    Application, ApplicationSection, FundingAward, ComplianceObligation,
    CostAllocation, AdminPolicyInbox
)

from workforce.skills.models import SkillRegistryItem, SkillTrajectoryCandidate
from platform_core.tech_radar.models import TechnologyRadarItem

from workforce.models import (
    AgentDefinition, ToolDefinition, AgentToolPermission,
    PlatformPromptTemplate, PlatformPromptVersion, PlatformSecretRef,
    LegacyPlatformAgentRun as PlatformAgentRun, AgentStep as PlatformAgentStep,
    FounderDecision, AgentAlias, EscalationRecord,
)
from business.packs.models import (
    BusinessPackModel, BusinessAssetOverrideModel,
    LegalSourceRecord, LegalAnnotationRecord,
)

# Note: this file must be updated whenever a new model is added

from workforce.extensions.models import ExtensionRegistration
