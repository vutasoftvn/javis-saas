import { describe, expect, it } from "vitest";
import { registerUserService } from "../../identity/services/auth.service";
import { createObligation, getObligation, fulfillObligation } from "../handlers/legal-obligation.handler";

async function makeAuthedWorkspace(displayName: string) {
  const user = await registerUserService({
    email: `${displayName.toLowerCase().replace(/\s+/g, "-")}-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
    password: "password123",
    displayName,
  });
  return { workspaceId: user.workspaceId, authorization: `Bearer ${user.accessToken}` };
}

describe("createObligation", () => {
  it("creates an obligation with the default OPEN status", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Obligation Test Inc");
    const obligation = await createObligation({ workspaceId, title: "File annual report", authorization });
    expect(obligation.id).toBeGreaterThan(0);
    expect(obligation.status).toBe("OPEN");
  });

  it("rejects an obligation for a workspace that doesn't exist", async () => {
    const { authorization } = await makeAuthedWorkspace("Nonexistent Ws Obligation Test");
    await expect(
      createObligation({ workspaceId: 999999999, title: "Orphan obligation", authorization })
    ).rejects.toThrow();
  });

  it("rejects when caller is not a member of the target workspace", async () => {
    const { workspaceId } = await makeAuthedWorkspace("Owner Obligation Ws");
    const outsider = await makeAuthedWorkspace("Outsider Obligation Test");
    await expect(
      createObligation({ workspaceId, title: "Should be blocked", authorization: outsider.authorization })
    ).rejects.toThrow();
  });
});

describe("getObligation/fulfillObligation", () => {
  it("fetches an obligation and marks it fulfilled", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Fulfill Obligation Inc");
    const created = await createObligation({ workspaceId, title: "Fetch me", authorization });

    const fetched = await getObligation({ id: created.id, authorization });
    expect(fetched).toEqual(created);

    const fulfilled = await fulfillObligation({ id: created.id, authorization });
    expect(fulfilled.status).toBe("FULFILLED");
  });

  it("throws not found for a missing id", async () => {
    const { authorization } = await makeAuthedWorkspace("Missing Obligation Test");
    await expect(getObligation({ id: 999999999, authorization })).rejects.toThrow();
  });
});
