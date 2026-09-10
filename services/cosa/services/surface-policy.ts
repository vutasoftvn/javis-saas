// Static released-surface policy cho WorkspaceCapabilityManifest.
//
// Đây là "sự thật tĩnh" về surface nào đã phát hành ở mức nào. Resolver
// (`workspace-capability-manifest.service.ts`) overlay entitlement (module
// configs), connector status và operator override lên trên đây để ra
// `surface_status` per-workspace. Xem spec 2026-09-09-founder-trial-domain-agent
// -mvp §7.1 / §8 module roadmap.
//
// Đổi policy này = đổi code + bump `SURFACE_POLICY_VERSION` + redeploy (theo
// ADR-AGENT-REG-001, registration API runtime là post-launch).

import type { OptionalModuleKey } from "./workspace-settings.service";

export type SurfaceStatus =
  | "AVAILABLE"
  | "PILOT"
  | "PLANNED"
  | "CONFIGURATION_REQUIRED"
  | "UNAVAILABLE";

export interface SurfacePolicyEntry {
  /** Khoá ổn định, không đổi qua các release. */
  readonly surfaceKey: string;
  readonly moduleKey: string;
  readonly featureKey: string;
  readonly defaultStatus: SurfaceStatus;
  /** Capability id trong shared/contracts/mvp-surface.json. */
  readonly requiredCapabilities: readonly string[];
  /** Connector key phải ở trạng thái enabled (vd "cas"). */
  readonly requiredConnectorKeys: readonly string[];
  /**
   * Nếu set, surface bị gate bởi cosa.workspace_module_configs
   * (finance/legal/crm). Module tắt → UNAVAILABLE + reason "module_disabled".
   */
  readonly optionalModuleKey?: OptionalModuleKey;
  /** Capability id chính để frontend bind CTA live. null khi PLANNED. */
  readonly contractEndpoint: string | null;
  readonly releaseNote: string | null;
}

export const SURFACE_POLICY_VERSION = "2026-09-10.4-startup-core";

export const FOUNDER_TRIAL_SURFACE_POLICY: readonly SurfacePolicyEntry[] = [
  // ── Startup Core: Project Operating Loop ──
  {
    surfaceKey: "project.operating_loop",
    moduleKey: "operations",
    featureKey: "project_operating_loop",
    defaultStatus: "AVAILABLE",
    requiredCapabilities: [
      "project.loop.read",
      "project.okr.write",
      "project.cycle.write",
      "project.week.write",
      "project.commitment.write",
      "project.task.write",
    ],
    requiredConnectorKeys: [],
    contractEndpoint: "project.loop.read",
    releaseNote: "Vòng lặp vận hành Project: OKRs, chu kỳ 1-12 tuần, weekly plan, cam kết và tasks.",
  },
  // ── CRM (gate bởi module 'crm') ──
  {
    surfaceKey: "crm.interview",
    moduleKey: "commercial",
    featureKey: "interview",
    defaultStatus: "AVAILABLE",
    requiredCapabilities: [
      "commercial.interview.create",
      "commercial.interview.submit_evidence",
    ],
    requiredConnectorKeys: [],
    optionalModuleKey: "crm",
    contractEndpoint: "commercial.interview.create",
    releaseNote: "Interview project-scoped; submit-as-evidence là hành động tường minh của founder.",
  },
  {
    surfaceKey: "crm.contact_lead",
    moduleKey: "commercial",
    featureKey: "contact_lead",
    defaultStatus: "AVAILABLE",
    requiredCapabilities: ["commercial.contact.create", "commercial.lead.create"],
    requiredConnectorKeys: [],
    optionalModuleKey: "crm",
    contractEndpoint: "commercial.contact.create",
    releaseNote: "Contact/lead liên kết project qua typed link (contact_projects / project_id).",
  },
  // ── Marketing (PILOT — chưa có paid spend / outbound) ──
  {
    surfaceKey: "marketing.experiments",
    moduleKey: "commercial",
    featureKey: "marketing_experiments",
    defaultStatus: "PILOT",
    requiredCapabilities: [
      "marketing.experiment.create",
      "marketing.experiment.list",
      "marketing.campaign.create",
      "marketing.campaign.list",
    ],
    requiredConnectorKeys: [],
    contractEndpoint: "marketing.experiment.create",
    releaseNote: "Experiment + campaign draft project-scoped. Không autonomous paid spend hoặc outbound send.",
  },
  // ── Finance ──
  {
    surfaceKey: "finance.project_budget",
    moduleKey: "finance",
    featureKey: "project_budget_coverage",
    defaultStatus: "AVAILABLE",
    requiredCapabilities: ["finance.budget_summary.read"],
    requiredConnectorKeys: [],
    optionalModuleKey: "finance",
    contractEndpoint: "finance.budget_summary.read",
    releaseNote: "Project budget coverage từ budget-summary. Cần budget envelope, không cần connector.",
  },
  {
    surfaceKey: "finance.cash_liquidity",
    moduleKey: "finance",
    featureKey: "workspace_liquidity",
    defaultStatus: "AVAILABLE",
    requiredCapabilities: ["finance.snapshot.latest"],
    requiredConnectorKeys: ["cas"],
    optionalModuleKey: "finance",
    contractEndpoint: "finance.snapshot.latest",
    releaseNote: "Workspace liquidity từ CAS. Không trình bày là 'tiền của project'. Cần kết nối CAS.",
  },
  // ── PLANNED (retained domains only) ──
  ...planned([
    ["knowledge.vault_rag", "knowledge", "vault_rag", "Vault/RAG retrieval — cần retrieval authorization."],
    ["agents.domain_orchestration", "agents", "domain_orchestration", "Project Orchestrator + domain agents."],
  ]),
];

function planned(
  rows: ReadonlyArray<readonly [string, string, string, string]>
): SurfacePolicyEntry[] {
  return rows.map(([surfaceKey, moduleKey, featureKey, releaseNote]) => ({
    surfaceKey,
    moduleKey,
    featureKey,
    defaultStatus: "PLANNED" as const,
    requiredCapabilities: [],
    requiredConnectorKeys: [],
    contractEndpoint: null,
    releaseNote,
  }));
}

// Fail-closed lúc khởi động: policy tĩnh phải khớp contract MVP đã sinh
// (mọi surface live tham chiếu capability enabled; PLANNED có contractEndpoint
// null). Import động để tránh phụ thuộc vòng khi test import riêng validator.
import {
  loadEnabledMvpCapabilityIds,
  validateSurfacePolicyAgainstMvpContract,
} from "./mvp-contract-policy";

validateSurfacePolicyAgainstMvpContract(
  FOUNDER_TRIAL_SURFACE_POLICY,
  loadEnabledMvpCapabilityIds()
);
