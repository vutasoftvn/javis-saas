// COSA Automation MVP — Company-owned automation definitions and immutable
// revisions (Task 2). docs/superpowers/plans/2026-09-10-cosa-automation-mvp.md
//
// Business truth lives here (CLAUDE.md rule #1). The LLM runtime never publishes
// an automation, grants a capability or changes a policy. Every write is
// workspace-scoped and fail-closed; publish/suspend need a publisher role.

import { APIError } from "encore.dev/api";
import { createHash } from "node:crypto";
import { and, desc, eq, isNull, isNotNull } from "drizzle-orm";
import { db, schema } from "../models/db";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { mvpItem, mvpList, MvpSuccess } from "../../shared/contracts/mvp-response";
import type { TenantContext } from "../../shared/types/tenant_context";
import {
  CURATED_BLUEPRINTS,
  CURATED_BLUEPRINT_KEYS,
  getCuratedBlueprint,
  type CuratedBlueprint,
  type TriggerKind,
} from "./automation-blueprint-registry";

const { automationDefinitions, automationRevisions } = schema;

const PUBLISHER_ROLES = new Set(["founder", "co-founder", "admin"]);
const SOURCE_REF = { kind: "company_db" as const, ref: "operating.automation_definitions" };

export type AutomationLifecycleState = "DRAFT" | "PUBLISHED" | "SUSPENDED" | "RETIRED";

export interface AutomationTriggerContract {
  readonly kind: TriggerKind;
  /** cron expression when kind === "schedule" */
  readonly schedule?: string;
  /** business event type when kind === "business_event" */
  readonly eventType?: string;
}

export interface AutomationRevisionView {
  readonly id: string;
  readonly revisionNo: number;
  readonly revisionHash: string;
  readonly configuration: Record<string, unknown>;
  readonly triggerContract: AutomationTriggerContract;
  readonly capabilityIds: readonly string[];
  readonly autonomyClass: string;
  readonly approvalRequired: boolean;
  readonly published: boolean;
  readonly publishedAt: string | null;
  readonly createdAt: string;
}

export interface AutomationDefinitionView {
  readonly id: string | null;
  readonly workspaceId: string;
  readonly automationKey: string;
  readonly title: string;
  readonly purpose: string;
  readonly domain: string;
  readonly lifecycleState: AutomationLifecycleState;
  readonly configured: boolean;
  readonly configFields: CuratedBlueprint["configFields"];
  readonly currentRevision: AutomationRevisionView | null;
  readonly draftRevision: AutomationRevisionView | null;
}

export interface ListAutomationDefinitionsParams {
  workspaceId: string;
  authorization?: string;
}

export interface GetAutomationDefinitionParams {
  workspaceId: string;
  definitionId: string;
  authorization?: string;
}

export interface ConfigureAutomationDefinitionParams {
  workspaceId: string;
  automationKey: string;
  configuration: Record<string, unknown>;
  triggerContract: AutomationTriggerContract;
  authorization?: string;
}

export interface PublishAutomationRevisionParams {
  workspaceId: string;
  definitionId: string;
  authorization?: string;
}

export interface SuspendAutomationDefinitionParams {
  workspaceId: string;
  definitionId: string;
  authorization?: string;
}

// --- helpers --------------------------------------------------------------

function requirePublisher(ctx: TenantContext): void {
  if (!PUBLISHER_ROLES.has((ctx.membershipRole || "").toLowerCase())) {
    throw APIError.permissionDenied(
      "automation publish/suspend requires an automation publisher role (founder / co-founder / admin)"
    );
  }
}

function canonicalize(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(canonicalize);
  if (value && typeof value === "object") {
    return Object.keys(value as Record<string, unknown>)
      .sort()
      .reduce<Record<string, unknown>>((acc, k) => {
        acc[k] = canonicalize((value as Record<string, unknown>)[k]);
        return acc;
      }, {});
  }
  return value;
}

function revisionHash(input: {
  automationKey: string;
  revisionNo: number;
  configuration: Record<string, unknown>;
  triggerContract: AutomationTriggerContract;
  capabilityIds: readonly string[];
  autonomyClass: string;
  approvalRequired: boolean;
  evidenceRequires: readonly string[];
  pinnedAgentSpecId: string;
}): string {
  return createHash("sha256")
    .update(JSON.stringify(canonicalize(input)))
    .digest("hex");
}

