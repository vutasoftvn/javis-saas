// M6 §4 — Cloud Continuity promotion/demotion advisor.
import { describe, expect, it } from "vitest";
import {
  resolveContinuityAction,
  ContinuityInput,
} from "../services/cloud-continuity.service";

function decide(over: Partial<ContinuityInput>) {
  return resolveContinuityAction({
    runtimeMode: "CLOUD_CONTINUITY",
    localPresence: "OFFLINE",
    cloudNodeAvailable: true,
    leaseHeldBy: "local",
    leaseExpired: true,
    failoverPolicy: "AUTO",
    syncFreshness: "FRESH",
    ...over,
  });
}

describe("cloud continuity advisor (M6 §4)", () => {
  it("non-CLOUD_CONTINUITY + local online ⇒ HOLD_LOCAL", () => {
    expect(decide({ runtimeMode: "REMOTE_ACCESS", localPresence: "ONLINE" }).action)
      .toBe("HOLD_LOCAL");
  });

  it("non-CLOUD_CONTINUITY + local offline ⇒ NO_RUNTIME (không failover cloud)", () => {
    const d = decide({ runtimeMode: "LOCAL_ONLY", localPresence: "OFFLINE" });
    expect(d.action).toBe("NO_RUNTIME");
    expect(d.reason).toMatch(/KHÔNG failover cloud/);
  });

  it("local online while cloud holds lease ⇒ DEMOTE_CLOUD", () => {
    expect(decide({ localPresence: "ONLINE", leaseHeldBy: "cloud" }).action)
      .toBe("DEMOTE_CLOUD");
  });

  it("local online holding lease ⇒ HOLD_LOCAL", () => {
    expect(decide({ localPresence: "ONLINE", leaseHeldBy: "local" }).action)
      .toBe("HOLD_LOCAL");
  });

  it("local offline but lease still valid ⇒ HOLD_LOCAL_LEASE", () => {
    expect(decide({ leaseExpired: false }).action).toBe("HOLD_LOCAL_LEASE");
  });

  it("MANUAL failover policy ⇒ MANUAL_REQUIRED", () => {
    expect(decide({ failoverPolicy: "MANUAL" }).action).toBe("MANUAL_REQUIRED");
  });

  it("sync not FRESH ⇒ HOLD_STALE", () => {
    expect(decide({ syncFreshness: "STALE" }).action).toBe("HOLD_STALE");
    expect(decide({ syncFreshness: "UNKNOWN" }).action).toBe("HOLD_STALE");
  });

  it("local offline + lease expired + FRESH + AUTO + cloud available ⇒ PROMOTE_CLOUD", () => {
    expect(decide({}).action).toBe("PROMOTE_CLOUD");
  });

  it("all conditions met but no cloud node ⇒ NO_RUNTIME", () => {
    expect(decide({ cloudNodeAvailable: false }).action).toBe("NO_RUNTIME");
  });
});
