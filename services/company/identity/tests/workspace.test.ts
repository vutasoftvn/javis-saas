import { describe, expect, it } from "vitest";
import { createWorkspace, getWorkspace } from "../handlers/workspace.handler";
import { createTestSession } from "./helpers/test-session";
import {
  createWorkspaceRecord,
  getWorkspaceRecord,
  updateWorkspaceCompanyIdentityRecord,
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

describe("updateWorkspaceCompanyIdentityRecord", () => {
  it("persists vision/mission/coreValues when all three are non-empty", async () => {
    const session = await createTestSession({ displayName: "Identity Save Test" });

    const updated = await updateWorkspaceCompanyIdentityRecord({
      workspaceId: session.workspaceId,
      authorization: `Bearer ${session.accessToken}`,
      vision: "Trở thành nền tảng số 1 cho founder Việt Nam",
      mission: "Trao quyền cho founder ra quyết định bằng dữ liệu thật",
      coreValues: "Minh bạch, Tốc độ, Lấy khách hàng làm trung tâm",
    });

    expect(updated.vision).toBe("Trở thành nền tảng số 1 cho founder Việt Nam");
    expect(updated.mission).toBe("Trao quyền cho founder ra quyết định bằng dữ liệu thật");
    expect(updated.coreValues).toBe("Minh bạch, Tốc độ, Lấy khách hàng làm trung tâm");

    const refetched = await getWorkspaceRecord(session.workspaceId);
    expect(refetched.vision).toBe(updated.vision);
  });

  it("rejects when any of the three fields is empty after trim", async () => {
    const session = await createTestSession({ displayName: "Identity Reject Test" });

    await expect(
      updateWorkspaceCompanyIdentityRecord({
        workspaceId: session.workspaceId,
        authorization: `Bearer ${session.accessToken}`,
        vision: "  ",
        mission: "Mission hợp lệ",
        coreValues: "Values hợp lệ",
      })
    ).rejects.toThrow();
  });

  it("rejects when caller is not a member of the target workspace", async () => {
    const session = await createTestSession({ displayName: "Identity Non Member Test" });
    const otherWorkspace = await createWorkspaceRecord({ name: "Other Workspace" });

    await expect(
      updateWorkspaceCompanyIdentityRecord({
        workspaceId: otherWorkspace.id,
        authorization: `Bearer ${session.accessToken}`,
        vision: "Vision",
        mission: "Mission",
        coreValues: "Values",
      })
    ).rejects.toThrow();
  });
});