const URL_RE = /https?:\/\//i;

function validateConfiguration(
  blueprint: CuratedBlueprint,
  configuration: Record<string, unknown>
): void {
  const allowed = new Set(blueprint.configFields.map((f) => f.key));
  for (const key of Object.keys(configuration)) {
    if (!allowed.has(key)) {
      throw APIError.invalidArgument(
        `unknown configuration field '${key}' for blueprint ${blueprint.key}`
      );
    }
  }
  for (const field of blueprint.configFields) {
    const present = Object.prototype.hasOwnProperty.call(configuration, field.key);
    if (field.required && !present) {
      throw APIError.invalidArgument(`missing required field '${field.key}'`);
    }
    if (!present) continue;
    const v = configuration[field.key];
    if (typeof v === "string" && URL_RE.test(v)) {
      throw APIError.invalidArgument(`field '${field.key}' must not contain a raw URL`);
    }
    if (field.type === "number" && typeof v !== "number") {
      throw APIError.invalidArgument(`field '${field.key}' must be a number`);
    }
    if (field.type === "boolean" && typeof v !== "boolean") {
      throw APIError.invalidArgument(`field '${field.key}' must be a boolean`);
    }
    if (field.type === "enum" && (typeof v !== "string" || !field.enumValues?.includes(v))) {
      throw APIError.invalidArgument(`field '${field.key}' must be one of ${field.enumValues?.join(", ")}`);
    }
    if ((field.type === "string" || field.type === "text" || field.type === "date") && typeof v !== "string") {
      throw APIError.invalidArgument(`field '${field.key}' must be a string`);
    }
  }
}

function validateTriggerContract(blueprint: CuratedBlueprint, trigger: AutomationTriggerContract): void {
  if (!trigger || !blueprint.triggerKinds.includes(trigger.kind)) {
    throw APIError.invalidArgument(
      `blueprint ${blueprint.key} does not allow trigger kind '${trigger?.kind}'`
    );
  }
  if (trigger.kind === "schedule" && !trigger.schedule) {
    throw APIError.invalidArgument("schedule trigger requires a cron expression");
  }
  if (trigger.kind === "business_event" && !trigger.eventType) {
    throw APIError.invalidArgument("business_event trigger requires an eventType");
  }
}

interface RevisionRow {
  id: bigint;
  revisionNo: number;
  revisionHash: string;
  configurationJson: unknown;
  triggerContractJson: unknown;
  capabilityIds: unknown;
  autonomyClass: string;
  approvalContractJson: unknown;
  publishedAt: Date | null;
  createdAt: Date;
}

function toRevisionView(row: RevisionRow): AutomationRevisionView {
  const approval = (row.approvalContractJson ?? {}) as { required?: boolean };
  return {
    id: row.id.toString(),
    revisionNo: row.revisionNo,
    revisionHash: row.revisionHash,
    configuration: (row.configurationJson ?? {}) as Record<string, unknown>,
    triggerContract: (row.triggerContractJson ?? { kind: "manual" }) as AutomationTriggerContract,
    capabilityIds: (row.capabilityIds ?? []) as string[],
    autonomyClass: row.autonomyClass,
    approvalRequired: approval.required === true,
    published: row.publishedAt != null,
    publishedAt: row.publishedAt ? row.publishedAt.toISOString() : null,
    createdAt: row.createdAt.toISOString(),
  };
}

async function loadDefinitionRow(workspaceId: bigint, definitionId: bigint) {
  const [row] = await db
    .select()
    .from(automationDefinitions)
    .where(
      and(
        eq(automationDefinitions.id, definitionId),
        eq(automationDefinitions.workspaceId, workspaceId),
        isNull(automationDefinitions.deletedAt)
      )
    )
    .limit(1);
  return row ?? null;
}

async function loadRevision(workspaceId: bigint, revisionId: bigint | null) {
  if (revisionId == null) return null;
  const [row] = await db
    .select()
    .from(automationRevisions)
    .where(
      and(
        eq(automationRevisions.id, revisionId),
        eq(automationRevisions.workspaceId, workspaceId)
      )
    )
    .limit(1);
  return (row as RevisionRow | undefined) ?? null;
}

