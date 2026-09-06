import { APIError } from "encore.dev/api";
import { and, eq } from "drizzle-orm";
import { db } from "../../models/db";
import { identityWorkforceMembers } from "../../../shared/db/schema/identity";
import type { TenantContext } from "../../../shared/types/tenant_context";
import {
  OwnerAgentProfile,
  AGENT_PROFILE_SPEC_ID,
  AGENT_PROFILE_SPEC_VERSION,
  ensureAiWorkforceMember,
} from "../../services/ai-member.service";
import {
  getWorkspaceStrategySettings,
  BscPerspective,
} from "./workspace-strategy-settings.service";
import { requireStrategyGovernanceAuthority } from "./strategy-governance-authorization.service";
import {
  createPestelSignal,
  PestelDimension,
  PestelImpact,
  PestelCertainty,
  PestelSignal,
} from "./strategy-analysis.service";
import {
  createTowsOption,
  TowsOption,
  TowsQuadrant,
  getTowsOption,
} from "./tows-option.service";
import {
  createInitiativeInWorkspace,
  Initiative,
} from "../../services/initiative.service";

export interface StrategyCopilotCapability {
  capabilityKey: string;
  name: string;
  description: string;
  domain: string;
  autonomyDefault: "AUTO" | "NEEDS_APPROVAL" | "FOUNDER_ONLY";
}

export interface StrategyCopilotProfileManifest {
  profile: OwnerAgentProfile;
  name: string;
  specId: string;
  specVersion: string;
  enabledInSettings: boolean;
  workforceMemberId: string | null;
  status: "ACTIVE" | "NOT_CONFIGURED" | "DISABLED";
  capabilities: StrategyCopilotCapability[];
}

const STRATEGY_COPILOT_PROFILES = [
  "research_intelligence",
  "strategy",
] as const;

type StrategyCopilotProfile = (typeof STRATEGY_COPILOT_PROFILES)[number];

const PROFILE_NAME_MAP: Record<StrategyCopilotProfile, string> = {
  research_intelligence: "Research & Intelligence Copilot",
  strategy: "Strategic Analysis & Planning Copilot",
};

const PROFILE_CAPABILITIES: Record<StrategyCopilotProfile, StrategyCopilotCapability[]> = {
  research_intelligence: [
    {
      capabilityKey: "evidence.ingestion",
      name: "Thu thập bằng chứng",
      description: "Thu thập và chuẩn hóa dữ liệu bằng chứng thị trường",
      domain: "research_intelligence",
      autonomyDefault: "AUTO",
    },
    {
      capabilityKey: "source.discovery",
      name: "Khám phá nguồn",
      description: "Khám phá nguồn tài liệu và đối thủ cạnh tranh",
      domain: "research_intelligence",
      autonomyDefault: "AUTO",
    },
    {
      capabilityKey: "pestel.extraction",
      name: "Trích xuất PESTEL",
      description: "Trích xuất và lập danh mục tín hiệu vĩ mô PESTEL",
      domain: "research_intelligence",
      autonomyDefault: "NEEDS_APPROVAL",
    },
    {
      capabilityKey: "resource.drafting",
      name: "Đánh giá nguồn lực",
      description: "Đánh giá sơ bộ nguồn lực nội bộ và năng lực cạnh tranh",
      domain: "research_intelligence",
      autonomyDefault: "NEEDS_APPROVAL",
    },
  ],
  strategy: [
    {
      capabilityKey: "swot.synthesis",
      name: "Tổng hợp SWOT",
      description: "Tổng hợp phân tích điểm mạnh, điểm yếu, cơ hội, thách thức",
      domain: "strategy",
      autonomyDefault: "NEEDS_APPROVAL",
    },
    {
      capabilityKey: "tows.draft",
      name: "Dự thảo TOWS",
      description: "Đề xuất các phương án chiến lược kết hợp ma trận TOWS",
      domain: "strategy",
      autonomyDefault: "NEEDS_APPROVAL",
    },
    {
      capabilityKey: "strategy.ranking",
      name: "Giải thích xếp hạng",
      description: "Phân tích điểm số và giải thích cơ sở xếp hạng chiến lược",
      domain: "strategy",
      autonomyDefault: "AUTO",
    },
    {
      capabilityKey: "strategy.initiative",
      name: "Đề xuất sáng kiến",
      description: "Đề xuất các sáng kiến thực thi gắn liền với mục tiêu chiến lược",
      domain: "strategy",
      autonomyDefault: "NEEDS_APPROVAL",
    },
  ],
};

/**
 * Returns capability manifests for strategy copilot profiles in the workspace.
 * Requires read access to the workspace.
 */
