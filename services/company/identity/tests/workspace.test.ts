import { describe, expect, it } from "vitest";
import { createWorkspace, getWorkspace, updateWorkspaceCompanyIdentity } from "../handlers/workspace.handler";
import { createTestSession } from "./helpers/test-session";
import {
  createWorkspaceRecord,
  getWorkspaceRecord,
  updateWorkspaceOrientationRecord,
} from "../services/workspace.service";

describe("createWorkspace", () => {
  it("creates a workspace with the default lifecycle stage", async () => {
    const workspace = await createWorkspace({ name: "Acme Inc" });
    expect(workspace.id).toBeTruthy();
    expect(typeof workspace.id).toBe("string");
    expect(workspace.name).toBe("Acme Inc");
    expect(workspace.lifecycleStage).toBe("W0_IDEA");
  });
});

describe("getWorkspace", () => {
  it("returns a previously created workspace", async () => {
    const created = await createWorkspace({ name: "Fetch Me Inc" });
    const fetched = await getWorkspace({ id: created.id });
    expect(fetched).toEqual(created);
  });

  it("throws not found for a missing id", async () => {
    await expect(getWorkspace({ id: "999999999" })).rejects.toThrow();
  });
});

describe("updateWorkspaceOrientationRecord", () => {
  it("updates one supplied orientation field without overwriting the others", async () => {
    const session = await createTestSession({ displayName: "Orientation partial update" });
    await updateWorkspaceOrientationRecord({
      workspaceId: session.workspaceId,
      authorization: "Bearer " + session.accessToken,
      vision: "Original vision",
      mission: "Original mission",
      coreValues: "Original values",
    });

    const updated = await updateWorkspaceOrientationRecord({
      workspaceId: session.workspaceId,
      authorization: "Bearer " + session.accessToken,
      mission: "Updated mission",
    });

    expect(updated.vision).toBe("Original vision");
    expect(updated.mission).toBe("Updated mission");
    expect(updated.coreValues).toBe("Original values");
  });

  it("clears an explicitly supplied blank field", async () => {
    const session = await createTestSession({ displayName: "Orientation clear" });
    await updateWorkspaceOrientationRecord({
      workspaceId: session.workspaceId,
      authorization: "Bearer " + session.accessToken,
      vision: "A direction",
    });

    const updated = await updateWorkspaceOrientationRecord({
      workspaceId: session.workspaceId,
      authorization: "Bearer " + session.accessToken,
      vision: "   ",
    });

    expect(updated.vision).toBeNull();
  });

  it("rejects a patch with no orientation keys", async () => {
    const session = await createTestSession({ displayName: "Orientation empty patch" });

    await expect(
      updateWorkspaceOrientationRecord({
        workspaceId: session.workspaceId,
        authorization: "Bearer " + session.accessToken,
      })
    ).rejects.toThrow(/at least one orientation field/i);
  });

  it("rejects when caller is not a member of the target workspace", async () => {
    const session = await createTestSession({ displayName: "Orientation Non Member Test" });
    const otherWorkspace = await createWorkspaceRecord({ name: "Other Workspace" });

    await expect(
      updateWorkspaceOrientationRecord({
        workspaceId: otherWorkspace.id,
        authorization: `Bearer ${session.accessToken}`,
        vision: "Vision",
      })
    ).rejects.toThrow();
  });
});

describe("updateWorkspaceCompanyIdentity handler", () => {
  it("exposes PATCH .../company-identity and returns the updated workspace with nullable fields", async () => {
    const session = await createTestSession({ displayName: "Orientation Handler Test" });

    const updated = await updateWorkspaceCompanyIdentity({
      id: session.workspaceId,
      authorization: `Bearer ${session.accessToken}`,
      mission: "Mission qua handler",
    });

    expect(updated.id).toBe(session.workspaceId);
    expect(updated.mission).toBe("Mission qua handler");
    expect(updated.vision).toBeNull();
    expect(updated.coreValues).toBeNull();
  });
});