async function loadDraftRevision(workspaceId: bigint, definitionId: bigint) {
  const [row] = await db
    .select()
    .from(automationRevisions)
    .where(
      and(
        eq(automationRevisions.definitionId, definitionId),
        eq(automationRevisions.workspaceId, workspaceId),
        isNull(automationRevisions.publishedAt)
      )
    )
    .orderBy(desc(automationRevisions.revisionNo))
    .limit(1);
  return (row as RevisionRow | undefined) ?? null;
}

async function maxRevisionNo(definitionId: bigint): Promise<number> {
  const [row] = await db
    .select({ n: automationRevisions.revisionNo })
    .from(automationRevisions)
    .where(eq(automationRevisions.definitionId, definitionId))
    .orderBy(desc(automationRevisions.revisionNo))
    .limit(1);
  return row?.n ?? 0;
}

function buildDefinitionView(
  workspaceId: string,
  blueprint: CuratedBlueprint,
  defRow: { id: bigint; lifecycleState: string } | null,
  current: RevisionRow | null,
  draft: RevisionRow | null
): AutomationDefinitionView {
  return {
    id: defRow ? defRow.id.toString() : null,
    workspaceId,
    automationKey: blueprint.key,
    title: blueprint.title,
    purpose: blueprint.purpose,
    domain: blueprint.domain,
    lifecycleState: (defRow?.lifecycleState ?? "DRAFT") as AutomationLifecycleState,
    configured: defRow != null,
    configFields: blueprint.configFields,
    currentRevision: current ? toRevisionView(current) : null,
    draftRevision: draft ? toRevisionView(draft) : null,
  };
}

// --- service functions --------------------------------------------------

export async function listAutomationDefinitions(
  params: ListAutomationDefinitionsParams
): Promise<MvpSuccess<readonly AutomationDefinitionView[]>> {
  await requireWorkspaceAccess(params.authorization, params.workspaceId);
  const wsId = BigInt(params.workspaceId);

  const rows = await db
    .select()
    .from(automationDefinitions)
    .where(
      and(eq(automationDefinitions.workspaceId, wsId), isNull(automationDefinitions.deletedAt))
    );
  const byKey = new Map(rows.map((r) => [r.automationKey, r]));

  const views: AutomationDefinitionView[] = [];
  for (const key of CURATED_BLUEPRINT_KEYS) {
    const blueprint = CURATED_BLUEPRINTS[key];
    const defRow = byKey.get(key) ?? null;
    const current = defRow ? await loadRevision(wsId, defRow.currentRevisionId as bigint | null) : null;
    const draft = defRow ? await loadDraftRevision(wsId, defRow.id) : null;
    views.push(buildDefinitionView(params.workspaceId, blueprint, defRow, current, draft));
  }
  return mvpList(views, [SOURCE_REF]);
}

export async function getAutomationDefinition(
  params: GetAutomationDefinitionParams
): Promise<MvpSuccess<AutomationDefinitionView>> {
  await requireWorkspaceAccess(params.authorization, params.workspaceId);
  const wsId = BigInt(params.workspaceId);
  const defRow = await loadDefinitionRow(wsId, BigInt(params.definitionId));
  if (!defRow) throw APIError.notFound("automation definition not found");
  const blueprint = getCuratedBlueprint(defRow.automationKey);
  if (!blueprint) throw APIError.internal(`definition references unknown blueprint ${defRow.automationKey}`);
  const current = await loadRevision(wsId, defRow.currentRevisionId as bigint | null);
  const draft = await loadDraftRevision(wsId, defRow.id);
  return mvpItem(
    buildDefinitionView(params.workspaceId, blueprint, defRow, current, draft),
    [SOURCE_REF]
  );
}

