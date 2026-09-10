// COSA Automation MVP — read-only curated blueprint registry surface (Task 9).
// docs/superpowers/plans/2026-09-10-cosa-automation-mvp.md
//
// Exposes the static registry metadata to the guided configuration form.
// Workspace policy can enable only a listed blueprint; it can never alter a
// blueprint's capability set, approval contract, evidence contract, runtime
// requirement or turn a draft blueprint into external delivery.

import { APIError } from "encore.dev/api";
import { mvpItem, mvpList, MvpSuccess } from "../../shared/contracts/mvp-response";
import {
  CURATED_BLUEPRINTS,
  CURATED_BLUEPRINT_KEYS,
  getCuratedBlueprint,
  type CuratedBlueprint,
} from "./automation-blueprint-registry";

const SOURCE_REF = { kind: "company_db" as const, ref: "operations.automation_blueprint_registry" };

// Fields a workspace may never submit through configuration — they are fixed by
// the curated blueprint.
const LOCKED_FIELDS = [
  "capabilityIds",
  "capability_ids",
  "capabilities",
  "autonomyClass",
  "autonomy_class",
  "approvalRequired",
  "approval_required",
  "approvalContract",
  "evidenceContract",
  "evidence_contract",
  "runtimeRequirement",
  "runtime_requirement",
  "pinnedAgentSpecId",
  "pinned_agent_spec_id",
  "deliversExternally",
  "delivers_externally",
  "endpoint",
  "url",
  "model",
  "modelProvider",
  "prompt",
];

export interface BlueprintRegistryView {
  readonly key: string;
  readonly version: string;
  readonly domain: string;
  readonly title: string;
  readonly purpose: string;
  readonly configFields: CuratedBlueprint["configFields"];
  readonly triggerKinds: CuratedBlueprint["triggerKinds"];
  readonly autonomyClass: string;
  readonly approvalRequired: boolean;
  readonly runtimeRequirement: string;
  readonly capabilityIds: readonly string[];
  readonly evidenceRequires: readonly string[];
  readonly deliversExternally: false;
}

function toView(b: CuratedBlueprint): BlueprintRegistryView {
  return {
    key: b.key,
    version: b.version,
    domain: b.domain,
    title: b.title,
    purpose: b.purpose,
    configFields: b.configFields,
    triggerKinds: b.triggerKinds,
    autonomyClass: b.autonomyClass,
    approvalRequired: b.approvalRequired,
    runtimeRequirement: b.runtimeRequirement,
    capabilityIds: b.capabilityIds,
    evidenceRequires: b.evidenceContract.requires,
    deliversExternally: b.deliversExternally,
  };
}

export function listCuratedBlueprints(): MvpSuccess<readonly BlueprintRegistryView[]> {
  return mvpList(
    CURATED_BLUEPRINT_KEYS.map((k) => toView(CURATED_BLUEPRINTS[k])),
    [SOURCE_REF]
  );
}

export function getCuratedBlueprintView(key: string): MvpSuccess<BlueprintRegistryView> {
  const b = getCuratedBlueprint(key);
  if (!b) throw APIError.notFound(`unknown automation blueprint '${key}'`);
  return mvpItem(toView(b), [SOURCE_REF]);
}

/** Throws if a submitted configuration object tries to override anything the
 *  curated blueprint owns. Called by configureAutomationDefinition. */
export function assertBlueprintConfigWithinBounds(
  key: string,
  submitted: Record<string, unknown>
): void {
  if (!getCuratedBlueprint(key)) {
    throw APIError.invalidArgument(`unknown automation blueprint '${key}'`);
  }
  for (const field of LOCKED_FIELDS) {
    if (Object.prototype.hasOwnProperty.call(submitted, field)) {
      throw APIError.invalidArgument(
        `configuration may not set '${field}' — it is fixed by the curated blueprint`
      );
    }
  }
}
