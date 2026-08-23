import { describe, expect, it } from "vitest";
import { createWorkspace, getWorkspace } from "../handlers/workspace.handler";

describe("createWorkspace", () => {
  it("creates a workspace with the default company stage", async () => {
    const workspace = await createWorkspace({ name: "Acme Inc" });
    expect(workspace.id).toBeTruthy();
    expect(typeof workspace.id).toBe("string");
    expect(workspace.name).toBe("Acme Inc");
    expect(workspace.companyStage).toBe("S0_GENESIS");
  });
});

describe("getWorkspace", () => {
  it("returns a previously created workspace", async () => {
    const created = await createWorkspace({ name: "Fetch Me Inc" });
    const fetched = await getWorkspace({ id: created.id });
    expect(fetched).toEqual(created);
  });

  it("throws not found for a missing id", async () => {
    await expect(getWorkspace({ id: 999999999 })).rejects.toThrow();
  });
});