export async function configureAutomationDefinition(
  params: ConfigureAutomationDefinitionParams
): Promise<MvpSuccess<AutomationDefinitionView>> {
  const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
  const blueprint = getCuratedBlueprint(params.automationKey);
  if (!blueprint) {
    throw APIError.invalidArgument(`unknown automation blueprint '${params.automationKey}'`);
  }
  validateConfiguration(blueprint, params.configuration);
  validateTriggerContract(blueprint, params.triggerContract);

  const wsId = BigInt(ctx.workspaceId);

  return db.transaction(async (tx) => {
    let [defRow] = await tx
      .select()
      .from(automationDefinitions)
      .where(
        and(
          eq(automationDefinitions.workspaceId, wsId),
          eq(automationDefinitions.automationKey, params.automationKey),
          isNull(automationDefinitions.deletedAt)
        )
      )
      .limit(1);

    if (defRow && defRow.lifecycleState === "RETIRED") {
      throw APIError.failedPrecondition("automation is retired and cannot be reconfigured");
    }

    if (!defRow) {
      const id = generateSnowflake();
      [defRow] = await tx
        .insert(automationDefinitions)
        .values({ id, workspaceId: wsId, automationKey: params.automationKey, lifecycleState: "DRAFT" })
        .returning();
    }

    const [existingDraft] = await tx
      .select()
      .from(automationRevisions)
      .where(
        and(
          eq(automationRevisions.definitionId, defRow.id),
          eq(automationRevisions.workspaceId, wsId),
          isNull(automationRevisions.publishedAt)
        )
      )
      .orderBy(desc(automationRevisions.revisionNo))
      .limit(1);

    const [maxRow] = await tx
      .select({ n: automationRevisions.revisionNo })
      .from(automationRevisions)
      .where(eq(automationRevisions.definitionId, defRow.id))
      .orderBy(desc(automationRevisions.revisionNo))
      .limit(1);

    const revisionNo = existingDraft ? existingDraft.revisionNo : (maxRow?.n ?? 0) + 1;
    const approvalRequired = blueprint.approvalRequired;
    const hash = revisionHash({
      automationKey: blueprint.key,
      revisionNo,
      configuration: params.configuration,
      triggerContract: params.triggerContract,
      capabilityIds: blueprint.capabilityIds,
      autonomyClass: blueprint.autonomyClass,
      approvalRequired,
      evidenceRequires: blueprint.evidenceContract.requires,
      pinnedAgentSpecId: blueprint.pinnedAgentSpecId,
    });

    const values = {
      workspaceId: wsId,
      definitionId: defRow.id,
      revisionNo,
      revisionHash: hash,
      configurationJson: params.configuration,
      triggerContractJson: params.triggerContract,
      capabilityIds: blueprint.capabilityIds as unknown as string[],
      evidenceContractJson: blueprint.evidenceContract,
      autonomyClass: blueprint.autonomyClass,
      approvalContractJson: { required: approvalRequired },
      pinnedDependenciesJson: { agentSpecId: blueprint.pinnedAgentSpecId, blueprintVersion: blueprint.version },
      createdBy: ctx.userId,
    };

    let draftRow: RevisionRow;
    if (existingDraft) {
      [draftRow] = (await tx
        .update(automationRevisions)
        .set({ ...values })
        .where(eq(automationRevisions.id, existingDraft.id))
        .returning()) as unknown as RevisionRow[];
    } else {
      [draftRow] = (await tx
        .insert(automationRevisions)
        .values({ id: generateSnowflake(), ...values })
        .returning()) as unknown as RevisionRow[];
    }

    await tx
      .update(automationDefinitions)
      .set({ updatedAt: new Date() })
      .where(eq(automationDefinitions.id, defRow.id));

    const current = await loadRevision(wsId, defRow.currentRevisionId as bigint | null);
    return mvpItem(
      buildDefinitionView(ctx.workspaceId, blueprint, defRow, current, draftRow),
      [SOURCE_REF]
    );
  });
}

