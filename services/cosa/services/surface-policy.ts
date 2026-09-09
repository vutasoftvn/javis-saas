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

export const SURFACE_POLICY_VERSION = "2026-09-10.1";

export const FOUNDER_TRIAL_SURFACE_POLICY: readonly SurfacePolicyEntry[] = [
  // ── R1 Founder Trial: AVAILABLE ──
  {
    surfaceKey: "founder_trial.board",
    moduleKey: "strategy",
    featureKey: "founder_trial_board",
    defaultStatus: "AVAILABLE",
    requiredCapabilities: ["strategy.founder_trial.board.read"],
    requiredConnectorKeys: [],
    contractEndpoint: "strategy.founder_trial.board.read",
    releaseNote: "Vòng lặp vận hành có dữ liệu thật: cycle → assumptions → experiments → evidence → decision.",
  },
  {
    surfaceKey: "founder_trial.operating_cycle",
    moduleKey: "strategy",
    featureKey: "operating_cycle",
    defaultStatus: "AVAILABLE",
    requiredCapabilities: ["strategy.operating_cycle.resize"],
    requiredConnectorKeys: [],
    contractEndpoint: "strategy.operating_cycle.resize",
    releaseNote: "Operating Cycle cấu hình được 1–12 tuần; 12 chỉ là template gợi ý.",
  },
  {
    surfaceKey: "founder_trial.assumptions",
    moduleKey: "strategy",
    featureKey: "assumptions",
    defaultStatus: "AVAILABLE",
    requiredCapabilities: ["strategy.assumptions.ranked", "strategy.assumption.create"],
    requiredConnectorKeys: [],
    contractEndpoint: "strategy.assumptions.ranked",
    releaseNote: "Giả thuyết xếp hạng theo importance × uncertainty.",
  },
  {
    surfaceKey: "founder_trial.experiments",
    moduleKey: "strategy",
    featureKey: "experiments",
    defaultStatus: "AVAILABLE",
    requiredCapabilities: ["strategy.founder_trial.experiment.create"],
    requiredConnectorKeys: [],
    contractEndpoint: "strategy.founder_trial.experiment.create",
    releaseNote: "Test contract: bắt buộc chọn assumption + method + success criteria.",
  },
  {
    surfaceKey: "founder_trial.evidence",
    moduleKey: "strategy",
    featureKey: "evidence",
    defaultStatus: "AVAILABLE",
    requiredCapabilities: ["strategy.evidence.review"],
    requiredConnectorKeys: [],
    contractEndpoint: "strategy.evidence.review",
    releaseNote: "Evidence candidate/approved/rejected; evidence chưa liên kết hypothesis nằm ngoài kết luận.",
  },
  {
    surfaceKey: "founder_trial.founder_brief",
    moduleKey: "strategy",
    featureKey: "founder_brief",
    defaultStatus: "AVAILABLE",
    requiredCapabilities: ["strategy.founder_brief.read", "strategy.decision.create"],
    requiredConnectorKeys: [],
    contractEndpoint: "strategy.founder_brief.read",
    releaseNote: "Tổng hợp 5 trục readiness. R1 không có agent recommendation.",
  },
  // ── R1 CRM (gate bởi module 'crm') ──
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
  // ── R1 Marketing (PILOT — chưa có paid spend / outbound) ──
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
  // ── R1 Finance ──
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
    // AVAILABLE là trạng thái "đã phát hành"; resolver tự hạ xuống
    // CONFIGURATION_REQUIRED khi connector "cas" chưa enabled.
    defaultStatus: "AVAILABLE",
    requiredCapabilities: ["finance.snapshot.latest"],
    requiredConnectorKeys: ["cas"],
    optionalModuleKey: "finance",
    contractEndpoint: "finance.snapshot.latest",
    releaseNote: "Workspace liquidity từ CAS. Không trình bày là 'tiền của project'. Cần kết nối CAS.",
  },
  // ── PLANNED (post-R1) ──
  ...planned([
    ["strategy.vision_mission_value", "strategy", "vision_mission_value", "Vision/Mission/Value — R1.1 sau khi founder trial cho thấy vòng evidence được hiểu."],
    ["strategy.pestel", "strategy", "pestel", "PESTEL — R1.2, cần decision consumer + version/review policy."],
    ["strategy.swot_tows", "strategy", "swot_tows", "SWOT/TOWS — R1.2."],
    ["strategy.bsc", "strategy", "bsc", "Balanced Scorecard — R1.2."],
    ["knowledge.vault_rag", "knowledge", "vault_rag", "Vault/RAG retrieval — R3, cần retrieval authorization."],
    ["automation.workflow_builder", "automation", "workflow_builder", "Free workflow builder — R3, cần workflow governance."],
    ["experience.voice_agent", "experience", "voice_agent", "Voice agent — R3 enterprise."],
    ["agents.domain_orchestration", "agents", "domain_orchestration", "Project Orchestrator + domain agents — sau khi persistent workforce đạt Task 9."],
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
