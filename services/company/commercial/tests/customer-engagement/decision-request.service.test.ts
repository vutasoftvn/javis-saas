import { describe, expect, it } from "vitest";
import { sql, eq } from "drizzle-orm";
import { createTestSession } from "../../../identity/tests/helpers/test-session";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import { db, schema } from "../../models/db";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import {
  seedDecisionAuthority,
  grantAuthorityCapability,
  ApprovalPolicy,
} from "../../services/customer-engagement/decision-authority.service";
import {
  createDecisionRequest,
  submitDecisionRequest,
  recordApproval,
  executeDecisionRequest,
} from "../../services/customer-engagement/decision-request.service";

async function ws(name: string) {
  const u = await createTestSession({ email: `${name}-${Date.now()}-${Math.random().toString(36).slice(2)}@ex.com`, displayName: name });
  const base = await requireWorkspaceAccess(`Bearer ${u.accessToken}`, u.workspaceId);
  const ctx = {
    ...base,
    workforceMemberId: String(generateSnowflake()),
    permissions: Object.freeze([...(base.permissions || []), "engagement.decision_request.review", "engagement.decision_request.decide"]),
  };
  return { ctx, workspaceId: u.workspaceId };
}

describe("decision-request.service", () => {
  it("createDecisionRequest fails while authority status='pending_binding'", async () => {
    const { ctx, workspaceId } = await ws("dr-pending-auth");
    const policy: ApprovalPolicy = {
      required_capabilities: ["sales_manager"],
      distinct_approvers: 1,
      requester_must_differ: true,
      requester_cannot_execute: true,
    };

    await seedDecisionAuthority(
      {
        workspaceId,
        authorityKey: "test.discount",
        decisionKind: "discount",
        approvalPolicy: policy,
      },
      ctx,
    );

    await expect(
      createDecisionRequest(
        {
          requestType: "discount",
          authorityKey: "test.discount",
          options: [],
        },
        ctx,
      ),
    ).rejects.toThrow(/not enabled/i);
  });

  it("createDecisionRequest succeeds after authority becomes enabled", async () => {
    const { ctx, workspaceId } = await ws("dr-enabled-auth");
    const policy: ApprovalPolicy = {
      required_capabilities: ["sales_manager"],
      distinct_approvers: 1,
      requester_must_differ: true,
      requester_cannot_execute: true,
    };

    await seedDecisionAuthority(
      {
        workspaceId,
        authorityKey: "test.discount2",
        decisionKind: "discount",
        approvalPolicy: policy,
      },
      ctx,
    );

    const memberId = String(generateSnowflake());
    await grantAuthorityCapability(
      {
        workspaceId,
        authorityKey: "test.discount2",
        workforceMemberId: memberId,
        capability: "sales_manager",
      },
      ctx,
    );

    const dr = await createDecisionRequest(
      {
        requestType: "discount",
        authorityKey: "test.discount2",
        options: [],
      },
      ctx,
    );

    expect(dr.status).toBe("draft");
    expect(dr.authorityKey).toBe("test.discount2");
  });

  it("submitDecisionRequest fails without policySnapshotRef", async () => {
    const { ctx, workspaceId } = await ws("dr-submit-no-ref");
    const policy: ApprovalPolicy = {
      required_capabilities: ["sales_manager"],
      distinct_approvers: 1,
      requester_must_differ: true,
      requester_cannot_execute: true,
    };

    await seedDecisionAuthority(
      {
        workspaceId,
        authorityKey: "test.discount3",
        decisionKind: "discount",
        approvalPolicy: policy,
      },
      ctx,
    );

    const memberId = String(generateSnowflake());
    await grantAuthorityCapability(
      {
        workspaceId,
        authorityKey: "test.discount3",
        workforceMemberId: memberId,
        capability: "sales_manager",
      },
      ctx,
    );

    const dr = await createDecisionRequest(
      {
        requestType: "discount",
        authorityKey: "test.discount3",
        options: [],
      },
      ctx,
    );

    await expect(
      submitDecisionRequest(dr.id, { policySnapshotRef: "" }, ctx),
    ).rejects.toThrow(/required/i);
  });

  it("recordApproval by requester throws permissionDenied", async () => {
    const { ctx, workspaceId } = await ws("dr-requester-approve");
    const policy: ApprovalPolicy = {
      required_capabilities: ["sales_manager"],
      distinct_approvers: 1,
      requester_must_differ: true,
      requester_cannot_execute: true,
    };

    await seedDecisionAuthority(
      {
        workspaceId,
        authorityKey: "test.discount4",
        decisionKind: "discount",
        approvalPolicy: policy,
      },
      ctx,
    );

    const memberId = ctx.workforceMemberId!;
    await grantAuthorityCapability(
      {
        workspaceId,
        authorityKey: "test.discount4",
        workforceMemberId: memberId,
        capability: "sales_manager",
      },
      ctx,
    );

    const dr = await createDecisionRequest(
      {
        requestType: "discount",
        authorityKey: "test.discount4",
        options: [],
      },
      ctx,
    );

    const ctxWithPermission = { ...ctx, permissions: Object.freeze([...(ctx.permissions || []), "engagement.decision_request.decide"]) };

    await expect(
      recordApproval(dr.id, { decision: "approve" }, ctxWithPermission),
    ).rejects.toThrow(/requester cannot approve/i);
  });

  it("recordApproval by member with NO grant throws permissionDenied", async () => {
    const { ctx: requesterCtx, workspaceId } = await ws("dr-no-grant");
    const approverCtx = {
      ...requesterCtx,
      workforceMemberId: String(generateSnowflake()),
    };

    const policy: ApprovalPolicy = {
      required_capabilities: ["sales_manager"],
      distinct_approvers: 1,
      requester_must_differ: true,
      requester_cannot_execute: true,
    };

    await seedDecisionAuthority(
      {
        workspaceId,
        authorityKey: "test.discount5",
        decisionKind: "discount",
        approvalPolicy: policy,
      },
      requesterCtx,
    );

    const memberId = String(generateSnowflake());
    await grantAuthorityCapability(
      {
        workspaceId,
        authorityKey: "test.discount5",
        workforceMemberId: memberId,
        capability: "sales_manager",
      },
      requesterCtx,
    );

    const dr = await createDecisionRequest(
      {
        requestType: "discount",
        authorityKey: "test.discount5",
        options: [],
      },
      requesterCtx,
    );

    await submitDecisionRequest(dr.id, { policySnapshotRef: "policy_v1" }, requesterCtx);

    const ctxWithPermission = { ...approverCtx, permissions: Object.freeze([...(approverCtx.permissions || []), "engagement.decision_request.decide"]) };

    await expect(
      recordApproval(dr.id, { decision: "approve" }, ctxWithPermission),
    ).rejects.toThrow(/no active grant/i);
  });

  it("two-approver policy: 1 approve keeps under_review, execute blocked", async () => {
    const { ctx: requesterCtx, workspaceId } = await ws("dr-two-approver");

    const policy: ApprovalPolicy = {
      required_capabilities: ["sales_director", "finance_controller"],
      distinct_approvers: 2,
      requester_must_differ: true,
      requester_cannot_execute: true,
    };

    await seedDecisionAuthority(
      {
        workspaceId,
        authorityKey: "commercial.pricing.exception",
        decisionKind: "pricing_exception",
        approvalPolicy: policy,
      },
      requesterCtx,
    );

    const approver1Ctx = { ...requesterCtx, workforceMemberId: String(generateSnowflake()) };
    const approver2Ctx = { ...requesterCtx, workforceMemberId: String(generateSnowflake()) };

    await grantAuthorityCapability(
      {
        workspaceId,
        authorityKey: "commercial.pricing.exception",
        workforceMemberId: approver1Ctx.workforceMemberId,
        capability: "sales_director",
      },
      requesterCtx,
    );

    await grantAuthorityCapability(
      {
        workspaceId,
        authorityKey: "commercial.pricing.exception",
        workforceMemberId: approver2Ctx.workforceMemberId,
        capability: "finance_controller",
      },
      requesterCtx,
    );

    const dr = await createDecisionRequest(
      {
        requestType: "pricing_exception",
        authorityKey: "commercial.pricing.exception",
        options: [],
      },
      requesterCtx,
    );

    await submitDecisionRequest(dr.id, { policySnapshotRef: "policy_v1" }, requesterCtx);

    const result1 = await recordApproval(dr.id, { decision: "approve" }, approver1Ctx);

    expect(result1.status).toBe("under_review"); // Not yet approved

    // Try to execute: should fail
    await expect(executeDecisionRequest(dr.id, approver1Ctx)).rejects.toThrow(/not approved/i);

    // Second approver approves
    const result2 = await recordApproval(dr.id, { decision: "approve" }, approver2Ctx);

    expect(result2.status).toBe("approved");
    expect(result2.approvals).toHaveLength(2);
  });

  it("three-approver policy only approved after 3 distinct with all capabilities", async () => {
    const { ctx: requesterCtx, workspaceId } = await ws("dr-three-approver");

    const policy: ApprovalPolicy = {
      required_capabilities: ["commercial_policy_owner", "finance_controller", "workspace_business_owner"],
      distinct_approvers: 3,
      requester_must_differ: true,
      requester_cannot_execute: true,
    };

    await seedDecisionAuthority(
      {
        workspaceId,
        authorityKey: "commercial.pricing.high_risk",
        decisionKind: "pricing_high_risk",
        approvalPolicy: policy,
      },
      requesterCtx,
    );

    const approver1Ctx = { ...requesterCtx, workforceMemberId: String(generateSnowflake()) };
    const approver2Ctx = { ...requesterCtx, workforceMemberId: String(generateSnowflake()) };
    const approver3Ctx = { ...requesterCtx, workforceMemberId: String(generateSnowflake()) };

    await grantAuthorityCapability(
      {
        workspaceId,
        authorityKey: "commercial.pricing.high_risk",
        workforceMemberId: approver1Ctx.workforceMemberId,
        capability: "commercial_policy_owner",
      },
      requesterCtx,
    );

    await grantAuthorityCapability(
      {
        workspaceId,
        authorityKey: "commercial.pricing.high_risk",
        workforceMemberId: approver2Ctx.workforceMemberId,
        capability: "finance_controller",
      },
      requesterCtx,
    );

    await grantAuthorityCapability(
      {
        workspaceId,
        authorityKey: "commercial.pricing.high_risk",
        workforceMemberId: approver3Ctx.workforceMemberId,
        capability: "workspace_business_owner",
      },
      requesterCtx,
    );

    const dr = await createDecisionRequest(
      {
        requestType: "pricing_high_risk",
        authorityKey: "commercial.pricing.high_risk",
        options: [],
      },
      requesterCtx,
    );

    await submitDecisionRequest(dr.id, { policySnapshotRef: "policy_v1" }, requesterCtx);

    const result1 = await recordApproval(dr.id, { decision: "approve" }, approver1Ctx);
    expect(result1.status).toBe("under_review");

    const result2 = await recordApproval(dr.id, { decision: "approve" }, approver2Ctx);
    expect(result2.status).toBe("under_review");

    const result3 = await recordApproval(dr.id, { decision: "approve" }, approver3Ctx);
    expect(result3.status).toBe("approved");
  });

  it("approval_deadline in past at execute marks expired and throws", async () => {
    const { ctx: requesterCtx, workspaceId } = await ws("dr-deadline");
    const approverCtx = { ...requesterCtx, workforceMemberId: String(generateSnowflake()) };

    const policy: ApprovalPolicy = {
      required_capabilities: ["sales_manager"],
      distinct_approvers: 1,
      requester_must_differ: true,
      requester_cannot_execute: true,
    };

    await seedDecisionAuthority(
      {
        workspaceId,
        authorityKey: "test.discount.deadline",
        decisionKind: "discount",
        approvalPolicy: policy,
      },
      requesterCtx,
    );

    await grantAuthorityCapability(
      {
        workspaceId,
        authorityKey: "test.discount.deadline",
        workforceMemberId: approverCtx.workforceMemberId,
        capability: "sales_manager",
      },
      requesterCtx,
    );

    const dr = await createDecisionRequest(
      {
        requestType: "discount",
        authorityKey: "test.discount.deadline",
        options: [],
      },
      requesterCtx,
    );

    // Set deadline in the past
    const pastDate = new Date();
    pastDate.setHours(pastDate.getHours() - 1);
    await db
      .update(schema.engagementDecisionRequests)
      .set({ approvalDeadline: pastDate })
      .where(eq(schema.engagementDecisionRequests.id, BigInt(dr.id)));

    await submitDecisionRequest(dr.id, { policySnapshotRef: "policy_v1" }, requesterCtx);

    await recordApproval(dr.id, { decision: "approve" }, approverCtx);

    // Try to execute: should fail with expired
    await expect(executeDecisionRequest(dr.id, approverCtx)).rejects.toThrow(/expired/i);

    // Check that status is marked expired
    const updated = await db.query.engagementDecisionRequests.findFirst({
      where: eq(schema.engagementDecisionRequests.id, BigInt(dr.id)),
    });
    expect(updated?.status).toBe("expired");
  });

  it("authority disabled after approved blocks execute", async () => {
    const { ctx: requesterCtx, workspaceId } = await ws("dr-disabled-auth");
    const approverCtx = { ...requesterCtx, workforceMemberId: String(generateSnowflake()) };

    const policy: ApprovalPolicy = {
      required_capabilities: ["sales_manager"],
      distinct_approvers: 1,
      requester_must_differ: true,
      requester_cannot_execute: true,
    };

    const auth = await seedDecisionAuthority(
      {
        workspaceId,
        authorityKey: "test.discount.disabled",
        decisionKind: "discount",
        approvalPolicy: policy,
      },
      requesterCtx,
    );

    await grantAuthorityCapability(
      {
        workspaceId,
        authorityKey: "test.discount.disabled",
        workforceMemberId: approverCtx.workforceMemberId,
        capability: "sales_manager",
      },
      requesterCtx,
    );

    const dr = await createDecisionRequest(
      {
        requestType: "discount",
        authorityKey: "test.discount.disabled",
        options: [],
      },
      requesterCtx,
    );

    await submitDecisionRequest(dr.id, { policySnapshotRef: "policy_v1" }, requesterCtx);

    await recordApproval(dr.id, { decision: "approve" }, approverCtx);

    // Disable the authority
    await db
      .update(schema.engagementDecisionAuthorities)
      .set({ status: "pending_binding" })
      .where(eq(schema.engagementDecisionAuthorities.id, BigInt(auth.id)));

    // Try to execute: should fail
    await expect(executeDecisionRequest(dr.id, approverCtx)).rejects.toThrow(/not enabled/i);
  });

  it("requester_cannot_execute prevents requester from executing", async () => {
    const { ctx: requesterCtx, workspaceId } = await ws("dr-requester-execute");
    const approverCtx = { ...requesterCtx, workforceMemberId: String(generateSnowflake()) };

    const policy: ApprovalPolicy = {
      required_capabilities: ["sales_manager"],
      distinct_approvers: 1,
      requester_must_differ: true,
      requester_cannot_execute: true,
    };

    await seedDecisionAuthority(
      {
        workspaceId,
        authorityKey: "test.discount.no-exec",
        decisionKind: "discount",
        approvalPolicy: policy,
      },
      requesterCtx,
    );

    await grantAuthorityCapability(
      {
        workspaceId,
        authorityKey: "test.discount.no-exec",
        workforceMemberId: requesterCtx.workforceMemberId,
        capability: "sales_manager",
      },
      requesterCtx,
    );

    const dr = await createDecisionRequest(
      {
        requestType: "discount",
        authorityKey: "test.discount.no-exec",
        options: [],
      },
      requesterCtx,
    );

    // Manually approve (bypass requester check)
    await grantAuthorityCapability(
      {
        workspaceId,
        authorityKey: "test.discount.no-exec",
        workforceMemberId: approverCtx.workforceMemberId,
        capability: "sales_manager",
      },
      requesterCtx,
    );

    await submitDecisionRequest(dr.id, { policySnapshotRef: "policy_v1" }, requesterCtx);

    await recordApproval(dr.id, { decision: "approve" }, approverCtx);

    // Requester tries to execute
    await expect(executeDecisionRequest(dr.id, requesterCtx)).rejects.toThrow(/requester cannot execute/i);
  });

  it("execute succeeds and sets executionRef=noop_<id>, status=executed", async () => {
    const { ctx: requesterCtx, workspaceId } = await ws("dr-execute-success");
    const approverCtx = { ...requesterCtx, workforceMemberId: String(generateSnowflake()) };

    const policy: ApprovalPolicy = {
      required_capabilities: ["sales_manager"],
      distinct_approvers: 1,
      requester_must_differ: true,
      requester_cannot_execute: true,
    };

    await seedDecisionAuthority(
      {
        workspaceId,
        authorityKey: "test.discount.execute",
        decisionKind: "discount",
        approvalPolicy: policy,
      },
      requesterCtx,
    );

    await grantAuthorityCapability(
      {
        workspaceId,
        authorityKey: "test.discount.execute",
        workforceMemberId: approverCtx.workforceMemberId,
        capability: "sales_manager",
      },
      requesterCtx,
    );

    const dr = await createDecisionRequest(
      {
        requestType: "discount",
        authorityKey: "test.discount.execute",
        options: [],
      },
      requesterCtx,
    );

    await submitDecisionRequest(dr.id, { policySnapshotRef: "policy_v1" }, requesterCtx);

    await recordApproval(dr.id, { decision: "approve" }, approverCtx);

    const executed = await executeDecisionRequest(dr.id, approverCtx);

    expect(executed.status).toBe("executed");
    expect(executed.executionRef).toBe(`noop_${dr.id}`);
    expect(executed.executedByWorkforceMemberId).toBe(approverCtx.workforceMemberId);
  });

  it("decision_request.submitted and decided events in outbox", async () => {
    const { ctx: requesterCtx, workspaceId } = await ws("dr-events");
    const approverCtx = { ...requesterCtx, workforceMemberId: String(generateSnowflake()) };

    const policy: ApprovalPolicy = {
      required_capabilities: ["sales_manager"],
      distinct_approvers: 1,
      requester_must_differ: true,
      requester_cannot_execute: true,
    };

    await seedDecisionAuthority(
      {
        workspaceId,
        authorityKey: "test.discount.events",
        decisionKind: "discount",
        approvalPolicy: policy,
      },
      requesterCtx,
    );

    await grantAuthorityCapability(
      {
        workspaceId,
        authorityKey: "test.discount.events",
        workforceMemberId: approverCtx.workforceMemberId,
        capability: "sales_manager",
      },
      requesterCtx,
    );

    const dr = await createDecisionRequest(
      {
        requestType: "discount",
        authorityKey: "test.discount.events",
        options: [],
      },
      requesterCtx,
    );

    await submitDecisionRequest(dr.id, { policySnapshotRef: "policy_v1" }, requesterCtx);

    // Check for submitted event
    const submittedRows = await db.execute(
      // @ts-ignore raw
      sql`SELECT event_type FROM integration.event_outbox WHERE aggregate_id = ${dr.id} AND event_type = 'engagement.decision_request.submitted.v1'`,
    );
    expect((submittedRows as any).rows).toHaveLength(1);

    await recordApproval(dr.id, { decision: "approve" }, approverCtx);

    // Check for decided event
    const decidedRows = await db.execute(
      // @ts-ignore raw
      sql`SELECT event_type FROM integration.event_outbox WHERE aggregate_id = ${dr.id} AND event_type = 'engagement.decision_request.decided.v1'`,
    );
    expect((decidedRows as any).rows).toHaveLength(1);
  });
});
