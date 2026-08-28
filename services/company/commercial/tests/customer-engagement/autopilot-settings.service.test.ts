import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { AutopilotSettingsService } from "../../services/customer-engagement/autopilot-settings.service";
import { db } from "../../db";
import {
  engagementAutopilotSettings,
  engagementAutopilotRuns,
} from "../../../shared/db/schema/customer-engagement";

describe("AutopilotSettingsService", () => {
  const service = new AutopilotSettingsService();
  let testWorkspaceId: bigint;
  const origNodeEnv = process.env.NODE_ENV;
  const origAppEnv = process.env.APP_ENV;

  beforeEach(() => {
    testWorkspaceId = BigInt(Math.floor(Date.now() + Math.random() * 1000000));
  });

  afterEach(() => {
    process.env.NODE_ENV = origNodeEnv;
    process.env.APP_ENV = origAppEnv;
    delete process.env.ENGAGEMENT_AUTOPILOT_PROD_GATE_OVERRIDE;
  });

  it("returns default settings when not yet configured", async () => {
    const settings = await service.getSettings(testWorkspaceId);
    expect(settings.enabled).toBe(false);
    expect(settings.envAllowlist).toEqual(["test", "staging"]);
    expect(settings.containmentMin).toBe(0.8);
    expect(settings.errorMax).toBe(0.05);
    expect(settings.takeoverMax).toBe(0.15);
  });

  it("updates settings in non-prod environment", async () => {
    process.env.NODE_ENV = "test";
    const updated = await service.updateSettings(
      testWorkspaceId,
      {
        enabled: true,
        envAllowlist: ["test", "staging"],
        containmentMin: 0.85,
      },
      BigInt("101")
    );

    expect(updated.enabled).toBe(true);
    expect(updated.containmentMin).toBe(0.85);
  });

  it("blocks enabling autopilot in production without ADR override", async () => {
    process.env.NODE_ENV = "production";
    await expect(
      service.updateSettings(testWorkspaceId, { enabled: true })
    ).rejects.toThrow(/ADR-ENGAGEMENT-AUTOPILOT-PROD-GATE/);
  });

  it("allows enabling autopilot in production when ADR override is set", async () => {
    process.env.NODE_ENV = "production";
    process.env.ENGAGEMENT_AUTOPILOT_PROD_GATE_OVERRIDE = "true";

    const updated = await service.updateSettings(testWorkspaceId, {
      enabled: true,
      envAllowlist: ["test", "staging", "production"],
    });
    expect(updated.enabled).toBe(true);
  });

  it("activates emergency kill switch immediately", async () => {
    process.env.NODE_ENV = "test";
    await service.updateSettings(testWorkspaceId, { enabled: true });
    let current = await service.getSettings(testWorkspaceId);
    expect(current.enabled).toBe(true);

    const killed = await service.emergencyKillSwitch(testWorkspaceId, BigInt("102"));
    expect(killed.enabled).toBe(false);
  });

  it("trips kill switch on error threshold breach", async () => {
    process.env.NODE_ENV = "test";
    await service.updateSettings(testWorkspaceId, {
      enabled: true,
      errorMax: 0.1,
    });

    // Seed 12 runs with 3 failures (25% error rate > 10% threshold)
    for (let i = 0; i < 9; i++) {
      await service.recordRun(testWorkspaceId, {
        runId: `run_ok_${Date.now()}_${i}`,
        triggerRuleId: "r1",
        threadId: BigInt("1"),
        outcome: "completed",
      });
    }
    for (let i = 0; i < 3; i++) {
      await service.recordRun(testWorkspaceId, {
        runId: `run_fail_${Date.now()}_${i}`,
        triggerRuleId: "r1",
        threadId: BigInt("1"),
        outcome: "failed",
      });
    }

    const check = await service.checkThresholdBreach(testWorkspaceId);
    expect(check.tripped).toBe(true);
    expect(check.reason).toContain("error_rate_breached");

    const settingsAfter = await service.getSettings(testWorkspaceId);
    expect(settingsAfter.enabled).toBe(false);
  });
});