export async function getStrategyAgentManifestsService(
  ctx: TenantContext
): Promise<StrategyCopilotProfileManifest[]> {
  const wsIdStr = String(ctx.workspaceId);
  const wsIdBig = BigInt(ctx.workspaceId);
  const settings = await getWorkspaceStrategySettings(wsIdStr);

  const existingAiMembers = await db
    .select()
    .from(identityWorkforceMembers)
    .where(
      and(
        eq(identityWorkforceMembers.workspaceId, wsIdBig),
        eq(identityWorkforceMembers.memberType, "AI_AGENT")
      )
    );

  const memberBySpecId = new Map<string, typeof identityWorkforceMembers.$inferSelect>();
  for (const m of existingAiMembers) {
    if (m.agentSpecId) {
      memberBySpecId.set(m.agentSpecId, m);
    }
  }

  const manifests: StrategyCopilotProfileManifest[] = [];

  for (const profile of STRATEGY_COPILOT_PROFILES) {
    const specId = AGENT_PROFILE_SPEC_ID[profile];
    const specVersion = AGENT_PROFILE_SPEC_VERSION[profile];
    const isAllowedInSettings = settings.allowedAgentProfiles.includes(profile);
    const existingMember = memberBySpecId.get(specId);

    let status: StrategyCopilotProfileManifest["status"];
    if (!isAllowedInSettings) {
      status = "DISABLED";
    } else if (existingMember) {
      status = "ACTIVE";
    } else {
      // Allowed in settings but not yet explicitly configured as a workforce member
      status = "NOT_CONFIGURED";
    }

    manifests.push({
      profile,
      name: PROFILE_NAME_MAP[profile],
      specId,
      specVersion,
      enabledInSettings: isAllowedInSettings,
      workforceMemberId: existingMember ? existingMember.id.toString() : null,
      status,
      capabilities: PROFILE_CAPABILITIES[profile],
    });
  }

  return manifests;
}

export interface ConfigureStrategyAgentParams {
  profile: OwnerAgentProfile;
  activateMember?: boolean;
}

/**
 * Configures an agent profile for the workspace.
 * Requires 'strategy.agent.configure' authority.
 * Only permitted profiles in workspace settings can be activated.
 * Does NOT silently create a workforce member unless explicitly requested.
 */
export async function configureStrategyAgentService(
  ctx: TenantContext,
  params: ConfigureStrategyAgentParams
): Promise<StrategyCopilotProfileManifest> {
  const wsIdStr = String(ctx.workspaceId);
  await requireStrategyGovernanceAuthority(ctx, "strategy.agent.configure", {
    workspaceId: wsIdStr,
  });

  if (!(STRATEGY_COPILOT_PROFILES as readonly string[]).includes(params.profile)) {
    throw APIError.invalidArgument(
      `Invalid strategy copilot profile: '${params.profile}'. Allowed: ${STRATEGY_COPILOT_PROFILES.join(", ")}`
    );
  }

  const typedProfile = params.profile as "research_intelligence" | "strategy";
  const settings = await getWorkspaceStrategySettings(wsIdStr);

  if (!settings.allowedAgentProfiles.includes(typedProfile)) {
    throw APIError.failedPrecondition(
      `Profile '${typedProfile}' is not permitted in workspace strategy settings. Enable it in workspace strategy settings first.`
    );
  }

  let workforceMemberId: string | null = null;
  if (params.activateMember) {
    workforceMemberId = await db.transaction(async (tx) => {
      return ensureAiWorkforceMember(tx, wsIdStr, typedProfile);
    });
  } else {
    // Check if one already exists
    const [existing] = await db
      .select({ id: identityWorkforceMembers.id })
      .from(identityWorkforceMembers)
      .where(
        and(
          eq(identityWorkforceMembers.workspaceId, BigInt(wsIdStr)),
          eq(identityWorkforceMembers.memberType, "AI_AGENT"),
          eq(identityWorkforceMembers.agentSpecId, AGENT_PROFILE_SPEC_ID[typedProfile])
        )
      )
      .limit(1);
    if (existing) {
      workforceMemberId = existing.id.toString();
    }
  }

  return {
    profile: typedProfile,
    name: PROFILE_NAME_MAP[typedProfile],
    specId: AGENT_PROFILE_SPEC_ID[typedProfile],
    specVersion: AGENT_PROFILE_SPEC_VERSION[typedProfile],
    enabledInSettings: true,
    workforceMemberId,
    status: workforceMemberId ? "ACTIVE" : "NOT_CONFIGURED",
    capabilities: PROFILE_CAPABILITIES[typedProfile],
  };
}

// --------------------------------------------------------------------------
// PROPOSAL APIS (DRAFT / PROPOSED only with evidence provenance)
// --------------------------------------------------------------------------

export interface CandidatePestelSignal {
  dimension: PestelDimension;
  statement: string;
  impact?: PestelImpact;
  certainty?: PestelCertainty;
  evidenceRefs?: string[];
  bscPerspectives?: BscPerspective[];
}

export interface ProposePestelSignalsParams {
  strategicObjectiveId: string;
  signals: CandidatePestelSignal[];
}

export interface ProposePestelSignalsResult {
  status: "DRAFT";
  strategicObjectiveId: string;
  proposedSignals: PestelSignal[];
}

