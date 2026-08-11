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
    OkrCycle, OkrObjective, KeyResult, OkrLink, Project, Initiative, InitiativeKeyResultLink,
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
    EmailApproval
)
from app.modules.platform.models import WorkspaceDomain, AuditLog, FeatureFlag

from app.modules.marketing.models import (
    MarketingContext, MarketingObjective, MarketingCampaign, CampaignAsset,
    MarketingMetric, MetricSnapshot, MarketingExperiment, MarketingLearning,
    SkillRegistry, SkillExecution, PendingApproval,
    MarketingLoop, MarketingDecision, MarketingRecommendation
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

# Note: this file must be updated whenever a new model is added
