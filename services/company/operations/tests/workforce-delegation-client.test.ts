import { afterEach, describe, expect, it } from "vitest";
import { TenantContext } from "../../shared/types/tenant_context";
import {
  DelegationAuthzTransport,
  requireFounderOrDelegate,
  setDelegationAuthzTransport,
} from "../services/workforce-delegation.client";

function ctx(overrides: Partial<TenantContext> = {}): TenantContext {
  return {
    workspaceId: "ws_1",
    userId: "user_1",
    membershipRole: "member",
    permissions: [],
    correlationId: "corr_1",
    ...overrides,
  };
}

describe("workforce delegation client (Task 6)", () => {
  afterEach(() => setDelegationAuthzTransport(null));

  it("passes when the control plane allows the delegate", async () => {
    setDelegationAuthzTransport(async () => ({
      status: 200,
      body: { data: { allowed: true, mapping_verified: true, workspace_id: "ws_1" } },
    }));
    await expect(requireFounderOrDelegate(ctx(), "queue_control", "operations")).resolves.toBeUndefined();
  });

  it("fails closed on timeout (503)", async () => {
    setDelegationAuthzTransport(async () => {
      throw new Error("ETIMEDOUT");
    });
    await expect(requireFounderOrDelegate(ctx(), "queue_control", null)).rejects.toThrow(
      /authorization lookup failed/i
    );
  });

  it("denies on an explicit deny result", async () => {
    setDelegationAuthzTransport(async () => ({
      status: 200,
      body: { data: { allowed: false } },
    }));
    await expect(requireFounderOrDelegate(ctx(), "review_override", null)).rejects.toThrow(
      /denied/i
    );
  });

  it("denies on a workspace mismatch in the authz response", async () => {
    setDelegationAuthzTransport(async () => ({
      status: 200,
      body: { data: { allowed: true, workspace_id: "ws_OTHER" } },
    }));
    await expect(requireFounderOrDelegate(ctx(), "evaluation", null)).rejects.toThrow(
      /workspace mismatch/i
    );
  });

  it("denies on an unverified principal mapping", async () => {
    setDelegationAuthzTransport(async () => ({
      status: 200,
      body: { data: { allowed: true, mapping_verified: false } },
    }));
    await expect(requireFounderOrDelegate(ctx(), "evaluation", null)).rejects.toThrow(
      /unverified principal mapping/i
    );
  });

  it("denies a 403 from the control plane", async () => {
    setDelegationAuthzTransport(async () => ({ status: 403, body: {} }));
    await expect(requireFounderOrDelegate(ctx(), "queue_control", null)).rejects.toThrow(/denied/i);
  });
});
