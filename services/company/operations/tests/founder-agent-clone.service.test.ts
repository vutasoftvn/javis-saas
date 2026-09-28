import { describe, it, expect, beforeEach } from "vitest";
import { and, eq } from "drizzle-orm";
import { db } from "../models/db";
import { createTestWorkspaceWithMember, makeTestTenantContext } from "./_helpers";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import type { TenantContext } from "../../shared/types/tenant_context";
import { eventOutbox } from "../../shared/db/schema/integration";
import {
  coreAgentCapabilityGrants,
  identityWorkforceMembers,
} from "../../shared/db/schema/identity";
import {
  commandFounderAsset,
  handleAssetStatusCallback,
  type AgentPublishManifest,
  type AssetOperation,
  type AssetRef,
} from "../services/founder-asset-authoring.service";
import {
  createWorkspaceAgent,
  deployAgentToProject,
  getProjectDeploymentAuthority,
  pauseProjectDeployment,
  WORKSPACE_CLONE_ORIGIN,
} from "../services/founder-asset-deployment.service";
import { AGENT_PROFILE_GRANTED_CAPABILITIES } from "../services/agent-profile-grants.service";
import { createWorkspaceCloneAgentApi } from "../handlers/founder-asset-deployment.handler";
import {
  AGENT_PROFILE_SPEC_HASH,
  AGENT_PROFILE_SPEC_ID,
  AGENT_PROFILE_SPEC_VERSION,
} from "../services/ai-member.service";

// C1 — phía company của executor CLONE/PUBLISH cho AGENT
// (docs/superpowers/specs/2026-09-27-agent-clone-executor-design.md §4-§5).
// Callback dưới đây mang đúng payload mà apps/cosa gửi (FounderAssetStatusCallbackClient);
// phía cosa của cùng luồng: tests/apps/cosa/worker/test_agent_clone_executor_e2e.py.

const DROPPED = "operations.task.advance";

