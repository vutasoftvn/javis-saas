import { describe, expect, it } from "vitest";
import { makeTenantContext } from "./tenant-context.fixture";

describe("makeTenantContext", () => {
  it("fills every required TenantContext field while preserving identities", () => {
    expect(makeTenantContext({ workspaceId: "10", userId: "20" })).toEqual({
      workspaceId: "10",
      userId: "20",
      membershipRole: "member",
      permissions: [],
      correlationId: "test-correlation-id",
    });
  });
});
