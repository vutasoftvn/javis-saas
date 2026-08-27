// services/company/shared/tests/workspace-resolver.test.ts
import { describe, expect, it } from "vitest";
import { resolveProductWorkspaceId } from "../services/workspace-resolver.service";
import { createTestSession } from "../../identity/tests/helpers/test-session";

describe("resolveProductWorkspaceId (workspace-only product resolver)", () => {
  it("returns the workspaceId directly when workspaceId is given", async () => {
    const session = await createTestSession({ displayName: "Product Resolver Direct Test" });
    const resolved = await resolveProductWorkspaceId(session.workspaceId);
    expect(resolved).toBe(BigInt(session.workspaceId));
  });

  it("throws invalidArgument when workspaceId is not provided", async () => {
    await expect(resolveProductWorkspaceId(undefined)).rejects.toThrow();
  });

  it("throws notFound when workspaceId does not exist", async () => {
    await expect(resolveProductWorkspaceId("999999999999999999")).rejects.toThrow();
  });

});
