import { describe, expect, it } from "vitest";
import { registerUserService } from "../../identity/services/auth.service";
import { recordFinanceSnapshot, getLatestFinanceSnapshot } from "../handlers/finance-snapshot.handler";

async function makeAuthedWorkspace(displayName: string) {
  const user = await registerUserService({
    email: `${displayName.toLowerCase().replace(/\s+/g, "-")}-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
    password: "password123",
    displayName,
  });
  return { workspaceId: user.workspaceId, authorization: `Bearer ${user.accessToken}` };
}

describe("recordFinanceSnapshot", () => {
  it("records a snapshot with exact decimal cash/burn as strings", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Snapshot Test Inc");
    const snapshot = await recordFinanceSnapshot({
      workspaceId,
      asOf: "2026-01-31",
      cash: "500000.00",
      burn: "50000.00",
      authorization,
    });
    expect(snapshot.id).toBeGreaterThan(0);
    expect(snapshot.cash).toBe("500000.00");
    expect(snapshot.burn).toBe("50000.00");
    expect(snapshot.revenue).toBe("0.00");
  });

  it("rejects a snapshot for a workspace that doesn't exist", async () => {
    const { authorization } = await makeAuthedWorkspace("Nonexistent Ws Snapshot Test");
    await expect(
      recordFinanceSnapshot({ workspaceId: 999999999, asOf: "2026-01-31", cash: "1.00", burn: "1.00", authorization })
    ).rejects.toThrow();
  });

  it("rejects when caller is not a member of the target workspace", async () => {
    const { workspaceId } = await makeAuthedWorkspace("Owner Snapshot Ws");
    const outsider = await makeAuthedWorkspace("Outsider Snapshot Test");
    await expect(
      recordFinanceSnapshot({
        workspaceId,
        asOf: "2026-01-31",
        cash: "1.00",
        burn: "1.00",
        authorization: outsider.authorization,
      })
    ).rejects.toThrow();
  });
});

describe("getLatestFinanceSnapshot", () => {
  it("returns the most recent snapshot by as_of date", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Latest Snapshot Test Inc");
    await recordFinanceSnapshot({ workspaceId, asOf: "2026-01-31", cash: "100.00", burn: "10.00", authorization });
    const latest = await recordFinanceSnapshot({
      workspaceId,
      asOf: "2026-02-28",
      cash: "90.00",
      burn: "10.00",
      authorization,
    });

    const fetched = await getLatestFinanceSnapshot({ workspaceId, authorization });
    expect(fetched.id).toBe(latest.id);
    expect(fetched.cash).toBe("90.00");
  });

  it("throws not found when no snapshot exists yet", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("No Snapshot Inc");
    await expect(getLatestFinanceSnapshot({ workspaceId, authorization })).rejects.toThrow();
  });
});
