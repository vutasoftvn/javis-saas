import { describe, expect, it } from "vitest";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { createSecondWorkspace, createTestWorkspaceWithMember } from "../../operations/tests/_helpers";
import { getMeProfile } from "../services/auth.service";

const { identityWorkspaceMemberships } = schema;

// /identity/me từng trả membership active đầu tiên bất kể workspace đang chọn,
// nên user có nhiều workspace nhận nhầm workspace và role.
describe("getMeProfile", () => {
  it("returns the membership of the requested workspace", async () => {
    const first = await createTestWorkspaceWithMember({ role: "founder" });
    const second = await createSecondWorkspace();
    await db.insert(identityWorkspaceMemberships).values({
      id: generateSnowflake(),
      workspaceId: BigInt(second.workspaceId),
      userId: BigInt(first.userId),
      role: "member",
    });

    const inFirst = await getMeProfile(first.userId, first.workspaceId);
    expect(inFirst).toMatchObject({ workspaceId: first.workspaceId, role: "founder" });

    const inSecond = await getMeProfile(first.userId, second.workspaceId);
    expect(inSecond).toMatchObject({ workspaceId: second.workspaceId, role: "member" });
  });

  it("denies a workspace the user does not belong to", async () => {
    const user = await createTestWorkspaceWithMember({ role: "founder" });
    const other = await createSecondWorkspace();

    await expect(getMeProfile(user.userId, other.workspaceId)).rejects.toMatchObject({
      code: "permission_denied",
    });
  });
});
