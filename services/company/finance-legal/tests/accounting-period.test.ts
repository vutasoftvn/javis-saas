import { describe, expect, it } from "vitest";
import { registerUserService } from "../../identity/services/auth.service";
import { openAccountingPeriod, getAccountingPeriod, closeAccountingPeriod } from "../handlers/accounting-period.handler";

async function makeAuthedWorkspace(displayName: string) {
  const user = await registerUserService({
    email: `${displayName.toLowerCase().replace(/\s+/g, "-")}-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
    password: "password123",
    displayName,
  });
  return { workspaceId: user.workspaceId, authorization: `Bearer ${user.accessToken}` };
}

describe("openAccountingPeriod", () => {
  it("opens a period with the default OPEN status", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Period Test Inc");
    const period = await openAccountingPeriod({
      workspaceId,
      startDate: "2026-01-01",
      endDate: "2026-01-31",
      authorization,
    });
    expect(period.id).toBeTruthy();
    expect(period.status).toBe("OPEN");
  });

  it("rejects a period for a workspace that doesn't exist", async () => {
    const { authorization } = await makeAuthedWorkspace("Nonexistent Ws Test");
    await expect(
      openAccountingPeriod({ workspaceId: 999999999, startDate: "2026-01-01", endDate: "2026-01-31", authorization })
    ).rejects.toThrow();
  });

  it("rejects when caller is not a member of the target workspace", async () => {
    const { workspaceId } = await makeAuthedWorkspace("Owner Ws Test");
    const outsider = await makeAuthedWorkspace("Outsider Test");
    await expect(
      openAccountingPeriod({
        workspaceId,
        startDate: "2026-01-01",
        endDate: "2026-01-31",
        authorization: outsider.authorization,
      })
    ).rejects.toThrow();
  });
});

describe("getAccountingPeriod/closeAccountingPeriod", () => {
  it("fetches a period and closes it", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Close Period Test Inc");
    const created = await openAccountingPeriod({
      workspaceId,
      startDate: "2026-02-01",
      endDate: "2026-02-28",
      authorization,
    });

    const fetched = await getAccountingPeriod({ id: created.id, authorization });
    expect(fetched).toEqual(created);

    const closed = await closeAccountingPeriod({ id: created.id, authorization });
    expect(closed.status).toBe("CLOSED");
  });

  it("throws not found for a missing id", async () => {
    await expect(getAccountingPeriod({ id: 999999999 })).rejects.toThrow();
  });
});
