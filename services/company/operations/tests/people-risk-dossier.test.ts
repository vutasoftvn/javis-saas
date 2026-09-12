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
  createPeopleRiskDossier,
  appendPeopleRiskRevision,
  readPeopleRiskSnapshot,
} from "../services/people-risk-dossier.service";
import {
  createPeopleRiskDossierEndpoint,
  appendPeopleRiskRevisionEndpoint,
  readPeopleRiskSnapshotEndpoint,
} from "../handlers/people-risk-dossier.handler";
import { mintCompanyDelegation } from "../../shared/auth/cosa-delegation.service";

/**
 * Tạo project thứ hai TRONG CÙNG workspace (khác `createSecondWorkspace`,
 * vốn tạo workspace khác hẳn). Dùng để test cross-project isolation trong
 * cùng 1 tenant — gap mà reviewer Task 1 của CPO plan đã flag là chưa test.
 */
async function createSecondProjectInWorkspace(workspaceId: string): Promise<string> {
  const projectId = generateSnowflake();
  await db.execute(sql`
    INSERT INTO strategy.projects (id, workspace_id, title, status, lifecycle_stage)
    VALUES (${projectId}, ${BigInt(workspaceId)}, 'Second Project', 'ACTIVE', 'P0_DISCOVERY')
  `);
  return projectId.toString();
}

