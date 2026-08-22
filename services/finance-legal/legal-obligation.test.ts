import { describe, expect, it } from "vitest";
import { createWorkspace } from "../identity/workspace";
import { createObligation, getObligation, fulfillObligation } from "./legal-obligation";

describe("createObligation", () => {
  it("creates an obligation with the default OPEN status", async () => {
    const workspace = await createWorkspace({ name: "Obligation Test Inc" });
    const obligation = await createObligation({ workspaceId: workspace.id, title: "File annual report" });
    expect(obligation.id).toBeGreaterThan(0);
    expect(obligation.status).toBe("OPEN");
  });

  it("rejects an obligation for a workspace that doesn't exist", async () => {
    await expect(
      createObligation({ workspaceId: 999999999, title: "Orphan obligation" })
    ).rejects.toThrow();
  });
});

describe("getObligation/fulfillObligation", () => {
  it("fetches an obligation and marks it fulfilled", async () => {
    const workspace = await createWorkspace({ name: "Fulfill Obligation Inc" });
    const created = await createObligation({ workspaceId: workspace.id, title: "Fetch me" });

    const fetched = await getObligation({ id: created.id });
    expect(fetched).toEqual(created);

    const fulfilled = await fulfillObligation({ id: created.id });
    expect(fulfilled.status).toBe("FULFILLED");
  });

  it("throws not found for a missing id", async () => {
    await expect(getObligation({ id: 999999999 })).rejects.toThrow();
  });
});
