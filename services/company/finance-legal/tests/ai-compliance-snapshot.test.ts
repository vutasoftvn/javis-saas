import { describe, expect, it } from "vitest";
import {
  captureComplianceSnapshot,
  verifySnapshotIntegrity,
} from "../services/ai-compliance-snapshot.service";
import { generateSnowflake } from "../../shared/services/snowflake.service";

describe("AI compliance snapshot and audit export", () => {
  const workspaceId = String(generateSnowflake());

  it("verifies snapshot hash matches canonical content", async () => {
    const snap = await captureComplianceSnapshot(workspaceId);
    expect(snap.snapshotHash).toMatch(/^sha256:[a-f0-9]{64}$/);
    const ok = await verifySnapshotIntegrity(workspaceId, String(snap.id));
    expect(ok).toBe(true);
  });
});
