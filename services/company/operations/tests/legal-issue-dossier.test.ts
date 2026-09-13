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
  createLegalIssueDossier,
  appendLegalIssueRevision,
  readLegalIssueSnapshot,
} from "../services/legal-issue-dossier.service";
import {
  createLegalIssueDossierEndpoint,
  appendLegalIssueRevisionEndpoint,
  readLegalIssueSnapshotEndpoint,
} from "../handlers/legal-issue-dossier.handler";
import { mintCompanyDelegation } from "../../shared/auth/cosa-delegation.service";
import { createObligationService } from "../../finance-legal/services/legal-obligation.service";

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

describe("Legal Issue Dossier Service", () => {
  let founderCtx: TenantContext;
  let memberCtx: TenantContext;
  let agentCtx: TenantContext;
  let foreignCtx: TenantContext;
  let workspaceId: string;
  let projectId: string;
  let secondProjectId: string;
  let dossierId: string;
  let founderBearerToken: string;
  let obligationId: string;

  const draft = {
    issueCategory: "CONTRACT_QUESTION" as const,
    legalRecordRefs: [] as { recordType: "OBLIGATION"; recordId: string; classification?: string }[],
    applicabilityStatus: "UNKNOWN" as const,
    jurisdiction: "US-DE",
    redactedQuestion: "Does the vendor MSA renewal clause require 30 or 60 days notice?",
    reasonCode: "ISSUE_RAISED" as const,
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

    // Seed một obligation THẬT qua Finance-Legal service thật (không SQL
    // trực tiếp) để legalRecordRefs có một recordId hợp lệ tham chiếu tới.
    const obligation = await createObligationService(
      { workspaceId, title: "Annual data protection filing" },
      founderBearerToken
    );
    obligationId = obligation.id;

    const created = await createLegalIssueDossier(founderCtx, {
      projectId,
      issueCategory: draft.issueCategory,
      legalRecordRefs: [{ recordType: "OBLIGATION", recordId: obligationId }],
      applicabilityStatus: draft.applicabilityStatus,
      jurisdiction: draft.jurisdiction,
      redactedQuestion: draft.redactedQuestion,
      reasonCode: draft.reasonCode,
    });
    dossierId = created.dossierId;
  });

  // --- (a) contract-body / PII rejection ---------------------------------

  it("rejects a payload with a contract-body-shaped field with invalid_argument", async () => {
    await expect(
      createLegalIssueDossier(founderCtx, {
        ...draft,
        projectId: secondProjectId,
        redactedQuestion:
          "WHEREAS the parties wish to enter into this Agreement, NOW THEREFORE in consideration of the mutual covenants contained herein, the parties agree as follows...",
      } as never)
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  it("rejects a payload with a PII-shaped field (email) with invalid_argument", async () => {
    await expect(
      createLegalIssueDossier(founderCtx, {
        ...draft,
        projectId: secondProjectId,
        redactedQuestion: "Please contact jane.doe@example.com about the renewal terms",
      } as never)
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  it("rejects a payload with privileged-advice-shaped language with invalid_argument", async () => {
    await expect(
      createLegalIssueDossier(founderCtx, {
        ...draft,
        projectId: secondProjectId,
        redactedQuestion: "This is protected by attorney-client privilege: outside counsel advises we settle",
      } as never)
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  it("rejects a redacted question that is far too long (contract-body-shaped by length)", async () => {
    await expect(
      createLegalIssueDossier(founderCtx, {
        ...draft,
        projectId: secondProjectId,
        redactedQuestion: "a".repeat(801),
      } as never)
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  it("rejects an unknown field even when its value is not secret-shaped", async () => {
    await expect(
      createLegalIssueDossier(founderCtx, {
        ...draft,
        projectId: secondProjectId,
        contractBody: "private",
      } as never)
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  it("rejects an issueCategory outside the fixed allowlist", async () => {
    await expect(
      createLegalIssueDossier(founderCtx, {
        ...draft,
        projectId: secondProjectId,
        issueCategory: "because I said so",
      } as never)
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  it("rejects secret/PII-bearing input on append too", async () => {
    await expect(
      appendLegalIssueRevision(founderCtx, dossierId, 1, {
        ...draft,
        redactedQuestion: "call me at 555-123-4567",
        reasonCode: "REFERENCE_UPDATED",
      } as never)
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  // --- (b) foreign-workspace read is denied ------------------------------

  it("rejects a foreign-workspace read with permission_denied", async () => {
    await expect(readLegalIssueSnapshot(foreignCtx, projectId)).rejects.toMatchObject({
      code: "permission_denied",
    });
  });

  // --- (c) cross-project isolation within the SAME workspace -------------

  it("rejects a same-workspace-different-project read (cross-project isolation)", async () => {
    await expect(readLegalIssueSnapshot(founderCtx, secondProjectId)).rejects.toMatchObject({
      code: "not_found",
    });
  });

  // --- (d) agent/COSA-delegation context can never create or append ------

  it("agent context can never create a dossier", async () => {
    await expect(
      createLegalIssueDossier(agentCtx, { ...draft, projectId: secondProjectId } as never)
    ).rejects.toMatchObject({ code: "permission_denied" });
  });

  it("agent context can never append a revision", async () => {
    await expect(
      appendLegalIssueRevision(agentCtx, dossierId, 1, { ...draft, reasonCode: "REFERENCE_UPDATED" } as never)
    ).rejects.toMatchObject({ code: "permission_denied" });
  });

  it("an agent context (non-founder) can still read the redacted snapshot", async () => {
    const snapshot = await readLegalIssueSnapshot(agentCtx, projectId);
    expect(snapshot.dossierId).toBe(dossierId);
    expect(snapshot).not.toHaveProperty("contractBody");
  });

  // Mirror security-posture.test.ts's exact test — prove the Agent Platform
  // (apps/cosa) cannot reach these endpoints at all: its only credential
  // towards services/company is a COSA_COMPANY_DELEGATION_SECRET-signed
  // delegation token, never a JWT_SECRET-signed local session token.
  // `requireWorkspaceAccess` → `resolveTenantContext` only accepts the
  // latter, so a delegation token must be rejected with `unauthenticated`
  // BEFORE any TenantContext (and therefore any `ctx.isAiAgent` check) is
  // even built.
  it("rejects a COSA-delegation-signed token before any TenantContext is built", async () => {
    const delegationToken = mintCompanyDelegation({
      sub: "cosa-worker-1",
      workspace_id: founderCtx.workspaceId,
      run_id: "run-1",
      capability_ids: ["operations.legal_issue.append"],
    });

    await expect(
      createLegalIssueDossierEndpoint({
        authorization: `Bearer ${delegationToken}`,
        workspaceId: founderCtx.workspaceId,
        projectId: secondProjectId,
        issueCategory: draft.issueCategory,
        redactedQuestion: draft.redactedQuestion,
        reasonCode: draft.reasonCode,
      })
    ).rejects.toMatchObject({ code: "unauthenticated" });

    await expect(
      appendLegalIssueRevisionEndpoint({
        id: dossierId,
        authorization: `Bearer ${delegationToken}`,
        workspaceId: founderCtx.workspaceId,
        expectedVersion: 1,
        issueCategory: draft.issueCategory,
        redactedQuestion: draft.redactedQuestion,
        reasonCode: "REFERENCE_UPDATED",
      })
    ).rejects.toMatchObject({ code: "unauthenticated" });
  });

  it("rejects a COSA-delegation-signed token on the read endpoint the same way", async () => {
    const delegationToken = mintCompanyDelegation({
      sub: "cosa-worker-1",
      workspace_id: founderCtx.workspaceId,
      run_id: "run-1",
      capability_ids: ["legal_issue.read"],
    });

    await expect(
      readLegalIssueSnapshotEndpoint({
        projectId,
        authorization: `Bearer ${delegationToken}`,
        workspaceId: founderCtx.workspaceId,
      })
    ).rejects.toMatchObject({ code: "unauthenticated" });
  });

  // --- (e) one dossier per project ----------------------------------------

  it("rejects a second dossier created for the same project as alreadyExists", async () => {
    await expect(
      createLegalIssueDossier(founderCtx, { ...draft, projectId } as never)
    ).rejects.toMatchObject({ code: "already_exists" });
  });

  // --- (f) CAS revision versioning -----------------------------------------

  it("creates a dossier as revision 1 in DRAFT status with UNKNOWN applicability", async () => {
    expect(dossierId).toBeTruthy();
    const snapshot = await readLegalIssueSnapshot(founderCtx, projectId);
    expect(snapshot.dossierId).toBe(dossierId);
    expect(snapshot.revision).toBe(1);
    expect(snapshot.status).toBe("DRAFT");
    expect(snapshot.issueCategory).toBe("CONTRACT_QUESTION");
    expect(snapshot.applicabilityStatus).toBe("UNKNOWN");
    expect(snapshot.legalRecordRefs).toEqual([{ recordType: "OBLIGATION", recordId: obligationId }]);
  });

  it("a human member can append a DRAFT revision with CAS, and stale CAS is rejected", async () => {
    const appended = await appendLegalIssueRevision(memberCtx, dossierId, 1, {
      issueCategory: "REGULATORY_QUESTION",
      legalRecordRefs: [{ recordType: "OBLIGATION", recordId: obligationId }],
      applicabilityStatus: "APPLICABLE",
      redactedQuestion: "Does the new data protection filing apply to our EU subsidiary?",
      reasonCode: "APPLICABILITY_UPDATED",
    });
    expect(appended.revision).toBe(2);
    expect(appended.status).toBe("DRAFT");
    expect(appended.applicabilityStatus).toBe("APPLICABLE");
    expect(appended.issueCategory).toBe("REGULATORY_QUESTION");

    await expect(
      appendLegalIssueRevision(memberCtx, dossierId, 1, {
        ...draft,
        reasonCode: "REFERENCE_UPDATED",
      })
    ).rejects.toMatchObject({ code: "aborted" });
  });

  it("only a human founder can confirm a legal issue dossier revision", async () => {
    await expect(
      appendLegalIssueRevision(memberCtx, dossierId, 1, {
        ...draft,
        status: "CONFIRMED",
        reasonCode: "FOUNDER_REVIEW",
      })
    ).rejects.toMatchObject({ code: "permission_denied" });

    const confirmed = await appendLegalIssueRevision(founderCtx, dossierId, 1, {
      ...draft,
      status: "CONFIRMED",
      reasonCode: "FOUNDER_REVIEW",
    });
    expect(confirmed.status).toBe("CONFIRMED");
    expect(confirmed.revision).toBe(2);

    const snapshot = await readLegalIssueSnapshot(founderCtx, projectId);
    expect(snapshot.status).toBe("CONFIRMED");
    expect(snapshot.revision).toBe(2);
  });

  it("rejects append to a dossier that does not exist in this workspace", async () => {
    await expect(
      appendLegalIssueRevision(founderCtx, "999999999999999999", 1, {
        ...draft,
        reasonCode: "REFERENCE_UPDATED",
      })
    ).rejects.toMatchObject({ code: "not_found" });
  });

  it("rejects create when projectId is missing", async () => {
    await expect(
      createLegalIssueDossier(founderCtx, { ...draft, projectId: "" } as never)
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  it("rejects create when reasonCode is not one of the fixed allowed values", async () => {
    await expect(
      createLegalIssueDossier(founderCtx, {
        ...draft,
        projectId: secondProjectId,
        reasonCode: "because I said so",
      } as never)
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  // --- (h) legalRecordRefs must resolve via the Finance-Legal service -----

  it("rejects legalRecordRefs containing a nonexistent/foreign obligation id", async () => {
    await expect(
      createLegalIssueDossier(founderCtx, {
        ...draft,
        projectId: secondProjectId,
        legalRecordRefs: [{ recordType: "OBLIGATION", recordId: "999999999999999999" }],
      } as never)
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  it("rejects legalRecordRefs referencing an obligation that belongs to a different workspace", async () => {
    const foreignWs = await createSecondWorkspace();
    const foreignFounderCtx = makeTestTenantContext({
      workspaceId: foreignWs.workspaceId,
      userId: "foreign-founder",
      membershipRole: "founder",
      isAiAgent: false,
    });
    // Seed obligation trong workspace CHÍNH (đã có bearer token thật), rồi
    // thử tham chiếu nó từ workspace KHÁC (foreignFounderCtx, với project
    // hợp lệ CỦA workspace đó) — obligation không resolve được qua
    // getObligationService cho workspace đó nên bị reject bằng
    // invalid_argument (tham chiếu sai trong input, không phải lỗi truy cập
    // resource đang thao tác).
    await expect(
      createLegalIssueDossier(foreignFounderCtx, {
        ...draft,
        projectId: foreignWs.projectId,
        legalRecordRefs: [{ recordType: "OBLIGATION", recordId: obligationId }],
      } as never)
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  // --- (i) applicabilityStatus explicit UNKNOWN/ESCALATED, never null -----

  it("defaults applicabilityStatus to UNKNOWN when not provided", async () => {
    const created = await createLegalIssueDossier(founderCtx, {
      projectId: secondProjectId,
      issueCategory: "OTHER",
      redactedQuestion: "Do we need a new NDA template for contractors?",
      reasonCode: "ISSUE_RAISED",
    } as never);
    expect(created.applicabilityStatus).toBe("UNKNOWN");
    expect(created.applicabilityStatus).not.toBeNull();
    expect(created.applicabilityStatus).not.toBeUndefined();
  });

  it("can explicitly set applicabilityStatus to ESCALATED when it cannot be determined", async () => {
    const created = await createLegalIssueDossier(founderCtx, {
      projectId: secondProjectId,
      issueCategory: "REGULATORY_QUESTION",
      applicabilityStatus: "ESCALATED",
      redactedQuestion: "Does the new export control rule apply to our SaaS product?",
      reasonCode: "ESCALATED",
    } as never);
    expect(created.applicabilityStatus).toBe("ESCALATED");
  });

  it("rejects an applicabilityStatus value outside the fixed enum", async () => {
    await expect(
      createLegalIssueDossier(founderCtx, {
        ...draft,
        projectId: secondProjectId,
        applicabilityStatus: "PROBABLY",
      } as never)
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
    const created = await createLegalIssueDossierEndpoint({
      workspaceId,
      authorization: founderBearerToken,
      projectId: secondProjectId,
      issueCategory: draft.issueCategory,
      legalRecordRefs: [{ recordType: "OBLIGATION", recordId: obligationId }],
      applicabilityStatus: draft.applicabilityStatus,
      jurisdiction: draft.jurisdiction,
      redactedQuestion: draft.redactedQuestion,
      reasonCode: draft.reasonCode,
    });
    expect(created.revision).toBe(1);
    expect(created.applicabilityStatus).toBe("UNKNOWN");

    const appended = await appendLegalIssueRevisionEndpoint({
      id: created.dossierId,
      workspaceId,
      authorization: founderBearerToken,
      expectedVersion: 1,
      issueCategory: "REGULATORY_QUESTION",
      redactedQuestion: "Follow-up: does the filing deadline extend to Q2?",
      applicabilityStatus: "ESCALATED",
      reasonCode: "APPLICABILITY_UPDATED",
    });
    expect(appended.revision).toBe(2);
    expect(appended.applicabilityStatus).toBe("ESCALATED");
  });
});
