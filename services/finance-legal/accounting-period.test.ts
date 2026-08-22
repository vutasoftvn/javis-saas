import { describe, expect, it } from "vitest";
import { createWorkspace } from "../identity/workspace";
import { openAccountingPeriod, getAccountingPeriod, closeAccountingPeriod } from "./accounting-period";

describe("openAccountingPeriod", () => {
  it("opens a period with the default OPEN status", async () => {
    const workspace = await createWorkspace({ name: "Period Test Inc" });
    const period = await openAccountingPeriod({
      workspaceId: workspace.id,
      startDate: "2026-01-01",
      endDate: "2026-01-31",
    });
    expect(period.id).toBeGreaterThan(0);
    expect(period.status).toBe("OPEN");
  });

  it("rejects a period for a workspace that doesn't exist", async () => {
    await expect(
      openAccountingPeriod({ workspaceId: 999999999, startDate: "2026-01-01", endDate: "2026-01-31" })
    ).rejects.toThrow();
  });
});

describe("getAccountingPeriod/closeAccountingPeriod", () => {
  it("fetches a period and closes it", async () => {
    const workspace = await createWorkspace({ name: "Close Period Test Inc" });
    const created = await openAccountingPeriod({
      workspaceId: workspace.id,
      startDate: "2026-02-01",
      endDate: "2026-02-28",
    });

    const fetched = await getAccountingPeriod({ id: created.id });
    expect(fetched).toEqual(created);

    const closed = await closeAccountingPeriod({ id: created.id });
    expect(closed.status).toBe("CLOSED");
  });

  it("throws not found for a missing id", async () => {
    await expect(getAccountingPeriod({ id: 999999999 })).rejects.toThrow();
  });
});
