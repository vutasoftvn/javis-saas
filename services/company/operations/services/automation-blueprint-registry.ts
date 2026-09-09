// COSA Automation MVP — curated blueprint registry (static source of truth).
//
// docs/superpowers/specs/2026-09-10-cosa-automation-mvp-design.md §7.1.
// System-published, read-first blueprints. A workspace can only configure a
// listed blueprint through a guided typed form; it can never author a raw
// prompt, pick a model provider, widen the capability set, add a connector
// secret or turn a draft blueprint into external delivery. Changing this
// registry = code change + redeploy (ADR-AGENT-REG-001: runtime registration
// is post-launch).
//
// The Agent Platform side (packages/agent/workflows/automation_blueprints.py)
// carries the executable WorkflowSpec for each key; a contract test keys the two
// halves together (Task 9).

export type BlueprintFieldType = "string" | "text" | "number" | "boolean" | "enum" | "date";

export interface BlueprintFieldSpec {
  readonly key: string;
  readonly label: string;
  readonly type: BlueprintFieldType;
  readonly required: boolean;
  readonly enumValues?: readonly string[];
  readonly help?: string;
}

export type AutonomyClass = "read_only" | "draft_only" | "gated_effect";
export type TriggerKind = "manual" | "schedule" | "business_event";
export type RuntimeRequirement = "any" | "local_only";

export interface CuratedBlueprint {
  readonly key: string;
  readonly version: string;
  readonly domain: string;
  readonly title: string;
  readonly purpose: string;
  readonly configFields: readonly BlueprintFieldSpec[];
  /** Read / draft / evidence capabilities only — never an external send or an
   *  authoritative business mutation. */
  readonly capabilityIds: readonly string[];
  readonly autonomyClass: AutonomyClass;
  readonly evidenceContract: { readonly requires: readonly string[] };
  readonly triggerKinds: readonly TriggerKind[];
  readonly approvalRequired: boolean;
  readonly runtimeRequirement: RuntimeRequirement;
  readonly pinnedAgentSpecId: string;
  /** Hard MVP invariant. Never true for any curated blueprint. */
  readonly deliversExternally: false;
}

const OPERATIONS_SPEC = "cosa.agents.operations";

export const CURATED_BLUEPRINTS: Readonly<Record<string, CuratedBlueprint>> = Object.freeze({
  "operating.weekly-review": {
    key: "operating.weekly-review",
    version: "1.0.0",
    domain: "operating",
    title: "Weekly review digest",
    purpose:
      "KPI / rủi ro / quyết định trong tuần kèm evidence reference. Không mutation.",
    configFields: [
      { key: "projectId", label: "Project", type: "string", required: true, help: "Project được tổng hợp." },
      { key: "lookbackWeeks", label: "Số tuần nhìn lại", type: "number", required: false },
    ],
    capabilityIds: ["operations.task.read", "strategy.founder_trial.board.read"],
    autonomyClass: "read_only",
    evidenceContract: { requires: ["digest_markdown", "source_refs"] },
    triggerKinds: ["manual", "schedule"],
    approvalRequired: false,
    runtimeRequirement: "any",
    pinnedAgentSpecId: OPERATIONS_SPEC,
    deliversExternally: false,
  },
  "operations.task-follow-up": {
    key: "operations.task-follow-up",
    version: "1.0.0",
    domain: "operations",
    title: "Delayed / blocked work follow-up",
    purpose:
      "Phân tích công việc trễ hạn hoặc bị chặn và đề xuất follow-up. Không gửi ra ngoài.",
    configFields: [
      { key: "projectId", label: "Project", type: "string", required: true },
      { key: "staleAfterDays", label: "Trễ sau (ngày)", type: "number", required: false },
    ],
    capabilityIds: ["operations.task.read"],
    autonomyClass: "read_only",
    evidenceContract: { requires: ["follow_up_recommendations", "source_refs"] },
    triggerKinds: ["manual", "schedule", "business_event"],
    approvalRequired: false,
    runtimeRequirement: "any",
    pinnedAgentSpecId: OPERATIONS_SPEC,
    deliversExternally: false,
  },
  "commercial.outbound-draft": {
    key: "commercial.outbound-draft",
    version: "1.0.0",
    domain: "commercial",
    title: "Evidence-backed outbound draft",
    purpose:
      "Soạn nháp outbound dựa trên evidence. KHÔNG gửi — chỉ tạo draft artifact.",
    configFields: [
      { key: "audienceRef", label: "Audience reference", type: "string", required: true },
      { key: "tone", label: "Tông giọng", type: "enum", required: false, enumValues: ["neutral", "warm", "formal"] },
    ],
    capabilityIds: ["operations.task.read"],
    autonomyClass: "draft_only",
    evidenceContract: { requires: ["draft_artifact", "source_refs"] },
    triggerKinds: ["manual"],
    approvalRequired: true,
    runtimeRequirement: "any",
    pinnedAgentSpecId: OPERATIONS_SPEC,
    deliversExternally: false,
  },
  "strategy.initiative-health": {
    key: "strategy.initiative-health",
    version: "1.0.0",
    domain: "strategy",
    title: "Initiative / KR health check",
    purpose:
      "Phát hiện lệch hướng Initiative/KR/Task và evidence thiếu. Không mutation chiến lược có thẩm quyền.",
    configFields: [
      { key: "projectId", label: "Project", type: "string", required: true },
    ],
    capabilityIds: ["operations.task.read", "strategy.founder_trial.board.read"],
    autonomyClass: "read_only",
    evidenceContract: { requires: ["deviation_report", "missing_evidence_list", "source_refs"] },
    triggerKinds: ["manual", "schedule"],
    approvalRequired: false,
    runtimeRequirement: "any",
    pinnedAgentSpecId: OPERATIONS_SPEC,
    deliversExternally: false,
  },
});

export const CURATED_BLUEPRINT_KEYS: readonly string[] = Object.freeze(
  Object.keys(CURATED_BLUEPRINTS)
);

export function getCuratedBlueprint(key: string): CuratedBlueprint | undefined {
  return CURATED_BLUEPRINTS[key];
}
