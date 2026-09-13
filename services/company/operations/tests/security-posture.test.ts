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
  createSecurityPostureDossier,
  appendSecurityPostureRevision,
  readSecurityPostureSnapshot,
} from "../services/security-posture.service";
import {
  createSecurityPostureDossierEndpoint,
  appendSecurityPostureRevisionEndpoint,
  readSecurityPostureSnapshotEndpoint,
} from "../handlers/security-posture.handler";
import { mintCompanyDelegation } from "../../shared/auth/cosa-delegation.service";

/**
 * Tạo project thứ hai TRONG CÙNG workspace (khác `createSecondWorkspace`,
 * vốn tạo workspace khác hẳn). Dùng để test cross-project isolation trong
 * cùng 1 tenant.
 */
async function createSecondProjectInWorkspace(workspaceId: string): Promise<string> {
  const projectId = generateSnowflake();
  await db.execute(sql`
    INSERT INTO strategy.projects (id, workspace_id, title, status, lifecycle_stage)
    VALUES (${projectId}, ${BigInt(workspaceId)}, 'Second Project', 'ACTIVE', 'P0_DISCOVERY')
  `);
  return projectId.toString();
}

describe("Security Posture Dossier Service", () => {
  let founderCtx: TenantContext;
  let memberCtx: TenantContext;
  let agentCtx: TenantContext;
  let foreignCtx: TenantContext;
  let workspaceId: string;
  let projectId: string;
  let secondProjectId: string;
  let dossierId: string;
  let founderBearerToken: string;

  const draft = {
    controls: [{ controlId: "mfa-enforced", category: "access_control" as const, state: "IMPLEMENTED" as const }],
    findings: [
      { category: "outdated_dependency" as const, severity: "HIGH" as const, sourceRef: "dependency-scan://2026-09" },
    ],
    evidenceRefs: [
      { sourceRef: "security-review://q3-2026", classification: "security_review" },
    ],
    reasonCode: "INITIAL_ASSESSMENT" as const,
  };

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

    const created = await createSecurityPostureDossier(founderCtx, {
      projectId,
      controls: draft.controls,
      findings: draft.findings,
      evidenceRefs: draft.evidenceRefs,
      reasonCode: "INITIAL_ASSESSMENT",
    });
    dossierId = created.dossierId;
  });

  // --- (a) secret rejection ---------------------------------------------

  it("rejects a payload with a sk-prefixed token field with invalid_argument", async () => {
    await expect(
      createSecurityPostureDossier(founderCtx, {
        ...draft,
        projectId: secondProjectId,
        token: "sk-abcdefghijklmnopqrstuvwx",
      } as never)
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  it("rejects a PEM private key header nested inside an allowed field", async () => {
    await expect(
      createSecurityPostureDossier(founderCtx, {
        projectId: secondProjectId,
        controls: [],
        findings: [],
        evidenceRefs: [
          { sourceRef: "-----BEGIN RSA PRIVATE KEY-----\nMIIEow...", classification: "security_review" },
        ],
        reasonCode: "EVIDENCE_UPDATED",
      } as never)
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  it("rejects an Authorization header blob nested inside an allowed field", async () => {
    await expect(
      createSecurityPostureDossier(founderCtx, {
        projectId: secondProjectId,
        controls: [],
        findings: [],
        evidenceRefs: [
          { sourceRef: "log excerpt", classification: "security_review", redactedExcerpt: "Authorization: Bearer abc123def456ghi789jkl" },
        ],
        reasonCode: "EVIDENCE_UPDATED",
      } as never)
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  it("rejects an unknown field even when its value is not secret-shaped", async () => {
    await expect(
      createSecurityPostureDossier(founderCtx, {
        ...draft,
        projectId: secondProjectId,
        infraTopology: "not a secret, just an unknown field",
      } as never)
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  it("rejects a controls category outside the fixed allowlist", async () => {
    await expect(
      createSecurityPostureDossier(founderCtx, {
        projectId: secondProjectId,
        controls: [{ controlId: "x", category: "raw_config_dump", state: "IMPLEMENTED" }],
        reasonCode: "CONTROL_UPDATED",
      } as never)
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  it("rejects secret-bearing input on append too", async () => {
    await expect(
      appendSecurityPostureRevision(founderCtx, dossierId, 1, {
        reasonCode: "FINDING_ADDED",
        password: "hunter2",
      } as never)
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  // --- (b) foreign-workspace read is denied ------------------------------

  it("rejects a foreign-workspace read with permission_denied", async () => {
    await expect(readSecurityPostureSnapshot(foreignCtx, projectId)).rejects.toMatchObject({
      code: "permission_denied",
    });
  });

  // --- (c) cross-project isolation within the SAME workspace -------------

  it("rejects a same-workspace-different-project read (cross-project isolation)", async () => {
    await expect(readSecurityPostureSnapshot(founderCtx, secondProjectId)).rejects.toMatchObject({
      code: "not_found",
    });
  });

  // --- (d) agent/COSA-delegation context can never create or append ------

  it("agent context can never create a dossier", async () => {
    await expect(
      createSecurityPostureDossier(agentCtx, { projectId: secondProjectId, reasonCode: "INITIAL_ASSESSMENT" })
    ).rejects.toMatchObject({ code: "permission_denied" });
  });

  it("agent context can never append a revision", async () => {
    await expect(
      appendSecurityPostureRevision(agentCtx, dossierId, 1, { reasonCode: "FINDING_ADDED" })
    ).rejects.toMatchObject({ code: "permission_denied" });
  });

  it("an agent context (non-founder) can still read the redacted snapshot", async () => {
    const snapshot = await readSecurityPostureSnapshot(agentCtx, projectId);
    expect(snapshot.dossierId).toBe(dossierId);
    expect(snapshot.findings[0]).not.toHaveProperty("rawPayload");
  });

  // Mirror people-risk-dossier.test.ts's exact test — prove the Agent
  // Platform (apps/cosa) cannot reach these endpoints at all: its only
  // credential towards services/company is a COSA_COMPANY_DELEGATION_SECRET-
  // signed delegation token, never a JWT_SECRET-signed local session token.
  // `requireWorkspaceAccess` → `resolveTenantContext` only accepts the
  // latter, so a delegation token must be rejected with `unauthenticated`
  // BEFORE any TenantContext (and therefore any `ctx.isAiAgent` check) is
  // even built.
  it("rejects a COSA-delegation-signed token before any TenantContext is built", async () => {
    const delegationToken = mintCompanyDelegation({
      sub: "cosa-worker-1",
      workspace_id: founderCtx.workspaceId,
      run_id: "run-1",
      capability_ids: ["operations.security_posture.append"],
    });

    await expect(
      createSecurityPostureDossierEndpoint({
        authorization: `Bearer ${delegationToken}`,
        workspaceId: founderCtx.workspaceId,
        projectId: secondProjectId,
        reasonCode: "INITIAL_ASSESSMENT",
      })
    ).rejects.toMatchObject({ code: "unauthenticated" });

    await expect(
      appendSecurityPostureRevisionEndpoint({
        id: dossierId,
        authorization: `Bearer ${delegationToken}`,
        workspaceId: founderCtx.workspaceId,
        expectedVersion: 1,
        reasonCode: "FINDING_ADDED",
      })
    ).rejects.toMatchObject({ code: "unauthenticated" });
  });

  it("rejects a COSA-delegation-signed token on the read endpoint the same way", async () => {
    const delegationToken = mintCompanyDelegation({
      sub: "cosa-worker-1",
      workspace_id: founderCtx.workspaceId,
      run_id: "run-1",
      capability_ids: ["security_posture.read"],
    });

    await expect(
      readSecurityPostureSnapshotEndpoint({
        projectId,
        authorization: `Bearer ${delegationToken}`,
        workspaceId: founderCtx.workspaceId,
      })
    ).rejects.toMatchObject({ code: "unauthenticated" });
  });

  // --- (e) one dossier per project ----------------------------------------

  it("rejects a second dossier created for the same project as alreadyExists", async () => {
    await expect(
      createSecurityPostureDossier(founderCtx, { projectId, reasonCode: "INITIAL_ASSESSMENT" })
    ).rejects.toMatchObject({ code: "already_exists" });
  });

  // --- (f) CAS revision versioning -----------------------------------------

  it("creates a dossier as revision 1 in DRAFT status with aggregate severity", async () => {
    expect(dossierId).toBeTruthy();
    const snapshot = await readSecurityPostureSnapshot(founderCtx, projectId);
    expect(snapshot.dossierId).toBe(dossierId);
    expect(snapshot.revision).toBe(1);
    expect(snapshot.status).toBe("DRAFT");
    expect(snapshot.severity).toBe("HIGH");
    expect(snapshot.controlStates).toEqual([
      { controlId: "mfa-enforced", category: "access_control", state: "IMPLEMENTED" },
    ]);
    expect(snapshot.findings[0]).toMatchObject({
      category: "outdated_dependency",
      severity: "HIGH",
    });
  });

  it("a human member can append a DRAFT revision with CAS, and stale CAS is rejected", async () => {
    const appended = await appendSecurityPostureRevision(memberCtx, dossierId, 1, {
      controls: [{ controlId: "mfa-enforced", category: "access_control", state: "PARTIAL" }],
      findings: [{ category: "exposed_secret", severity: "CRITICAL", sourceRef: "scan://2026-09-13" }],
      reasonCode: "FINDING_ADDED",
    });
    expect(appended.revision).toBe(2);
    expect(appended.status).toBe("DRAFT");
    expect(appended.severity).toBe("CRITICAL");

    await expect(
      appendSecurityPostureRevision(memberCtx, dossierId, 1, { reasonCode: "EVIDENCE_UPDATED" })
    ).rejects.toMatchObject({ code: "aborted" });
  });

  it("only a human founder can confirm a security posture revision", async () => {
    await expect(
      appendSecurityPostureRevision(memberCtx, dossierId, 1, {
        status: "CONFIRMED",
        reasonCode: "FOUNDER_REVIEW",
      })
    ).rejects.toMatchObject({ code: "permission_denied" });

    const confirmed = await appendSecurityPostureRevision(founderCtx, dossierId, 1, {
      status: "CONFIRMED",
      reasonCode: "FOUNDER_REVIEW",
    });
    expect(confirmed.status).toBe("CONFIRMED");
    expect(confirmed.revision).toBe(2);

    const snapshot = await readSecurityPostureSnapshot(founderCtx, projectId);
    expect(snapshot.status).toBe("CONFIRMED");
    expect(snapshot.revision).toBe(2);
  });

  it("rejects append to a dossier that does not exist in this workspace", async () => {
    await expect(
      appendSecurityPostureRevision(founderCtx, "999999999999999999", 1, { reasonCode: "EVIDENCE_UPDATED" })
    ).rejects.toMatchObject({ code: "not_found" });
  });

  it("rejects create when projectId is missing", async () => {
    await expect(
      createSecurityPostureDossier(founderCtx, { projectId: "", reasonCode: "INITIAL_ASSESSMENT" } as never)
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  it("rejects create when reasonCode is not one of the fixed allowed values", async () => {
    await expect(
      createSecurityPostureDossier(founderCtx, { projectId: secondProjectId, reasonCode: "because I said so" } as never)
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  // --- (g) real handler/endpoint mapping (not just service function) -----
  //
  // CRITICAL regression test (progress.md lesson #7): CHRO's Task 1 handler
  // originally forwarded the raw Encore `params` object (which includes
  // Header-bound `workspaceId`/`authorization`) straight into the
  // allowlist-validated service call, so every real HTTP request self-
  // rejected with a FIELD_REJECTED error even with valid auth and valid
  // business fields. Calling the SERVICE function directly (as tests (a)-(f)
  // do) can never catch this class of bug because it bypasses the handler
  // entirely. This test calls the actual EXPORTED endpoint functions with a
  // real, valid founder bearer token and asserts they succeed end to end.

  it("the real create+append endpoints succeed with a valid founder token and real business fields (no Header-field leakage)", async () => {
    const created = await createSecurityPostureDossierEndpoint({
      workspaceId,
      authorization: founderBearerToken,
      projectId: secondProjectId,
      controls: draft.controls,
      findings: draft.findings,
      evidenceRefs: draft.evidenceRefs,
      reasonCode: "INITIAL_ASSESSMENT",
    });
    expect(created.revision).toBe(1);
    expect(created.severity).toBe("HIGH");

    const appended = await appendSecurityPostureRevisionEndpoint({
      id: created.dossierId,
      workspaceId,
      authorization: founderBearerToken,
      expectedVersion: 1,
      findings: [{ category: "exposed_secret", severity: "CRITICAL", sourceRef: "scan://2026-09-13" }],
      reasonCode: "FINDING_ADDED",
    });
    expect(appended.revision).toBe(2);
    expect(appended.severity).toBe("CRITICAL");
  });
});
