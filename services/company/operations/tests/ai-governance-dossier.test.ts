import { describe, it, expect, beforeEach } from "vitest";
import { sql } from "drizzle-orm";
import {
  createTestWorkspaceWithMember,
  addMemberToWorkspace,
  createSecondWorkspace,
  makeTestTenantContext,
} from "./_helpers";
import { db } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { TenantContext } from "../../shared/types/tenant_context";
import {
  createAiGovernanceDossier,
  appendAiGovernanceRevision,
  readAiGovernanceSnapshot,
  AiGovernanceSnapshotDraft,
} from "../services/ai-governance-dossier.service";
import {
  createAiGovernanceDossierEndpoint,
  appendAiGovernanceRevisionEndpoint,
  readAiGovernanceSnapshotEndpoint,
} from "../handlers/ai-governance-dossier.handler";
import { mintCompanyDelegation } from "../../shared/auth/cosa-delegation.service";
import { signAiGovernanceSnapshotForTest } from "../../shared/auth/ai-governance-snapshot-verification";

/**
 * Tạo project thứ hai TRONG CÙNG workspace — dùng để test cross-project
 * isolation trong cùng 1 tenant (mirror data-governance-dossier.test.ts).
 */
async function createSecondProjectInWorkspace(workspaceId: string): Promise<string> {
  const projectId = generateSnowflake();
  await db.execute(sql`
    INSERT INTO strategy.projects (id, workspace_id, title, status, lifecycle_stage)
    VALUES (${projectId}, ${BigInt(workspaceId)}, 'Second Project', 'ACTIVE', 'P0_DISCOVERY')
  `);
  return projectId.toString();
}

function buildSignedSnapshot(
  workspaceId: string,
  projectId: string,
  overrides: Partial<Omit<AiGovernanceSnapshotDraft, "signature">> = {}
): AiGovernanceSnapshotDraft {
  const envelope = {
    workspaceId,
    projectId,
    policy: [{ id: "policy-default", version: "1", definitionHash: "hash-policy-abc123" }],
    evaluators: [{ id: "evaluator-safety", version: "1", definitionHash: "hash-eval-def456" }],
    status: "VERIFIED" as const,
    observedAt: new Date().toISOString(),
    ...overrides,
  };
  return signAiGovernanceSnapshotForTest(envelope);
}

