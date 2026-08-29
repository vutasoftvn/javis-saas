// M5 §3 — Runtime Router decision core.
import { describe, expect, it } from "vitest";
import {
  resolveRuntimeRoute,
  RuntimeRouteInput,
} from "../services/runtime-router.service";

const ONLINE = { presence: "ONLINE" as const, hasValidLease: true };
const OFFLINE_NODE = { presence: "OFFLINE" as const, hasValidLease: false };

function route(over: Partial<RuntimeRouteInput>) {
  return resolveRuntimeRoute({
    runtimeMode: "REMOTE_ACCESS",
    membershipValid: true,
    localNode: ONLINE,
    ...over,
  });
}

describe("runtime router (M5 §3)", () => {
  it("non-member ⇒ DENIED regardless of node state", () => {
    expect(route({ membershipValid: false }).target).toBe("DENIED");
  });

  it("LOCAL_ONLY + local up ⇒ LOCAL_DIRECT", () => {
    expect(route({ runtimeMode: "LOCAL_ONLY" }).target).toBe("LOCAL_DIRECT");
  });

  it("LOCAL_ONLY + local down ⇒ OFFLINE", () => {
    const d = route({ runtimeMode: "LOCAL_ONLY", localNode: OFFLINE_NODE });
    expect(d.target).toBe("OFFLINE");
    expect(d.cloudConsidered).toBe(false);
  });

  it("REMOTE_ACCESS + local up ⇒ LOCAL_RELAY, KHÔNG cân nhắc cloud", () => {
    const d = route({});
    expect(d.target).toBe("LOCAL_RELAY");
    expect(d.cloudConsidered).toBe(false);
  });

  it("REMOTE_ACCESS + local offline ⇒ OFFLINE, KHÔNG failover cloud (guardrail 7)", () => {
    const d = route({ localNode: OFFLINE_NODE, cloudNode: ONLINE });
    expect(d.target).toBe("OFFLINE");
    expect(d.cloudConsidered).toBe(false);
  });

  it("REMOTE_ACCESS + no registered local node ⇒ OFFLINE", () => {
    const d = route({ localNode: null });
    expect(d.target).toBe("OFFLINE");
    expect(d.reason).toMatch(/chưa có local runtime node/);
  });

  it("REMOTE_ACCESS + local DEGRADED ⇒ LOCAL_RELAY nhưng degraded=true", () => {
    const d = route({ localNode: { presence: "DEGRADED", hasValidLease: true } });
    expect(d.target).toBe("LOCAL_RELAY");
    expect(d.degraded).toBe(true);
  });

  it("REMOTE_ACCESS + local ONLINE nhưng thiếu lease ⇒ OFFLINE", () => {
    const d = route({ localNode: { presence: "ONLINE", hasValidLease: false } });
    expect(d.target).toBe("OFFLINE");
  });

  it("CLOUD_CONTINUITY + local up ⇒ LOCAL_RELAY (ưu tiên local), cloudConsidered=true", () => {
    const d = route({ runtimeMode: "CLOUD_CONTINUITY" });
    expect(d.target).toBe("LOCAL_RELAY");
    expect(d.cloudConsidered).toBe(true);
  });

  it("CLOUD_CONTINUITY + local down + cloud up ⇒ CLOUD_ISOLATED", () => {
    const d = route({
      runtimeMode: "CLOUD_CONTINUITY",
      localNode: OFFLINE_NODE,
      cloudNode: ONLINE,
    });
    expect(d.target).toBe("CLOUD_ISOLATED");
  });

  it("CLOUD_CONTINUITY + cloud up + sync STALE ⇒ CLOUD_ISOLATED degraded", () => {
    const d = route({
      runtimeMode: "CLOUD_CONTINUITY",
      localNode: OFFLINE_NODE,
      cloudNode: ONLINE,
      syncFreshness: "STALE",
    });
    expect(d.target).toBe("CLOUD_ISOLATED");
    expect(d.degraded).toBe(true);
  });

  it("CLOUD_CONTINUITY + both down ⇒ OFFLINE", () => {
    const d = route({
      runtimeMode: "CLOUD_CONTINUITY",
      localNode: OFFLINE_NODE,
      cloudNode: OFFLINE_NODE,
    });
    expect(d.target).toBe("OFFLINE");
  });
});
