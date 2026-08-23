import { describe, expect, it } from "vitest";
import { createTestSession } from "./helpers/test-session";
import { getMe } from "../handlers/auth.handler";

describe("getMe", () => {
  it("resolves the current user's profile and workspace info", async () => {
    const email = `me-${Date.now()}@example.com`;
    const session = await createTestSession({ email, displayName: "Me User" });

    const me = await getMe({ userID: session.userId });
    expect(me.id).toBe(session.userId);
    expect(me.email).toBe(email);
    expect(me.displayName).toBe("Me User");
    expect(me.workspaceId).toBe(session.workspaceId);
    expect(me.role).toBe("admin");
  });
});
