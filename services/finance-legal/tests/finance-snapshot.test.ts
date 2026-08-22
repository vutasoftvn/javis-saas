import { describe, expect, it } from "vitest";
import { createWorkspace } from "../../identity/handlers/workspace.handler";
import { recordFinanceSnapshot, getLatestFinanceSnapshot } from "../handlers/finance-snapshot.handler";

describe("recordFinanceSnapshot", () => {
  it("records a snapshot with exact decimal cash/burn as strings", async () => {
    const workspace = await createWorkspace({ name: "Snapshot Test Inc" });
    const snapshot = await recordFinanceSnapshot({
      workspaceId: workspace.id,
      asOf: "2026-01-31",
      cash: "500000.00",
      burn: "50000.00",
    });
    expect(snapshot.id).toBeGreaterThan(0);
    expect(snapshot.cash).toBe("500000.00");
    expect(snapshot.burn).toBe("50000.00");
    expect(snapshot.revenue).toBe("0.00");
  });

  it("rejects a snapshot for a workspace that doesn't exist", async () => {
    await expect(
      recordFinanceSnapshot({ workspaceId: 999999999, asOf: "2026-01-31", cash: "1.00", burn: "1.00" })
    ).rejects.toThrow();
  });
});

describe("getLatestFinanceSnapshot", () => {
  it("returns the most recent snapshot by as_of date", async () => {
    const workspace = await createWorkspace({ name: "Latest Snapshot Test Inc" });
    await recordFinanceSnapshot({ workspaceId: workspace.id, asOf: "2026-01-31", cash: "100.00", burn: "10.00" });
    const latest = await recordFinanceSnapshot({ workspaceId: workspace.id, asOf: "2026-02-28", cash: "90.00", burn: "10.00" });

    const fetched = await getLatestFinanceSnapshot({ workspaceId: workspace.id });
    expect(fetched.id).toBe(latest.id);
    expect(fetched.cash).toBe("90.00");
  });

  it("throws not found when no snapshot exists yet", async () => {
    const workspace = await createWorkspace({ name: "No Snapshot Inc" });
    await expect(getLatestFinanceSnapshot({ workspaceId: workspace.id })).rejects.toThrow();
  });
});