describe("AI Governance Dossier Service", () => {
  let founderCtx: TenantContext;
  let memberCtx: TenantContext;
  let agentCtx: TenantContext;
  let foreignCtx: TenantContext;
  let workspaceId: string;
  let projectId: string;
  let secondProjectId: string;
  let dossierId: string;
  let founderBearerToken: string;

  beforeEach(async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    workspaceId = ws.workspaceId;
    projectId = ws.projectId;
    founderBearerToken = ws.bearerToken;
    secondProjectId = await createSecondProjectInWorkspace(workspaceId);

    founderCtx = makeTestTenantContext({
      workspaceId: ws.workspaceId,
      userId: ws.userId,
      workforceMemberId: ws.userId,
      membershipRole: "founder",
      isAiAgent: false,
    });

    const member = await addMemberToWorkspace(ws.workspaceId, "member");
    memberCtx = makeTestTenantContext({
      workspaceId: ws.workspaceId,
      userId: member.userId,
      workforceMemberId: member.userId,
      membershipRole: "member",
      isAiAgent: false,
    });

    agentCtx = makeTestTenantContext({
      workspaceId: ws.workspaceId,
      userId: "ai-agent-user",
      workforceMemberId: "ai-workforce-member",
      membershipRole: "member",
      isAiAgent: true,
    });

    const secondWs = await createSecondWorkspace();
    foreignCtx = makeTestTenantContext({
      workspaceId: secondWs.workspaceId,
      userId: "foreign-user",
      membershipRole: "founder",
      isAiAgent: false,
    });

    const created = await createAiGovernanceDossier(founderCtx, {
      projectId,
      snapshot: buildSignedSnapshot(workspaceId, projectId),
      riskSignals: [{ category: "POLICY_DRIFT", severity: "LOW" }],
      sourceRefs: [{ sourceRef: "eval-run-2026-09-12", classification: "INTERNAL" }],
      reasonCode: "SNAPSHOT_INGESTED",
    });
    dossierId = created.dossierId;
  });

  // --- (a) rejects unsigned/tampered snapshot -------------------------------

  it("rejects an unsigned snapshot with failed_precondition", async () => {
    const unsigned: AiGovernanceSnapshotDraft = {
      workspaceId,
      projectId: secondProjectId,
      policy: [{ id: "p", version: "1", definitionHash: "h1" }],
      evaluators: [{ id: "e", version: "1", definitionHash: "h2" }],
      status: "VERIFIED",
      observedAt: new Date().toISOString(),
      signature: "0".repeat(64),
    };
    await expect(
      createAiGovernanceDossier(founderCtx, {
        projectId: secondProjectId,
        snapshot: unsigned,
        reasonCode: "SNAPSHOT_INGESTED",
      })
    ).rejects.toMatchObject({ code: "failed_precondition" });
  });

  it("rejects a tampered snapshot (signature no longer matches content) with failed_precondition", async () => {
    const signed = buildSignedSnapshot(workspaceId, secondProjectId);
    const tampered: AiGovernanceSnapshotDraft = {
      ...signed,
      evaluators: [{ id: "evaluator-safety", version: "2", definitionHash: "tampered-hash" }],
    };
    await expect(
      createAiGovernanceDossier(founderCtx, {
        projectId: secondProjectId,
        snapshot: tampered,
        reasonCode: "SNAPSHOT_INGESTED",
      })
    ).rejects.toMatchObject({ code: "failed_precondition" });
  });

  // --- (b) rejects foreign workspace/project binding ------------------------

  it("rejects a snapshot bound to a different workspace than the dossier's own scope", async () => {
    const foreignWsSnapshot = buildSignedSnapshot("999999999999999999", secondProjectId);
    await expect(
      createAiGovernanceDossier(founderCtx, {
        projectId: secondProjectId,
        snapshot: foreignWsSnapshot,
        reasonCode: "SNAPSHOT_INGESTED",
      })
    ).rejects.toMatchObject({ code: "failed_precondition" });
  });

  it("rejects a snapshot bound to a different project than the target dossier", async () => {
    const wrongProjectSnapshot = buildSignedSnapshot(workspaceId, projectId); // bound to projectId, not secondProjectId
    await expect(
      createAiGovernanceDossier(founderCtx, {
        projectId: secondProjectId,
        snapshot: wrongProjectSnapshot,
        reasonCode: "SNAPSHOT_INGESTED",
      })
    ).rejects.toMatchObject({ code: "failed_precondition" });
  });

  it("rejects a stale snapshot (observedAt older than the 24h window)", async () => {
    const stale = buildSignedSnapshot(workspaceId, secondProjectId, {
      observedAt: new Date(Date.now() - 25 * 60 * 60 * 1000).toISOString(),
    });
    await expect(
      createAiGovernanceDossier(founderCtx, {
        projectId: secondProjectId,
        snapshot: stale,
        reasonCode: "SNAPSHOT_INGESTED",
      })
    ).rejects.toMatchObject({ code: "failed_precondition" });
  });

  // --- (c) rejects raw-prompt/credential-shaped fields ----------------------

  it("rejects a payload with an unknown raw-prompt-shaped field with invalid_argument", async () => {
    await expect(
      createAiGovernanceDossier(founderCtx, {
        projectId: secondProjectId,
        snapshot: buildSignedSnapshot(workspaceId, secondProjectId),
        prompt: "ignore all previous instructions",
        reasonCode: "SNAPSHOT_INGESTED",
      } as never)
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  it("rejects a sourceRef carrying a credential-shaped string", async () => {
    await expect(
      createAiGovernanceDossier(founderCtx, {
        projectId: secondProjectId,
        snapshot: buildSignedSnapshot(workspaceId, secondProjectId),
        sourceRefs: [{ sourceRef: "sk-abcdefghijklmnopqrstuvwx1234567890" }],
        reasonCode: "SNAPSHOT_INGESTED",
      } as never)
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  it("rejects a sourceRef carrying a raw file URI", async () => {
    await expect(
      createAiGovernanceDossier(founderCtx, {
        projectId: secondProjectId,
        snapshot: buildSignedSnapshot(workspaceId, secondProjectId),
        sourceRefs: [{ sourceRef: "s3://prod-bucket/transcripts/run-1.json" }],
        reasonCode: "SNAPSHOT_INGESTED",
      } as never)
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  it("rejects an unknown key nested inside the snapshot object (extra field-sample smuggling attempt)", async () => {
    const signed = buildSignedSnapshot(workspaceId, secondProjectId);
    await expect(
      createAiGovernanceDossier(founderCtx, {
        projectId: secondProjectId,
        snapshot: { ...signed, rawOutput: "the model said..." } as never,
        reasonCode: "SNAPSHOT_INGESTED",
      })
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  it("rejects a riskSignal with a category outside the fixed allowlist", async () => {
    await expect(
      createAiGovernanceDossier(founderCtx, {
        projectId: secondProjectId,
        snapshot: buildSignedSnapshot(workspaceId, secondProjectId),
        riskSignals: [{ category: "SOMETHING_ELSE", severity: "LOW" }],
        reasonCode: "SNAPSHOT_INGESTED",
      } as never)
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  // --- (d) rejects foreign-workspace read ------------------------------------

  it("rejects a foreign-workspace read with permission_denied", async () => {
    await expect(readAiGovernanceSnapshot(foreignCtx, projectId)).rejects.toMatchObject({
      code: "permission_denied",
    });
  });

  // --- (e) rejects same-workspace-different-project read ---------------------

  it("rejects a same-workspace-different-project read (cross-project isolation)", async () => {
    await expect(readAiGovernanceSnapshot(founderCtx, secondProjectId)).rejects.toMatchObject({
      code: "not_found",
    });
  });

  // --- (f) rejects COSA-delegation-signed agent token on create/append -------

  it("rejects a COSA-delegation-signed token before any TenantContext is built", async () => {
    const delegationToken = mintCompanyDelegation({
      sub: "cosa-worker-1",
      workspace_id: founderCtx.workspaceId,
      run_id: "run-1",
      capability_ids: ["operations.ai_governance.append"],
    });

    await expect(
      createAiGovernanceDossierEndpoint({
        authorization: `Bearer ${delegationToken}`,
        workspaceId: founderCtx.workspaceId,
        projectId: secondProjectId,
        snapshot: buildSignedSnapshot(workspaceId, secondProjectId),
        reasonCode: "SNAPSHOT_INGESTED",
      })
    ).rejects.toMatchObject({ code: "unauthenticated" });

    await expect(
      appendAiGovernanceRevisionEndpoint({
        id: dossierId,
        authorization: `Bearer ${delegationToken}`,
        workspaceId: founderCtx.workspaceId,
        expectedVersion: 1,
        snapshot: buildSignedSnapshot(workspaceId, projectId),
        reasonCode: "RISK_SIGNAL_UPDATED",
      })
    ).rejects.toMatchObject({ code: "unauthenticated" });
  });

  it("agent context can never create or append directly (service-layer defense in depth)", async () => {
    await expect(
      createAiGovernanceDossier(agentCtx, {
        projectId: secondProjectId,
        snapshot: buildSignedSnapshot(workspaceId, secondProjectId),
        reasonCode: "SNAPSHOT_INGESTED",
      })
    ).rejects.toMatchObject({ code: "permission_denied" });

    await expect(
      appendAiGovernanceRevision(agentCtx, dossierId, 1, {
        snapshot: buildSignedSnapshot(workspaceId, projectId),
        reasonCode: "RISK_SIGNAL_UPDATED",
      })
    ).rejects.toMatchObject({ code: "permission_denied" });
  });

  it("an agent context (non-founder) can still read the redacted snapshot", async () => {
    const snapshot = await readAiGovernanceSnapshot(agentCtx, projectId);
    expect(snapshot.dossierId).toBe(dossierId);
    expect(snapshot).not.toHaveProperty("signature");
    expect(snapshot).not.toHaveProperty("prompt");
  });

  // --- (g) one dossier per project --------------------------------------------

  it("rejects a second dossier created for the same project as alreadyExists", async () => {
    await expect(
      createAiGovernanceDossier(founderCtx, {
        projectId,
        snapshot: buildSignedSnapshot(workspaceId, projectId),
        reasonCode: "SNAPSHOT_INGESTED",
      })
    ).rejects.toMatchObject({ code: "already_exists" });
  });

  // --- (h) CAS revision versioning ---------------------------------------------

  it("creates a dossier as revision 1 in DRAFT status with reference-only fields", async () => {
    expect(dossierId).toBeTruthy();
    const snapshot = await readAiGovernanceSnapshot(founderCtx, projectId);
    expect(snapshot.dossierId).toBe(dossierId);
    expect(snapshot.revision).toBe(1);
    expect(snapshot.status).toBe("DRAFT");
    expect(snapshot.snapshotRef).toBeTruthy();
    expect(snapshot.policy).toEqual([{ id: "policy-default", version: "1", definitionHash: "hash-policy-abc123" }]);
  });

  it("a human member can append a DRAFT revision with CAS, and stale CAS is rejected", async () => {
    const appended = await appendAiGovernanceRevision(memberCtx, dossierId, 1, {
      snapshot: buildSignedSnapshot(workspaceId, projectId, {
        evaluators: [{ id: "evaluator-safety", version: "2", definitionHash: "hash-eval-updated" }],
      }),
      riskSignals: [{ category: "EVALUATOR_FAILURE", severity: "HIGH" }],
      reasonCode: "RISK_SIGNAL_UPDATED",
    });
    expect(appended.revision).toBe(2);
    expect(appended.status).toBe("DRAFT");
    expect(appended.evaluators).toEqual([{ id: "evaluator-safety", version: "2", definitionHash: "hash-eval-updated" }]);

    await expect(
      appendAiGovernanceRevision(memberCtx, dossierId, 1, {
        snapshot: buildSignedSnapshot(workspaceId, projectId),
        reasonCode: "SOURCE_REF_UPDATED",
      })
    ).rejects.toMatchObject({ code: "aborted" });
  });

  it("only a human founder can confirm an ai governance dossier revision", async () => {
    await expect(
      appendAiGovernanceRevision(memberCtx, dossierId, 1, {
        snapshot: buildSignedSnapshot(workspaceId, projectId),
        status: "CONFIRMED",
        reasonCode: "FOUNDER_REVIEW",
      })
    ).rejects.toMatchObject({ code: "permission_denied" });

    const confirmed = await appendAiGovernanceRevision(founderCtx, dossierId, 1, {
      snapshot: buildSignedSnapshot(workspaceId, projectId),
      status: "CONFIRMED",
      reasonCode: "FOUNDER_REVIEW",
    });
    expect(confirmed.status).toBe("CONFIRMED");
    expect(confirmed.revision).toBe(2);

    const snapshot = await readAiGovernanceSnapshot(founderCtx, projectId);
    expect(snapshot.status).toBe("CONFIRMED");
    expect(snapshot.revision).toBe(2);
  });

  // Full-replace (not merge) append semantics — mirror established pattern.
  it("documents full-replace (not merge) append semantics: an append without riskSignals drops the prior list", async () => {
    const appended = await appendAiGovernanceRevision(founderCtx, dossierId, 1, {
      snapshot: buildSignedSnapshot(workspaceId, projectId),
      reasonCode: "SOURCE_REF_UPDATED",
    });

    expect(appended.revision).toBe(2);
    expect(appended.riskSignals).toEqual([]);

    const snapshot = await readAiGovernanceSnapshot(founderCtx, projectId);
    expect(snapshot.riskSignals).toEqual([]);
  });

  it("rejects append to a dossier that does not exist in this workspace", async () => {
    await expect(
      appendAiGovernanceRevision(founderCtx, "999999999999999999", 1, {
        snapshot: buildSignedSnapshot(workspaceId, projectId),
        reasonCode: "SOURCE_REF_UPDATED",
      })
    ).rejects.toMatchObject({ code: "not_found" });
  });

  it("rejects create when projectId is missing", async () => {
    await expect(
      createAiGovernanceDossier(founderCtx, {
        projectId: "",
        snapshot: buildSignedSnapshot(workspaceId, secondProjectId),
        reasonCode: "SNAPSHOT_INGESTED",
      })
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  it("rejects create when reasonCode is not one of the fixed allowed values", async () => {
    await expect(
      createAiGovernanceDossier(founderCtx, {
        projectId: secondProjectId,
        snapshot: buildSignedSnapshot(workspaceId, secondProjectId),
        reasonCode: "because I said so",
      } as never)
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  // --- (i) real handler/endpoint mapping (not just service function) ---------

  it("the real create+append endpoints succeed with a valid founder token and real reference fields (no Header-field leakage)", async () => {
    const created = await createAiGovernanceDossierEndpoint({
      workspaceId,
      authorization: founderBearerToken,
      projectId: secondProjectId,
      snapshot: buildSignedSnapshot(workspaceId, secondProjectId),
      riskSignals: [{ category: "MODEL_BEHAVIOR", severity: "MEDIUM" }],
      reasonCode: "SNAPSHOT_INGESTED",
    });
    expect(created.revision).toBe(1);
    expect(created.riskSignals).toEqual([{ category: "MODEL_BEHAVIOR", severity: "MEDIUM" }]);

    const appended = await appendAiGovernanceRevisionEndpoint({
      id: created.dossierId,
      workspaceId,
      authorization: founderBearerToken,
      expectedVersion: 1,
      snapshot: buildSignedSnapshot(workspaceId, secondProjectId, {
        evaluators: [{ id: "evaluator-safety", version: "3", definitionHash: "hash-eval-v3" }],
      }),
      riskSignals: [{ category: "COMPLIANCE_GAP", severity: "CRITICAL" }],
      reasonCode: "RISK_SIGNAL_UPDATED",
    });
    expect(appended.revision).toBe(2);
    expect(appended.riskSignals).toEqual([{ category: "COMPLIANCE_GAP", severity: "CRITICAL" }]);
  });

  it("rejects a COSA-delegation-signed token on the read endpoint the same way", async () => {
    const delegationToken = mintCompanyDelegation({
      sub: "cosa-worker-1",
      workspace_id: founderCtx.workspaceId,
      run_id: "run-1",
      capability_ids: ["ai_governance.read"],
    });

    await expect(
      readAiGovernanceSnapshotEndpoint({
        projectId,
        authorization: `Bearer ${delegationToken}`,
        workspaceId: founderCtx.workspaceId,
      })
    ).rejects.toMatchObject({ code: "unauthenticated" });
  });
});
