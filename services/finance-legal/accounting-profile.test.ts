import { describe, expect, it } from "vitest";
import { createWorkspace } from "../identity/workspace";
import { createAccountingProfile, getAccountingProfileByWorkspace } from "./accounting-profile";

describe("createAccountingProfile", () => {
  it("creates a profile with canonical defaults", async () => {
    const workspace = await createWorkspace({ name: "Profile Test Inc" });
    const profile = await createAccountingProfile({ workspaceId: workspace.id });
    expect(profile.id).toBeGreaterThan(0);
    expect(profile.mode).toBe("TT58_MODE_1");
    expect(profile.status).toBe("DRAFT");
  });

  it("rejects a profile for a workspace that doesn't exist", async () => {
    await expect(createAccountingProfile({ workspaceId: 999999999 })).rejects.toThrow();
  });

  it("rejects a second profile for the same workspace", async () => {
    const workspace = await createWorkspace({ name: "Dup Profile Inc" });
    await createAccountingProfile({ workspaceId: workspace.id });
    await expect(createAccountingProfile({ workspaceId: workspace.id })).rejects.toThrow();
  });
});

describe("getAccountingProfileByWorkspace", () => {
  it("fetches the profile for a workspace", async () => {
    const workspace = await createWorkspace({ name: "Fetch Profile Inc" });
    const created = await createAccountingProfile({ workspaceId: workspace.id });
    const fetched = await getAccountingProfileByWorkspace({ workspaceId: workspace.id });
    expect(fetched).toEqual(created);
  });

  it("throws not found when no profile exists yet", async () => {
    const workspace = await createWorkspace({ name: "No Profile Inc" });
    await expect(getAccountingProfileByWorkspace({ workspaceId: workspace.id })).rejects.toThrow();
  });
});