describe("founder agent clone (C1) — publish receipt, workspace agent, grants", () => {
  let ctx: TenantContext;
  let projectId: string;
  let workspaceId: string;
  let bearerToken: string;
  let seq = 0;

  beforeEach(async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    workspaceId = ws.workspaceId;
    projectId = ws.projectId;
    bearerToken = ws.bearerToken;
    const founderMemberId = generateSnowflake();
    await db.insert(identityWorkforceMembers).values({
      id: founderMemberId,
      workspaceId: BigInt(ws.workspaceId),
      memberType: "HUMAN",
      humanUserId: BigInt(ws.userId),
      roleTitle: "Founder",
      status: "active",
    });
    ctx = makeTestTenantContext({
      workspaceId: ws.workspaceId,
      userId: ws.userId,
      workforceMemberId: founderMemberId.toString(),
      membershipRole: "founder",
    });
  });

  async function command(operation: AssetOperation, assetRef: AssetRef, metadata = {}) {
    seq += 1;
    return commandFounderAsset(ctx, {
      projectId,
      assetKind: "AGENT",
      operation,
      assetRef,
      idempotencyKey: `c1-${operation}-${seq}-${generateSnowflake()}`,
      reason: "Founder tạo agent vận hành riêng",
      metadata,
    });
  }

  function manifest(capabilityRefs: string[]): AgentPublishManifest {
    return {
      originProfileKey: "operations",
      originSpec: {
        id: AGENT_PROFILE_SPEC_ID.operations,
        version: AGENT_PROFILE_SPEC_VERSION.operations,
        definitionHash: AGENT_PROFILE_SPEC_HASH.operations,
      },
      capabilityRefs,
      displayName: "Vận hành gọn",
    };
  }

  /** CLONE → EDIT_DRAFT → EVALUATE → PUBLISH, mỗi lệnh kèm callback SUCCESS của worker. */
  async function publishClone(capabilityRefs: string[]): Promise<AssetRef> {
    const clone = await command("CLONE", { assetId: AGENT_PROFILE_SPEC_ID.operations }, {
      name: "Vận hành Sao Mai",
    });
    // Payload outbox là đúng thứ consumer founder_asset_events.py đọc.
    const [outbox] = await db
      .select()
      .from(eventOutbox)
      .where(eq(eventOutbox.aggregateId, clone.commandId));
    const envelope = outbox.envelope as Record<string, any>;
    expect(envelope.eventType).toBe("founder.asset.commanded.v1");
    expect(envelope.payload).toMatchObject({
      commandId: clone.commandId,
      workspaceId,
      projectId,
      assetKind: "AGENT",
      operation: "CLONE",
      assetRef: { assetId: AGENT_PROFILE_SPEC_ID.operations },
      metadata: { name: "Vận hành Sao Mai" },
    });

    const assetId = `custom.operations.${clone.commandId}`;
    const draftRef = { assetId, version: "0.1.0", definitionHash: "sha256:draft" };
    await handleAssetStatusCallback({
      commandId: clone.commandId,
      workspaceId,
      projectId,
      assetKind: "AGENT",
      operation: "CLONE",
      status: "SUCCESS",
      assetRef: draftRef,
    });

    const edited = { ...draftRef, definitionHash: `sha256:edited-${clone.commandId}` };
    const edit = await command("EDIT_DRAFT", draftRef, {
      content: { name: "Vận hành gọn", instructions_addendum: "Ưu tiên việc tuần này." },
    });
    await handleAssetStatusCallback({
      commandId: edit.commandId,
      workspaceId,
      projectId,
      assetKind: "AGENT",
      operation: "EDIT_DRAFT",
      status: "SUCCESS",
      assetRef: edited,
    });

    const evaluate = await command("EVALUATE", edited);
    await handleAssetStatusCallback({
      commandId: evaluate.commandId,
      workspaceId,
      projectId,
      assetKind: "AGENT",
      operation: "EVALUATE",
      status: "SUCCESS",
      assetRef: edited,
      evaluationSummary: { status: "PASS" },
    });

    const publish = await command("PUBLISH", edited);
    await handleAssetStatusCallback({
      commandId: publish.commandId,
      workspaceId,
      projectId,
      assetKind: "AGENT",
      operation: "PUBLISH",
      status: "SUCCESS",
      assetRef: edited,
      agentManifest: manifest(capabilityRefs),
    });
    return edited;
  }

  async function activeGrants(memberId: string): Promise<string[]> {
    const rows = await db
      .select({ capabilityId: coreAgentCapabilityGrants.capabilityId })
      .from(coreAgentCapabilityGrants)
      .where(
        and(
          eq(coreAgentCapabilityGrants.workspaceId, BigInt(workspaceId)),
          eq(coreAgentCapabilityGrants.agentWorkforceMemberId, BigInt(memberId)),
          eq(coreAgentCapabilityGrants.projectId, BigInt(projectId)),
          eq(coreAgentCapabilityGrants.status, "ACTIVE")
        )
      );
    return rows.map((r) => r.capabilityId).sort();
  }

  it("workspace agent + deploy of a published clone grants origin profile ∩ narrowed capabilities", async () => {
    const kept = AGENT_PROFILE_GRANTED_CAPABILITIES.operations.filter((c) => c !== DROPPED);
    // Manifest liệt kê thêm capability ngoài bảng grant của profile gốc: không bao giờ được cấp.
    const ref = await publishClone([...kept, "finance.transaction.record"]);

    const agent = await createWorkspaceAgent(ctx, {
      agentAssetId: ref.assetId,
      agentAssetVersion: ref.version!,
      agentDefinitionHash: ref.definitionHash!,
      originKind: WORKSPACE_CLONE_ORIGIN,
      reason: "Tạo agent workspace từ clone đã publish",
    });
    expect(agent.originKind).toBe(WORKSPACE_CLONE_ORIGIN);
    expect(agent.workforceMemberId).not.toBe(ctx.workforceMemberId);
    const [member] = await db
      .select()
      .from(identityWorkforceMembers)
      .where(eq(identityWorkforceMembers.id, BigInt(agent.workforceMemberId)));
    expect(member.memberType).toBe("AI_AGENT");
    expect(member.agentSpecId).toBe(ref.assetId);
    expect(member.roleTitle).toBe("Vận hành gọn");

    const deployment = await deployAgentToProject(ctx, {
      projectId,
      workspaceAgentId: agent.id,
      reason: "Deploy agent riêng vào Project",
    });
    const granted = await activeGrants(agent.workforceMemberId);
    expect(granted.length).toBeGreaterThan(0);
    expect(granted).not.toContain(DROPPED);
    expect(granted).not.toContain("finance.transaction.record");
    for (const cap of granted) {
      expect(kept).toContain(cap);
    }

    const authority = await getProjectDeploymentAuthority(ctx, {
      projectId,
      projectAgentDeploymentId: deployment.id,
    });
    expect(authority.state).toBe("ACTIVE");
    expect(authority.workforceMemberId).toBe(agent.workforceMemberId);
    expect(authority.agentSpec).toEqual({
      id: ref.assetId,
      version: ref.version,
      definitionHash: ref.definitionHash,
    });

    await pauseProjectDeployment(ctx, {
      deploymentId: deployment.id,
      kind: "AGENT",
      expectedVersion: deployment.version,
      reason: "Tạm dừng agent riêng",
    });
    expect(await activeGrants(agent.workforceMemberId)).toEqual([]);
  });

  it("refuses a workspace clone agent without an exact publish receipt", async () => {
    const ref = await publishClone([...AGENT_PROFILE_GRANTED_CAPABILITIES.operations]);

    await expect(
      createWorkspaceAgent(ctx, {
        agentAssetId: ref.assetId,
        agentAssetVersion: ref.version!,
        agentDefinitionHash: "sha256:not-the-published-one",
        originKind: WORKSPACE_CLONE_ORIGIN,
        reason: "Pin sai hash",
      })
    ).rejects.toMatchObject({ code: "invalid_argument" });

    await expect(
      createWorkspaceAgent(ctx, {
        agentAssetId: "custom.operations.never-published",
        agentAssetVersion: "0.1.0",
        agentDefinitionHash: "sha256:x",
        originKind: WORKSPACE_CLONE_ORIGIN,
        reason: "Chưa từng publish",
      })
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  it("a published clone pin cannot bypass the clone path with another originKind", async () => {
    const ref = await publishClone([...AGENT_PROFILE_GRANTED_CAPABILITIES.operations]);
    const agent = await createWorkspaceAgent(ctx, {
      agentAssetId: ref.assetId,
      agentAssetVersion: ref.version!,
      agentDefinitionHash: ref.definitionHash!,
      workforceMemberId: ctx.workforceMemberId,
      originKind: "BUILTIN",
      reason: "Thử lách originKind và dùng member của founder",
    });
    expect(agent.originKind).toBe(WORKSPACE_CLONE_ORIGIN);
    expect(agent.workforceMemberId).not.toBe(ctx.workforceMemberId);
  });

  it("rejects a malformed agentManifest in the publish callback", async () => {
    const ref = { assetId: "custom.operations.bad", version: "0.1.0", definitionHash: "sha256:bad" };
    const publish = await command("PUBLISH", ref);
    await expect(
      handleAssetStatusCallback({
        commandId: publish.commandId,
        workspaceId,
        projectId,
        assetKind: "AGENT",
        operation: "PUBLISH",
        status: "SUCCESS",
        assetRef: ref,
        agentManifest: { originProfileKey: "operations" } as unknown as AgentPublishManifest,
      })
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  it("POST /operations/founder/assets/workspace-agents creates the clone agent for C2", async () => {
    const ref = await publishClone([...AGENT_PROFILE_GRANTED_CAPABILITIES.operations]);
    const agent = await createWorkspaceCloneAgentApi({
      authorization: bearerToken,
      workspaceId,
      agentAssetId: ref.assetId,
      agentAssetVersion: ref.version!,
      agentDefinitionHash: ref.definitionHash!,
      idempotencyKey: "c1-handler",
    });
    expect(agent.originKind).toBe(WORKSPACE_CLONE_ORIGIN);
    expect(agent.agentAssetId).toBe(ref.assetId);

    await expect(
      createWorkspaceCloneAgentApi({
        authorization: bearerToken,
        workspaceId,
        agentAssetId: "custom.operations.unpublished",
        agentAssetVersion: "0.1.0",
        agentDefinitionHash: "sha256:x",
      })
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });
});
