import { describe, it, expect } from "vitest";
import { eq, and } from "drizzle-orm";
import { db } from "../models/db";
import { identityWorkforceMembers } from "../../shared/db/schema/identity";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { createTestWorkspaceWithMember } from "./_helpers";
import {
  ensureAiWorkforceMember,
  resolveFounderMemberId,
  AGENT_PROFILE_SPEC_ID,
} from "../services/ai-member.service";

async function seedHumanMember(workspaceId: string, humanUserId: string): Promise<string> {
  const id = generateSnowflake();
  await db.insert(identityWorkforceMembers).values({
    id,
    workspaceId: BigInt(workspaceId),
    memberType: "HUMAN",
    humanUserId: BigInt(humanUserId),
    roleTitle: "Founder",
    status: "active",
  });
  return id.toString();
}

describe("ensureAiWorkforceMember", () => {
  it("creates the AI member once and returns the same id on a second call", async () => {
    const ws = await createTestWorkspaceWithMember();
    const id1 = await db.transaction((tx) => ensureAiWorkforceMember(tx, ws.workspaceId, "operations"));
    const id2 = await db.transaction((tx) => ensureAiWorkforceMember(tx, ws.workspaceId, "operations"));
    expect(id1).toBe(id2);

    const [row] = await db
      .select()
      .from(identityWorkforceMembers)
      .where(eq(identityWorkforceMembers.id, BigInt(id1)));
    expect(row!.memberType).toBe("AI_AGENT");
    expect(row!.agentSpecId).toBe(AGENT_PROFILE_SPEC_ID.operations);
  });

  it("creates a distinct AI member per agent profile", async () => {
    const ws = await createTestWorkspaceWithMember();
    const ops = await db.transaction((tx) => ensureAiWorkforceMember(tx, ws.workspaceId, "operations"));
    const fin = await db.transaction((tx) => ensureAiWorkforceMember(tx, ws.workspaceId, "finance"));
    const mkt = await db.transaction((tx) => ensureAiWorkforceMember(tx, ws.workspaceId, "marketing"));
    expect(new Set([ops, fin, mkt]).size).toBe(3);
  });
});

describe("resolveFounderMemberId", () => {
  it("returns the preferred member when it is a HUMAN member of the workspace", async () => {
    const ws = await createTestWorkspaceWithMember();
    const memberId = await seedHumanMember(ws.workspaceId, ws.userId);
    const resolved = await db.transaction((tx) =>
      resolveFounderMemberId(tx, ws.workspaceId, memberId)
    );
    expect(resolved).toBe(memberId);
  });

  it("falls back to the oldest HUMAN member when no preferred id is given", async () => {
    const ws = await createTestWorkspaceWithMember();
    const first = await seedHumanMember(ws.workspaceId, ws.userId);
    await seedHumanMember(ws.workspaceId, ws.userId);
    const resolved = await db.transaction((tx) => resolveFounderMemberId(tx, ws.workspaceId, null));
    expect(resolved).toBe(first);
  });

  it("returns null when the workspace has no HUMAN member", async () => {
    const ws = await createTestWorkspaceWithMember();
    const resolved = await db.transaction((tx) => resolveFounderMemberId(tx, ws.workspaceId, null));
    expect(resolved).toBeNull();
  });

  it("ignores a preferred id that is an AI member and falls back", async () => {
    const ws = await createTestWorkspaceWithMember();
    const human = await seedHumanMember(ws.workspaceId, ws.userId);
    const ai = await db.transaction((tx) => ensureAiWorkforceMember(tx, ws.workspaceId, "operations"));
    const resolved = await db.transaction((tx) => resolveFounderMemberId(tx, ws.workspaceId, ai));
    expect(resolved).toBe(human);
  });
});