describe("People Risk Dossier Service", () => {
  let founderCtx: TenantContext;
  let memberCtx: TenantContext;
  let agentCtx: TenantContext;
  let foreignCtx: TenantContext;
  let workspaceId: string;
  let projectId: string;
  let secondProjectId: string;
  let dossierId: string;

  const draft = {
    capacityBands: [{ roleCategory: "engineering", headcount: 4 }],
    riskSignals: [
      { category: "single_point_of_failure" as const, severity: "HIGH" as const, sourceRef: "org-chart://eng-2026-09" },
    ],
    sourceRefs: [
      { sourceRef: "org-review://q3-2026", classification: "org_review" },
    ],
    reasonCode: "INITIAL_ASSESSMENT" as const,
  };

  beforeEach(async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    workspaceId = ws.workspaceId;
    projectId = ws.projectId;
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

    const created = await createPeopleRiskDossier(founderCtx, {
      projectId,
      capacityBands: draft.capacityBands,
      riskSignals: draft.riskSignals,
      sourceRefs: draft.sourceRefs,
      reasonCode: "INITIAL_ASSESSMENT",
    });
    dossierId = created.dossierId;
  });

  // --- (a) PII rejection ----------------------------------------------

  it("rejects a payload with an email-shaped field with invalid_argument", async () => {
    await expect(
      createPeopleRiskDossier(founderCtx, {
        ...draft,
        projectId: secondProjectId,
        candidateEmail: "a@b.test",
      } as never)
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  it("rejects an unknown field even when its value is not PII-shaped", async () => {
    await expect(
      createPeopleRiskDossier(founderCtx, {
        ...draft,
        projectId: secondProjectId,
        candidateName: "not an email or phone",
      } as never)
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  it("rejects a phone-number-shaped string nested inside an allowed field", async () => {
    await expect(
      createPeopleRiskDossier(founderCtx, {
        projectId: secondProjectId,
        capacityBands: [],
        riskSignals: [],
        sourceRefs: [{ sourceRef: "call +1 555-123-4567 for details", classification: "org_review" }],
        reasonCode: "SOURCE_UPDATED",
      } as never)
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  it("rejects a riskSignals category outside the fixed allowlist", async () => {
    await expect(
      createPeopleRiskDossier(founderCtx, {
        projectId: secondProjectId,
        riskSignals: [{ category: "performance_review", severity: "HIGH", sourceRef: "x" }],
        reasonCode: "RISK_REASSESSMENT",
      } as never)
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  it("rejects PII fields on append too", async () => {
    await expect(
      appendPeopleRiskRevision(founderCtx, dossierId, 1, {
        reasonCode: "RISK_REASSESSMENT",
        compensation: 150000,
      } as never)
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  // --- (b) foreign-workspace read is denied ----------------------------

  it("rejects a foreign-workspace read with permission_denied", async () => {
    await expect(readPeopleRiskSnapshot(foreignCtx, projectId)).rejects.toMatchObject({
      code: "permission_denied",
    });
  });

  // --- (c) cross-project isolation within the SAME workspace -----------

  it("rejects a same-workspace-different-project read (cross-project isolation)", async () => {
    await expect(readPeopleRiskSnapshot(founderCtx, secondProjectId)).rejects.toMatchObject({
      code: "not_found",
    });
  });

  // --- (d) agent/COSA-delegation context can never create or append ----

  it("agent context can never create a dossier", async () => {
    await expect(
      createPeopleRiskDossier(agentCtx, { projectId: secondProjectId, reasonCode: "INITIAL_ASSESSMENT" })
    ).rejects.toMatchObject({ code: "permission_denied" });
  });

  it("agent context can never append a revision", async () => {
    await expect(
      appendPeopleRiskRevision(agentCtx, dossierId, 1, { reasonCode: "RISK_REASSESSMENT" })
    ).rejects.toMatchObject({ code: "permission_denied" });
  });

  it("an agent context (non-founder) can still read the redacted snapshot", async () => {
    const snapshot = await readPeopleRiskSnapshot(agentCtx, projectId);
    expect(snapshot.dossierId).toBe(dossierId);
    expect(snapshot.riskSignals[0]).not.toHaveProperty("rawAttachment");
  });

  // Mirror product-decision-dossier.service.ts's exact test — prove the
  // Agent Platform (apps/cosa) cannot reach these endpoints at all: its only
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
      capability_ids: ["operations.people_risk.append"],
    });

    await expect(
      createPeopleRiskDossierEndpoint({
        authorization: `Bearer ${delegationToken}`,
        workspaceId: founderCtx.workspaceId,
        projectId: secondProjectId,
        reasonCode: "INITIAL_ASSESSMENT",
      })
    ).rejects.toMatchObject({ code: "unauthenticated" });

    await expect(
      appendPeopleRiskRevisionEndpoint({
        id: dossierId,
        authorization: `Bearer ${delegationToken}`,
        workspaceId: founderCtx.workspaceId,
        expectedVersion: 1,
        reasonCode: "RISK_REASSESSMENT",
      })
    ).rejects.toMatchObject({ code: "unauthenticated" });
  });

  it("rejects a COSA-delegation-signed token on the read endpoint the same way", async () => {
    const delegationToken = mintCompanyDelegation({
      sub: "cosa-worker-1",
      workspace_id: founderCtx.workspaceId,
      run_id: "run-1",
      capability_ids: ["people_risk.read"],
    });

    await expect(
      readPeopleRiskSnapshotEndpoint({
        projectId,
        authorization: `Bearer ${delegationToken}`,
        workspaceId: founderCtx.workspaceId,
      })
    ).rejects.toMatchObject({ code: "unauthenticated" });
  });

  // --- (e) one dossier per project --------------------------------------

  it("rejects a second dossier created for the same project as alreadyExists", async () => {
    await expect(
      createPeopleRiskDossier(founderCtx, { projectId, reasonCode: "INITIAL_ASSESSMENT" })
    ).rejects.toMatchObject({ code: "already_exists" });
  });

  // --- (f) CAS revision versioning ---------------------------------------

  it("creates a dossier as revision 1 in DRAFT status", async () => {
    expect(dossierId).toBeTruthy();
    const snapshot = await readPeopleRiskSnapshot(founderCtx, projectId);
    expect(snapshot.dossierId).toBe(dossierId);
    expect(snapshot.revision).toBe(1);
    expect(snapshot.status).toBe("DRAFT");
    expect(snapshot.capacityBands).toEqual([{ roleCategory: "engineering", headcount: 4 }]);
    expect(snapshot.riskSignals[0]).toMatchObject({
      category: "single_point_of_failure",
      severity: "HIGH",
    });
  });

  it("a human member can append a DRAFT revision with CAS, and stale CAS is rejected", async () => {
    const appended = await appendPeopleRiskRevision(memberCtx, dossierId, 1, {
      capacityBands: [{ roleCategory: "engineering", headcount: 5 }],
      reasonCode: "NEW_CAPACITY_DATA",
    });
    expect(appended.revision).toBe(2);
    expect(appended.status).toBe("DRAFT");

    await expect(
      appendPeopleRiskRevision(memberCtx, dossierId, 1, { reasonCode: "SOURCE_UPDATED" })
    ).rejects.toMatchObject({ code: "aborted" });
  });

  it("only a human founder can confirm a people risk revision", async () => {
    await expect(
      appendPeopleRiskRevision(memberCtx, dossierId, 1, {
        status: "CONFIRMED",
        reasonCode: "FOUNDER_REVIEW",
      })
    ).rejects.toMatchObject({ code: "permission_denied" });

    const confirmed = await appendPeopleRiskRevision(founderCtx, dossierId, 1, {
      status: "CONFIRMED",
      reasonCode: "FOUNDER_REVIEW",
    });
    expect(confirmed.status).toBe("CONFIRMED");
    expect(confirmed.revision).toBe(2);

    const snapshot = await readPeopleRiskSnapshot(founderCtx, projectId);
    expect(snapshot.status).toBe("CONFIRMED");
    expect(snapshot.revision).toBe(2);
  });

  it("rejects append to a dossier that does not exist in this workspace", async () => {
    await expect(
      appendPeopleRiskRevision(founderCtx, "999999999999999999", 1, { reasonCode: "SOURCE_UPDATED" })
    ).rejects.toMatchObject({ code: "not_found" });
  });

  it("rejects create when projectId is missing", async () => {
    await expect(
      createPeopleRiskDossier(founderCtx, { projectId: "", reasonCode: "INITIAL_ASSESSMENT" } as never)
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  it("rejects create when reasonCode is not one of the fixed allowed values", async () => {
    await expect(
      createPeopleRiskDossier(founderCtx, { projectId: secondProjectId, reasonCode: "because I said so" } as never)
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });
});
