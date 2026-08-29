import { describe, expect, it } from "vitest";
import { createTestSession } from "../../../identity/tests/helpers/test-session";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import { db, schema } from "../../models/db";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import {
  seedDecisionAuthority,
  grantAuthorityCapability,
  recomputeAuthorityStatus,
  resolveEnabledAuthority,
  memberCoversCapability,
  assertApprovalPolicySatisfied,
  ApprovalPolicy,
} from "../../services/customer-engagement/decision-authority.service";

async function ws(name: string) {
  const u = await createTestSession({ email: `${name}-${Date.now()}-${Math.random().toString(36).slice(2)}@ex.com`, displayName: name });
  const ctx = await requireWorkspaceAccess(`Bearer ${u.accessToken}`, u.workspaceId);
  return { ctx, workspaceId: u.workspaceId };
}

describe("decision-authority.service", () => {
  it("rejects an authority whose workspace does not match the authenticated context", async () => {
    const { ctx } = await ws("authority-workspace-mismatch");

    await expect(seedDecisionAuthority({
      workspaceId: String(generateSnowflake()),
      authorityKey: "test.workspace.mismatch",
      decisionKind: "discount",
      approvalPolicy: {
        required_capabilities: ["sales_manager"],
        distinct_approvers: 1,
        requester_must_differ: true,
        requester_cannot_execute: true,
      },
    }, ctx)).rejects.toThrow(/workspace mismatch/i);
  });

  it("seedDecisionAuthority creates authority with status='pending_binding'", async () => {
    const { ctx, workspaceId } = await ws("auth-seed");
    const policy: ApprovalPolicy = {
      required_capabilities: ["sales_manager"],
      distinct_approvers: 1,
      requester_must_differ: true,
      requester_cannot_execute: true,
    };

    const auth = await seedDecisionAuthority(
      {
        workspaceId,
        authorityKey: "test.discount.up_to_10_pct",
        decisionKind: "discount",
        approvalPolicy: policy,
      },
      ctx,
    );

    expect(auth.status).toBe("pending_binding");
    expect(auth.authorityKey).toBe("test.discount.up_to_10_pct");
    expect(auth.version).toBe(1);
  });

  it("grantAuthorityCapability for PART of required_capabilities keeps status='pending_binding'", async () => {
    const { ctx, workspaceId } = await ws("auth-partial");
    const policy: ApprovalPolicy = {
      required_capabilities: ["sales_director", "finance_controller"],
      distinct_approvers: 2,
      requester_must_differ: true,
      requester_cannot_execute: true,
    };

    const auth = await seedDecisionAuthority(
      {
        workspaceId,
        authorityKey: "test.pricing.exception",
        decisionKind: "pricing_exception",
        approvalPolicy: policy,
      },
      ctx,
    );

    const memberId = String(generateSnowflake());
    await grantAuthorityCapability(
      {
        workspaceId,
        authorityKey: "test.pricing.exception",
        workforceMemberId: memberId,
        capability: "sales_director",
      },
      ctx,
    );

    const row = await db.query.engagementDecisionAuthorities.findFirst({
      where: (t, { eq }) => eq(t.id, BigInt(auth.id)),
    });
    expect(row?.status).toBe("pending_binding");
  });

  it("grantAuthorityCapability for ALL required_capabilities sets status='enabled'", async () => {
    const { ctx, workspaceId } = await ws("auth-complete");
    const policy: ApprovalPolicy = {
      required_capabilities: ["sales_director", "finance_controller"],
      distinct_approvers: 2,
      requester_must_differ: true,
      requester_cannot_execute: true,
    };

    const auth = await seedDecisionAuthority(
      {
        workspaceId,
        authorityKey: "test.pricing.exception2",
        decisionKind: "pricing_exception",
        approvalPolicy: policy,
      },
      ctx,
    );

    const member1 = String(generateSnowflake());
    const member2 = String(generateSnowflake());

    await grantAuthorityCapability(
      {
        workspaceId,
        authorityKey: "test.pricing.exception2",
        workforceMemberId: member1,
        capability: "sales_director",
      },
      ctx,
    );

    await grantAuthorityCapability(
      {
        workspaceId,
        authorityKey: "test.pricing.exception2",
        workforceMemberId: member2,
        capability: "finance_controller",
      },
      ctx,
    );

    const row = await db.query.engagementDecisionAuthorities.findFirst({
      where: (t, { eq }) => eq(t.id, BigInt(auth.id)),
    });
    expect(row?.status).toBe("enabled");
  });

  it("resolveEnabledAuthority while status='pending_binding' throws failedPrecondition", async () => {
    const { ctx, workspaceId } = await ws("auth-not-enabled");
    const policy: ApprovalPolicy = {
      required_capabilities: ["sales_manager"],
      distinct_approvers: 1,
      requester_must_differ: true,
      requester_cannot_execute: true,
    };

    await seedDecisionAuthority(
      {
        workspaceId,
        authorityKey: "test.not_enabled",
        decisionKind: "discount",
        approvalPolicy: policy,
      },
      ctx,
    );

    await expect(resolveEnabledAuthority("test.not_enabled", ctx)).rejects.toThrow(/not enabled/i);
  });

  it("assertApprovalPolicySatisfied with 1 approver when 2 distinct required throws", () => {
    const policy: ApprovalPolicy = {
      required_capabilities: ["sales_director", "finance_controller"],
      distinct_approvers: 2,
      requester_must_differ: true,
      requester_cannot_execute: true,
    };

    const approvals = [
      {
        workforceMemberId: "member1",
        capability: "sales_director",
        decision: "approve",
      },
    ];

    expect(() => assertApprovalPolicySatisfied(policy, approvals as any)).toThrow(/insufficient/i);
  });

  it("assertApprovalPolicySatisfied with 2 distinct approvers covering all capabilities passes", () => {
    const policy: ApprovalPolicy = {
      required_capabilities: ["sales_director", "finance_controller"],
      distinct_approvers: 2,
      requester_must_differ: true,
      requester_cannot_execute: true,
    };

    const approvals = [
      {
        workforceMemberId: "member1",
        capability: "sales_director",
        decision: "approve",
      },
      {
        workforceMemberId: "member2",
        capability: "finance_controller",
        decision: "approve",
      },
    ];

    expect(() => assertApprovalPolicySatisfied(policy, approvals as any)).not.toThrow();
  });

  it("assertApprovalPolicySatisfied with missing required capability throws", () => {
    const policy: ApprovalPolicy = {
      required_capabilities: ["sales_director", "finance_controller"],
      distinct_approvers: 2,
      requester_must_differ: true,
      requester_cannot_execute: true,
    };

    const approvals = [
      {
        workforceMemberId: "member1",
        capability: "sales_director",
        decision: "approve",
      },
      {
        workforceMemberId: "member2",
        capability: "sales_director", // Missing finance_controller
        decision: "approve",
      },
    ];

    expect(() => assertApprovalPolicySatisfied(policy, approvals as any)).toThrow(/missing required/i);
  });

  it("memberCoversCapability with active grant returns capability", async () => {
    const { ctx, workspaceId } = await ws("auth-covers");
    const policy: ApprovalPolicy = {
      required_capabilities: ["sales_manager"],
      distinct_approvers: 1,
      requester_must_differ: true,
      requester_cannot_execute: true,
    };

    await seedDecisionAuthority(
      {
        workspaceId,
        authorityKey: "test.covers",
        decisionKind: "discount",
        approvalPolicy: policy,
      },
      ctx,
    );

    const memberId = String(generateSnowflake());
    await grantAuthorityCapability(
      {
        workspaceId,
        authorityKey: "test.covers",
        workforceMemberId: memberId,
        capability: "sales_manager",
      },
      ctx,
    );

    const cap = await memberCoversCapability(memberId, "test.covers", ctx);
    expect(cap).toBe("sales_manager");
  });

  it("memberCoversCapability without grant returns null", async () => {
    const { ctx, workspaceId } = await ws("auth-no-covers");
    const policy: ApprovalPolicy = {
      required_capabilities: ["sales_manager"],
      distinct_approvers: 1,
      requester_must_differ: true,
      requester_cannot_execute: true,
    };

    await seedDecisionAuthority(
      {
        workspaceId,
        authorityKey: "test.no_covers",
        decisionKind: "discount",
        approvalPolicy: policy,
      },
      ctx,
    );

    const memberId = String(generateSnowflake());
    const cap = await memberCoversCapability(memberId, "test.no_covers", ctx);
    expect(cap).toBeNull();
  });
});
