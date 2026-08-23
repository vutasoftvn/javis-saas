import { describe, expect, it } from "vitest";
import { createTestSession } from "./helpers/test-session";
import { createWorkspace } from "../handlers/workspace.handler";
import { hireWorkforceMember, getWorkforceMember } from "../handlers/workforce.handler";

describe("tenant boundary — identity workforce/workspace", () => {
  it("full lifecycle: only a real workspace member can hire and read workforce members in that workspace", async () => {
    const owner = await createTestSession({ displayName: "Boundary Owner" });
    const outsider = await createTestSession({ displayName: "Boundary Outsider" });

    // Outsider không thể hire vào workspace của owner.
    await expect(
      hireWorkforceMember({
        workspaceId: owner.workspaceId,
        memberType: "HUMAN",
        roleTitle: "Intruder",
        humanUserId: outsider.userId,
        authorization: `Bearer ${outsider.accessToken}`,
      })
    ).rejects.toThrow();

    // Owner hire thành công.
    const member = await hireWorkforceMember({
      workspaceId: owner.workspaceId,
      memberType: "HUMAN",
      roleTitle: "Ops Lead",
      humanUserId: owner.userId,
      authorization: `Bearer ${owner.accessToken}`,
    });

    // Outsider không đọc được member vừa tạo.
    await expect(
      getWorkforceMember({ id: member.id, authorization: `Bearer ${outsider.accessToken}` })
    ).rejects.toThrow();

    // Owner đọc được.
    const fetched = await getWorkforceMember({ id: member.id, authorization: `Bearer ${owner.accessToken}` });
    expect(fetched.id).toBe(member.id);
  });

  it("createWorkspace remains internally callable (not a public bypass) for migration/test flows", async () => {
    const ws = await createWorkspace({ name: "Internal Bootstrap Inc" });
    expect(ws.id).toBeTruthy();
  });
});