export async function proposePestelSignalsService(
  ctx: TenantContext,
  params: ProposePestelSignalsParams
): Promise<ProposePestelSignalsResult> {
  const wsIdStr = String(ctx.workspaceId);
  const settings = await getWorkspaceStrategySettings(wsIdStr);

  if (!settings.allowedAgentProfiles.includes("research_intelligence")) {
    throw APIError.failedPrecondition(
      "Agent profile 'research_intelligence' is disabled in workspace settings"
    );
  }

  if (!params.signals || params.signals.length === 0) {
    throw APIError.invalidArgument("signals array cannot be empty");
  }

  const createdSignals: PestelSignal[] = [];
  for (const s of params.signals) {
    const created = await createPestelSignal(ctx, {
      strategicObjectiveId: params.strategicObjectiveId,
      dimension: s.dimension,
      statement: s.statement,
      impact: s.impact ?? "POSITIVE",
      certainty: s.certainty ?? "MEDIUM",
      evidenceRefs: s.evidenceRefs,
      bscPerspectives: s.bscPerspectives,
    });
    createdSignals.push(created);
  }

  return {
    status: "DRAFT",
    strategicObjectiveId: params.strategicObjectiveId,
    proposedSignals: createdSignals,
  };
}

export interface CandidateTowsOption {
  quadrant: TowsQuadrant;
  title: string;
  description?: string;
  internalFactorRefs?: string[];
  externalFactorRefs?: string[];
  evidenceRefs?: string[];
}

export interface ProposeTowsOptionsParams {
  strategicObjectiveId: string;
  options: CandidateTowsOption[];
}

export interface ProposeTowsOptionsResult {
  status: "DRAFT";
  strategicObjectiveId: string;
  proposedOptions: TowsOption[];
}

export async function proposeTowsOptionsService(
  ctx: TenantContext,
  params: ProposeTowsOptionsParams
): Promise<ProposeTowsOptionsResult> {
  const wsIdStr = String(ctx.workspaceId);
  const settings = await getWorkspaceStrategySettings(wsIdStr);

  if (!settings.allowedAgentProfiles.includes("strategy")) {
    throw APIError.failedPrecondition(
      "Agent profile 'strategy' is disabled in workspace settings"
    );
  }

  if (!params.options || params.options.length === 0) {
    throw APIError.invalidArgument("options array cannot be empty");
  }

  const createdOptions: TowsOption[] = [];
  for (const opt of params.options) {
    const created = await createTowsOption({
      workspaceId: wsIdStr,
      strategicObjectiveId: params.strategicObjectiveId,
      quadrant: opt.quadrant,
      title: opt.title,
      rationale: opt.description,
      swotItemIds: opt.internalFactorRefs || opt.externalFactorRefs,
      aiProvenance: opt.evidenceRefs ? { evidenceRefs: opt.evidenceRefs } : undefined,
    });
    createdOptions.push(created);
  }

  return {
    status: "DRAFT",
    strategicObjectiveId: params.strategicObjectiveId,
    proposedOptions: createdOptions,
  };
}

export interface CandidateInitiative {
  title: string;
  description?: string;
  intendedOutcome?: string;
  startDate?: string;
  targetDate?: string;
  keyResultIds?: string[];
}

export interface ProposeInitiativesParams {
  strategicObjectiveId?: string;
  towsOptionId?: string;
  initiatives: CandidateInitiative[];
}

export interface ProposeInitiativesResult {
  status: "PROPOSED";
  proposedInitiatives: Initiative[];
}

export async function proposeInitiativesService(
  ctx: TenantContext,
  params: ProposeInitiativesParams
): Promise<ProposeInitiativesResult> {
  const wsIdStr = String(ctx.workspaceId);
  const settings = await getWorkspaceStrategySettings(wsIdStr);

  if (!settings.allowedAgentProfiles.includes("strategy")) {
    throw APIError.failedPrecondition(
      "Agent profile 'strategy' is disabled in workspace settings"
    );
  }

  if (params.towsOptionId) {
    const tows = await getTowsOption(params.towsOptionId, wsIdStr);
    if (tows.status !== "SELECTED") {
      throw APIError.failedPrecondition(
        `Source TOWS option ${params.towsOptionId} must be SELECTED before proposing initiatives`
      );
    }
  }

  if (!params.initiatives || params.initiatives.length === 0) {
    throw APIError.invalidArgument("initiatives array cannot be empty");
  }

  const proposed: Initiative[] = [];
  for (const init of params.initiatives) {
    const created = await createInitiativeInWorkspace(
      ctx,
      {
        workspaceId: wsIdStr,
        strategicObjectiveId: params.strategicObjectiveId,
        sourceTowsOptionId: params.towsOptionId,
        title: init.title,
        description: init.description,
        intendedOutcome: init.intendedOutcome,
        startDate: init.startDate,
        targetDate: init.targetDate,
        keyResultIds: init.keyResultIds,
      }
    );
    proposed.push(created);
  }

  return {
    status: "PROPOSED",
    proposedInitiatives: proposed,
  };
}