export async function publishAutomationRevision(
  params: PublishAutomationRevisionParams
): Promise<MvpSuccess<AutomationDefinitionView>> {
  const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
  requirePublisher(ctx);
  const wsId = BigInt(ctx.workspaceId);

  return db.transaction(async (tx) => {
    const [defRow] = await tx
      .select()
      .from(automationDefinitions)
      .where(
        and(
          eq(automationDefinitions.id, BigInt(params.definitionId)),
          eq(automationDefinitions.workspaceId, wsId),
          isNull(automationDefinitions.deletedAt)
        )
      )
      .limit(1);
    if (!defRow) throw APIError.notFound("automation definition not found");
    if (defRow.lifecycleState === "RETIRED") {
      throw APIError.failedPrecondition("automation is retired");
    }

    const blueprint = getCuratedBlueprint(defRow.automationKey);
    if (!blueprint) throw APIError.internal(`unknown blueprint ${defRow.automationKey}`);

    const [draft] = (await tx
      .select()
      .from(automationRevisions)
      .where(
        and(
          eq(automationRevisions.definitionId, defRow.id),
          eq(automationRevisions.workspaceId, wsId),
          isNull(automationRevisions.publishedAt)
        )
      )
      .orderBy(desc(automationRevisions.revisionNo))
      .limit(1)) as unknown as RevisionRow[];
    if (!draft) throw APIError.failedPrecondition("nothing to publish — configure the automation first");

    // Publish validation (spec §6): capability set must be exactly the curated
    // allowlist, autonomy that touches effects must carry an approval contract,
    // the pinned AgentSpec must be a system spec.
    const declared = new Set((draft.capabilityIds ?? []) as string[]);
    for (const cap of declared) {
      if (!blueprint.capabilityIds.includes(cap)) {
        throw APIError.failedPrecondition(`capability '${cap}' is not permitted for ${blueprint.key}`);
      }
    }
    const approval = (draft.approvalContractJson ?? {}) as { required?: boolean };
    if (blueprint.autonomyClass === "gated_effect" && approval.required !== true) {
      throw APIError.failedPrecondition("gated_effect autonomy requires an approval contract");
    }
    const pinned = (draft as unknown as { pinnedDependenciesJson?: { agentSpecId?: string } }).pinnedDependenciesJson;
    if (!pinned?.agentSpecId || !pinned.agentSpecId.startsWith("cosa.agents.")) {
      throw APIError.failedPrecondition("pinned AgentSpec must be a system spec");
    }

    const now = new Date();
    const [publishedRevision] = (await tx
      .update(automationRevisions)
      .set({ publishedAt: now })
      .where(eq(automationRevisions.id, draft.id))
      .returning()) as unknown as RevisionRow[];

    await tx
      .update(automationDefinitions)
      .set({ currentRevisionId: draft.id, lifecycleState: "PUBLISHED", updatedAt: now })
      .where(eq(automationDefinitions.id, defRow.id));

    // Decision #4 (plan): a published revision with a schedule/business-event
    // trigger drives an EventTriggerRule in the Control Plane. The cross-plane
    // call is wired in Task 4 where dispatch exists; the trigger contract is
    // persisted on the revision so that wiring is a pure projection.

    const refreshed = { ...defRow, currentRevisionId: draft.id, lifecycleState: "PUBLISHED" as const };
    return mvpItem(
      buildDefinitionView(ctx.workspaceId, blueprint, refreshed, publishedRevision, null),
      [SOURCE_REF]
    );
  });
}

export async function suspendAutomationDefinition(
  params: SuspendAutomationDefinitionParams
): Promise<MvpSuccess<AutomationDefinitionView>> {
  const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
  requirePublisher(ctx);
  const wsId = BigInt(ctx.workspaceId);

  const defRow = await loadDefinitionRow(wsId, BigInt(params.definitionId));
  if (!defRow) throw APIError.notFound("automation definition not found");
  const blueprint = getCuratedBlueprint(defRow.automationKey);
  if (!blueprint) throw APIError.internal(`unknown blueprint ${defRow.automationKey}`);
  if (defRow.lifecycleState !== "PUBLISHED") {
    throw APIError.failedPrecondition("only a PUBLISHED automation can be suspended");
  }

  await db
    .update(automationDefinitions)
    .set({ lifecycleState: "SUSPENDED", updatedAt: new Date() })
    .where(and(eq(automationDefinitions.id, defRow.id), eq(automationDefinitions.workspaceId, wsId)));

  const current = await loadRevision(wsId, defRow.currentRevisionId as bigint | null);
  const draft = await loadDraftRevision(wsId, defRow.id);
  return mvpItem(
    buildDefinitionView(ctx.workspaceId, blueprint, { ...defRow, lifecycleState: "SUSPENDED" }, current, draft),
    [SOURCE_REF]
  );
}
