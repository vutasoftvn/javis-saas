import { describe, expect, it } from "vitest";
import { registerUserService } from "../../identity/services/auth.service";
import { createAccountingProfile, getAccountingProfileByWorkspace } from "../handlers/accounting-profile.handler";

async function makeAuthedWorkspace(displayName: string) {
  const user = await registerUserService({
    email: `${displayName.toLowerCase().replace(/\s+/g, "-")}-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
    password: "password123",
    displayName,
  });
  return { workspaceId: user.workspaceId, authorization: `Bearer ${user.accessToken}` };
}

describe("createAccountingProfile", () => {
  it("creates a profile with canonical defaults", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Profile Test Inc");
    const profile = await createAccountingProfile({ workspaceId, authorization });
    expect(profile.id).toBeTruthy();
    expect(profile.mode).toBe("TT58_MODE_1");
    expect(profile.status).toBe("DRAFT");
  });

  it("rejects a profile for a workspace that doesn't exist", async () => {
    const { authorization } = await makeAuthedWorkspace("Nonexistent Ws Test");
    await expect(createAccountingProfile({ workspaceId: 999999999, authorization })).rejects.toThrow();
  });

  it("rejects a second profile for the same workspace", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Dup Profile Inc");
    await createAccountingProfile({ workspaceId, authorization });
    await expect(createAccountingProfile({ workspaceId, authorization })).rejects.toThrow();
  });

  it("rejects when caller is not a member of the target workspace", async () => {
    const { workspaceId } = await makeAuthedWorkspace("Owner Profile Ws");
    const outsider = await makeAuthedWorkspace("Outsider Profile Test");
    await expect(
      createAccountingProfile({ workspaceId, authorization: outsider.authorization })
    ).rejects.toThrow();
  });
});

describe("getAccountingProfileByWorkspace", () => {
  it("fetches the profile for a workspace", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Fetch Profile Inc");
    const created = await createAccountingProfile({ workspaceId, authorization });
    const fetched = await getAccountingProfileByWorkspace({ workspaceId, authorization });
    expect(fetched).toEqual(created);
  });

  it("throws not found when no profile exists yet", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("No Profile Inc");
    await expect(getAccountingProfileByWorkspace({ workspaceId, authorization })).rejects.toThrow();
  });
});
