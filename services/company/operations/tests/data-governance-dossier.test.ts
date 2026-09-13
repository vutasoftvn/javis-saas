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
  createDataGovernanceDossier,
  appendDataGovernanceRevision,
  readDataGovernanceSnapshot,
} from "../services/data-governance-dossier.service";
import {
  createDataGovernanceDossierEndpoint,
  appendDataGovernanceRevisionEndpoint,
  readDataGovernanceSnapshotEndpoint,
} from "../handlers/data-governance-dossier.handler";
import { mintCompanyDelegation } from "../../shared/auth/cosa-delegation.service";

/**
 * Tạo project thứ hai TRONG CÙNG workspace (khác `createSecondWorkspace`, vốn
 * tạo workspace khác hẳn). Dùng để test cross-project isolation trong cùng 1
 * tenant.
 */
async function createSecondProjectInWorkspace(workspaceId: string): Promise<string> {
  const projectId = generateSnowflake();
  await db.execute(sql`
    INSERT INTO strategy.projects (id, workspace_id, title, status, lifecycle_stage)
    VALUES (${projectId}, ${BigInt(workspaceId)}, 'Second Project', 'ACTIVE', 'P0_DISCOVERY')
  `);
  return projectId.toString();
}

describe("Data Governance Dossier Service", () => {
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
    assets: [
      { assetId: "asset-catalog-ref-001", classification: "INTERNAL" as const, qualityStatus: "VALIDATED" as const },
    ],
    sourceRefs: [{ sourceRef: "catalog-scan-2026-09-12", classification: "INTERNAL" }],
    reasonCode: "ASSET_CATALOGED" as const,
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

    const created = await createDataGovernanceDossier(founderCtx, {
      projectId,
      assets: draft.assets,
      sourceRefs: draft.sourceRefs,
      reasonCode: draft.reasonCode,
    });
    dossierId = created.dossierId;
  });

  // --- (a) field-sample / raw-value rejection -----------------------------

  it("rejects a payload with an unknown field-sample-shaped field with invalid_argument", async () => {
    await expect(
      createDataGovernanceDossier(founderCtx, {
        ...draft,
        projectId: secondProjectId,
        fieldSample: "PII",
      } as never)
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  it("rejects an asset entry that carries a raw-value-shaped delimited row instead of a classification label", async () => {
    await expect(
      createDataGovernanceDossier(founderCtx, {
        ...draft,
        projectId: secondProjectId,
        sourceRefs: [{ sourceRef: "john,doe,42,new-york,555-1234", classification: "INTERNAL" }],
      } as never)
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  // --- (b) embedding vector shape rejection -------------------------------

  it("rejects an embedding-vector-shaped array (all-numeric array) anywhere in the payload", async () => {
    await expect(
      createDataGovernanceDossier(founderCtx, {
        ...draft,
        projectId: secondProjectId,
        assets: [
          {
            assetId: "asset-002",
            classification: "INTERNAL",
            qualityStatus: "VALIDATED",
            embedding: [0.123, 0.456, 0.789, 0.111],
          },
        ],
      } as never)
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  // --- (c) raw file URI rejection ------------------------------------------

  it("rejects a raw-file-URI-shaped string (s3://)", async () => {
    await expect(
      createDataGovernanceDossier(founderCtx, {
        ...draft,
        projectId: secondProjectId,
        sourceRefs: [{ sourceRef: "s3://prod-data-lake/customers/export.csv", classification: "INTERNAL" }],
      } as never)
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  it("rejects a raw-file-URI-shaped string (absolute unix path)", async () => {
    await expect(
      createDataGovernanceDossier(founderCtx, {
        ...draft,
        projectId: secondProjectId,
        sourceRefs: [{ sourceRef: "/Users/founder/exports/customers.csv", classification: "INTERNAL" }],
      } as never)
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  it("rejects a raw-file-URI-shaped string (generic URL)", async () => {
    await expect(
      createDataGovernanceDossier(founderCtx, {
        ...draft,
        projectId: secondProjectId,
        sourceRefs: [{ sourceRef: "https://internal.example.com/exports/customers.csv", classification: "INTERNAL" }],
      } as never)
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  // --- (d) API-credential-shaped string rejection ---------------------------

  it("rejects a credential-shaped string (API key)", async () => {
    await expect(
      createDataGovernanceDossier(founderCtx, {
        ...draft,
        projectId: secondProjectId,
        sourceRefs: [{ sourceRef: "sk-abcdefghijklmnopqrstuvwx1234567890", classification: "INTERNAL" }],
      } as never)
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  it("rejects a credential-shaped string (Bearer token)", async () => {
    await expect(
      createDataGovernanceDossier(founderCtx, {
        ...draft,
        projectId: secondProjectId,
        sourceRefs: [{ sourceRef: "Bearer abcdefghijklmnopqrstuvwxyz012345", classification: "INTERNAL" }],
      } as never)
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  // --- (e) foreign-workspace read is denied --------------------------------

  it("rejects a foreign-workspace read with permission_denied", async () => {
    await expect(readDataGovernanceSnapshot(foreignCtx, projectId)).rejects.toMatchObject({
      code: "permission_denied",
    });
  });

  // --- (f) cross-project isolation within the SAME workspace ----------------

  it("rejects a same-workspace-different-project read (cross-project isolation)", async () => {
    await expect(readDataGovernanceSnapshot(founderCtx, secondProjectId)).rejects.toMatchObject({
      code: "not_found",
    });
  });

  // --- (g) agent/COSA-delegation context can never create or append --------

  it("agent context can never create a dossier", async () => {
    await expect(
      createDataGovernanceDossier(agentCtx, { ...draft, projectId: secondProjectId } as never)
    ).rejects.toMatchObject({ code: "permission_denied" });
  });

  it("agent context can never append a revision", async () => {
    await expect(
      appendDataGovernanceRevision(agentCtx, dossierId, 1, { ...draft, reasonCode: "CLASSIFICATION_UPDATED" } as never)
    ).rejects.toMatchObject({ code: "permission_denied" });
  });

  it("an agent context (non-founder) can still read the redacted snapshot", async () => {
    const snapshot = await readDataGovernanceSnapshot(agentCtx, projectId);
    expect(snapshot.dossierId).toBe(dossierId);
    expect(snapshot).not.toHaveProperty("fieldSample");
  });

  // Mirror security-posture.test.ts's exact test — prove the Agent Platform
  // (apps/cosa) cannot reach these endpoints at all: its only credential
  // towards services/company is a COSA_COMPANY_DELEGATION_SECRET-signed
  // delegation token, never a JWT_SECRET-signed local session token.
  it("rejects a COSA-delegation-signed token before any TenantContext is built", async () => {
    const delegationToken = mintCompanyDelegation({
      sub: "cosa-worker-1",
      workspace_id: founderCtx.workspaceId,
      run_id: "run-1",
      capability_ids: ["operations.data_governance.append"],
    });

    await expect(
      createDataGovernanceDossierEndpoint({
        authorization: `Bearer ${delegationToken}`,
        workspaceId: founderCtx.workspaceId,
        projectId: secondProjectId,
        assets: draft.assets,
        sourceRefs: draft.sourceRefs,
        reasonCode: draft.reasonCode,
      })
    ).rejects.toMatchObject({ code: "unauthenticated" });

    await expect(
      appendDataGovernanceRevisionEndpoint({
        id: dossierId,
        authorization: `Bearer ${delegationToken}`,
        workspaceId: founderCtx.workspaceId,
        expectedVersion: 1,
        assets: draft.assets,
        sourceRefs: draft.sourceRefs,
        reasonCode: "CLASSIFICATION_UPDATED",
      })
    ).rejects.toMatchObject({ code: "unauthenticated" });
  });

  it("rejects a COSA-delegation-signed token on the read endpoint the same way", async () => {
    const delegationToken = mintCompanyDelegation({
      sub: "cosa-worker-1",
      workspace_id: founderCtx.workspaceId,
      run_id: "run-1",
      capability_ids: ["data_governance.read"],
    });

    await expect(
      readDataGovernanceSnapshotEndpoint({
        projectId,
        authorization: `Bearer ${delegationToken}`,
        workspaceId: founderCtx.workspaceId,
      })
    ).rejects.toMatchObject({ code: "unauthenticated" });
  });

  // --- (h) one dossier per project ------------------------------------------

  it("rejects a second dossier created for the same project as alreadyExists", async () => {
    await expect(
      createDataGovernanceDossier(founderCtx, { ...draft, projectId } as never)
    ).rejects.toMatchObject({ code: "already_exists" });
  });

  // --- (i) CAS revision versioning -------------------------------------------

  it("creates a dossier as revision 1 in DRAFT status", async () => {
    expect(dossierId).toBeTruthy();
    const snapshot = await readDataGovernanceSnapshot(founderCtx, projectId);
    expect(snapshot.dossierId).toBe(dossierId);
    expect(snapshot.revision).toBe(1);
    expect(snapshot.status).toBe("DRAFT");
    expect(snapshot.assets).toEqual([
      { assetId: "asset-catalog-ref-001", classification: "INTERNAL", qualityStatus: "VALIDATED" },
    ]);
  });

  it("a human member can append a DRAFT revision with CAS, and stale CAS is rejected", async () => {
    const appended = await appendDataGovernanceRevision(memberCtx, dossierId, 1, {
      assets: [{ assetId: "asset-catalog-ref-001", classification: "CONFIDENTIAL", qualityStatus: "FLAGGED" }],
      sourceRefs: draft.sourceRefs,
      reasonCode: "CLASSIFICATION_UPDATED",
    });
    expect(appended.revision).toBe(2);
    expect(appended.status).toBe("DRAFT");
    expect(appended.assets).toEqual([
      { assetId: "asset-catalog-ref-001", classification: "CONFIDENTIAL", qualityStatus: "FLAGGED" },
    ]);

    await expect(
      appendDataGovernanceRevision(memberCtx, dossierId, 1, {
        ...draft,
        reasonCode: "SOURCE_REF_UPDATED",
      })
    ).rejects.toMatchObject({ code: "aborted" });
  });

  it("only a human founder can confirm a data governance dossier revision", async () => {
    await expect(
      appendDataGovernanceRevision(memberCtx, dossierId, 1, {
        ...draft,
        status: "CONFIRMED",
        reasonCode: "FOUNDER_REVIEW",
      })
    ).rejects.toMatchObject({ code: "permission_denied" });

    const confirmed = await appendDataGovernanceRevision(founderCtx, dossierId, 1, {
      ...draft,
      status: "CONFIRMED",
      reasonCode: "FOUNDER_REVIEW",
    });
    expect(confirmed.status).toBe("CONFIRMED");
    expect(confirmed.revision).toBe(2);

    const snapshot = await readDataGovernanceSnapshot(founderCtx, projectId);
    expect(snapshot.status).toBe("CONFIRMED");
    expect(snapshot.revision).toBe(2);
  });

  // Full-replace (not merge) append semantics — mirror established pattern
  // from sibling dossiers (progress.md lesson #10): append without assets
  // drops the prior asset list, not silently carried over.
  it("documents full-replace (not merge) append semantics: an append without assets drops the prior asset list", async () => {
    const appended = await appendDataGovernanceRevision(founderCtx, dossierId, 1, {
      sourceRefs: draft.sourceRefs,
      reasonCode: "SOURCE_REF_UPDATED",
    } as never);

    expect(appended.revision).toBe(2);
    expect(appended.assets).toEqual([]);

    const snapshot = await readDataGovernanceSnapshot(founderCtx, projectId);
    expect(snapshot.assets).toEqual([]);
  });

  it("rejects append to a dossier that does not exist in this workspace", async () => {
    await expect(
      appendDataGovernanceRevision(founderCtx, "999999999999999999", 1, {
        ...draft,
        reasonCode: "SOURCE_REF_UPDATED",
      })
    ).rejects.toMatchObject({ code: "not_found" });
  });

  it("rejects create when projectId is missing", async () => {
    await expect(
      createDataGovernanceDossier(founderCtx, { ...draft, projectId: "" } as never)
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  it("rejects create when reasonCode is not one of the fixed allowed values", async () => {
    await expect(
      createDataGovernanceDossier(founderCtx, {
        ...draft,
        projectId: secondProjectId,
        reasonCode: "because I said so",
      } as never)
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  it("rejects an asset entry with a classification outside the fixed allowlist", async () => {
    await expect(
      createDataGovernanceDossier(founderCtx, {
        ...draft,
        projectId: secondProjectId,
        assets: [{ assetId: "asset-x", classification: "TOP_SECRET", qualityStatus: "VALIDATED" }],
      } as never)
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  it("rejects an asset entry with a qualityStatus outside the fixed allowlist", async () => {
    await expect(
      createDataGovernanceDossier(founderCtx, {
        ...draft,
        projectId: secondProjectId,
        assets: [{ assetId: "asset-x", classification: "INTERNAL", qualityStatus: "PROBABLY_FINE" }],
      } as never)
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  // --- (j) classification/qualityStatus MISSING/UNKNOWN, never null --------

  it("defaults an asset's classification to MISSING and qualityStatus to UNKNOWN when not provided", async () => {
    const created = await createDataGovernanceDossier(founderCtx, {
      projectId: secondProjectId,
      assets: [{ assetId: "asset-unclassified" }],
      reasonCode: "ASSET_CATALOGED",
    } as never);
    expect(created.assets).toEqual([
      { assetId: "asset-unclassified", classification: "MISSING", qualityStatus: "UNKNOWN" },
    ]);
    expect(created.assets[0].classification).not.toBeNull();
    expect(created.assets[0].qualityStatus).not.toBeNull();
  });

  it("can explicitly set classification/qualityStatus to MISSING/UNKNOWN", async () => {
    const created = await createDataGovernanceDossier(founderCtx, {
      projectId: secondProjectId,
      assets: [{ assetId: "asset-y", classification: "MISSING", qualityStatus: "UNKNOWN" }],
      reasonCode: "ASSET_CATALOGED",
    } as never);
    expect(created.assets[0].classification).toBe("MISSING");
    expect(created.assets[0].qualityStatus).toBe("UNKNOWN");
  });

  // --- (k) real handler/endpoint mapping (not just service function) -------
  //
  // CRITICAL regression test (progress.md lesson #7): the handler must
  // destructure ONLY the fields the service's allowlist expects — never
  // forward the raw Encore `params` object (which includes Header-bound
  // `workspaceId`/`authorization`). This test calls the actual EXPORTED
  // endpoint functions with a real, valid founder bearer token.

  it("the real create+append endpoints succeed with a valid founder token and real business fields (no Header-field leakage)", async () => {
    const created = await createDataGovernanceDossierEndpoint({
      workspaceId,
      authorization: founderBearerToken,
      projectId: secondProjectId,
      assets: draft.assets,
      sourceRefs: draft.sourceRefs,
      reasonCode: draft.reasonCode,
    });
    expect(created.revision).toBe(1);
    expect(created.assets).toEqual(draft.assets);

    const appended = await appendDataGovernanceRevisionEndpoint({
      id: created.dossierId,
      workspaceId,
      authorization: founderBearerToken,
      expectedVersion: 1,
      assets: [{ assetId: "asset-catalog-ref-001", classification: "RESTRICTED", qualityStatus: "FLAGGED" }],
      sourceRefs: draft.sourceRefs,
      reasonCode: "CLASSIFICATION_UPDATED",
    });
    expect(appended.revision).toBe(2);
    expect(appended.assets[0].classification).toBe("RESTRICTED");
  });
});
