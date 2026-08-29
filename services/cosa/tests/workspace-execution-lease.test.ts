// M6 §2 — WorkspaceExecutionLease + fencing (split-brain protection).
import { afterEach, describe, expect, it } from "vitest";
import { inArray } from "drizzle-orm";
import { db, schema } from "../models/db";
import {
  acquireWriteLease,
  promoteCloudRuntime,
  assertFencingTokenCurrent,
  heartbeatWriteLease,
  releaseWriteLease,
  setFailoverPolicy,
  getWriteLease,
} from "../services/workspace-execution-lease.service";

const { workspaceExecutionLeases } = schema;
const used: bigint[] = [];

function ws(): bigint {
  const id = BigInt(Date.now()) * 1000n + BigInt(Math.floor(Math.random() * 1000));
  used.push(id);
  return id;
}

afterEach(async () => {
  if (used.length) {
    await db
      .delete(workspaceExecutionLeases)
      .where(inArray(workspaceExecutionLeases.workspaceId, used.splice(0)));
  }
});

describe("workspace execution lease (M6 §2)", () => {
  it("first acquire ⇒ epoch 1 + fencing token; same node renews in place", async () => {
    const workspaceId = ws();
    const a = await acquireWriteLease({ workspaceId, nodeId: 111n });
    expect(a.leaseEpoch).toBe("1");
    expect(BigInt(a.fencingToken)).toBeGreaterThan(0n);

    const b = await acquireWriteLease({ workspaceId, nodeId: 111n });
    expect(b.leaseEpoch).toBe("1"); // renew, epoch không đổi
    expect(b.fencingToken).toBe(a.fencingToken);
  });

  it("another node cannot steal a live lease", async () => {
    const workspaceId = ws();
    await acquireWriteLease({ workspaceId, nodeId: 111n, ttlSec: 60 });
    await expect(
      acquireWriteLease({ workspaceId, nodeId: 222n })
    ).rejects.toMatchObject({ code: "failed_precondition" });
  });

  it("expired lease ⇒ another local node takes over with epoch+1 + new fencing token", async () => {
    const workspaceId = ws();
    const a = await acquireWriteLease({ workspaceId, nodeId: 111n, ttlSec: 60 });
    // force expiry
    await db
      .update(workspaceExecutionLeases)
      .set({ leaseExpiresAt: new Date(Date.now() - 1000) })
      .where(inArray(workspaceExecutionLeases.workspaceId, [workspaceId]));

    const b = await acquireWriteLease({ workspaceId, nodeId: 222n });
    expect(b.leaseEpoch).toBe("2");
    expect(BigInt(b.fencingToken)).toBeGreaterThan(BigInt(a.fencingToken));

    // stale fencing token của node cũ bị reject
    await expect(
      assertFencingTokenCurrent({ workspaceId, fencingToken: BigInt(a.fencingToken) })
    ).rejects.toMatchObject({ code: "aborted" });
    // token hiện hành OK
    const ok = await assertFencingTokenCurrent({
      workspaceId,
      fencingToken: BigInt(b.fencingToken),
    });
    expect(ok.leaseEpoch).toBe("2");
  });

  it("promoteCloudRuntime rejected while local lease is live", async () => {
    const workspaceId = ws();
    await acquireWriteLease({ workspaceId, nodeId: 111n, ttlSec: 60 });
    await expect(
      promoteCloudRuntime({ workspaceId, cloudNodeId: 999n, syncFreshness: "FRESH" })
    ).rejects.toMatchObject({ code: "failed_precondition" });
  });

  it("promoteCloudRuntime: expired local lease + FRESH sync + AUTO ⇒ cloud gets epoch+1", async () => {
    const workspaceId = ws();
    const a = await acquireWriteLease({ workspaceId, nodeId: 111n, ttlSec: 60 });
    await db
      .update(workspaceExecutionLeases)
      .set({ leaseExpiresAt: new Date(Date.now() - 1000) })
      .where(inArray(workspaceExecutionLeases.workspaceId, [workspaceId]));

    const c = await promoteCloudRuntime({
      workspaceId,
      cloudNodeId: 999n,
      syncFreshness: "FRESH",
    });
    expect(c.activeRuntimeRole).toBe("cloud_workspace_runtime");
    expect(c.leaseEpoch).toBe("2");
    expect(BigInt(c.fencingToken)).toBeGreaterThan(BigInt(a.fencingToken));
  });

  it("promoteCloudRuntime rejected when sync freshness not FRESH", async () => {
    const workspaceId = ws();
    await acquireWriteLease({ workspaceId, nodeId: 111n, ttlSec: 60 });
    await db
      .update(workspaceExecutionLeases)
      .set({ leaseExpiresAt: new Date(Date.now() - 1000) })
      .where(inArray(workspaceExecutionLeases.workspaceId, [workspaceId]));

    await expect(
      promoteCloudRuntime({ workspaceId, cloudNodeId: 999n, syncFreshness: "STALE" })
    ).rejects.toMatchObject({ code: "failed_precondition" });
  });

  it("MANUAL failover policy blocks autonomous cloud promotion", async () => {
    const workspaceId = ws();
    await acquireWriteLease({
      workspaceId,
      nodeId: 111n,
      ttlSec: 60,
      failoverPolicy: "MANUAL",
    });
    await db
      .update(workspaceExecutionLeases)
      .set({ leaseExpiresAt: new Date(Date.now() - 1000) })
      .where(inArray(workspaceExecutionLeases.workspaceId, [workspaceId]));

    await expect(
      promoteCloudRuntime({ workspaceId, cloudNodeId: 999n, syncFreshness: "FRESH" })
    ).rejects.toMatchObject({ code: "failed_precondition" });
  });

  it("local reclaim after cloud wrote ⇒ new epoch fences the cloud token", async () => {
    const workspaceId = ws();
    await acquireWriteLease({ workspaceId, nodeId: 111n, ttlSec: 60 });
    await db
      .update(workspaceExecutionLeases)
      .set({ leaseExpiresAt: new Date(Date.now() - 1000) })
      .where(inArray(workspaceExecutionLeases.workspaceId, [workspaceId]));
    const cloud = await promoteCloudRuntime({
      workspaceId,
      cloudNodeId: 999n,
      syncFreshness: "FRESH",
    });
    // cloud lease expires, local comes back
    await db
      .update(workspaceExecutionLeases)
      .set({ leaseExpiresAt: new Date(Date.now() - 1000) })
      .where(inArray(workspaceExecutionLeases.workspaceId, [workspaceId]));
    const local2 = await acquireWriteLease({ workspaceId, nodeId: 111n });
    expect(local2.leaseEpoch).toBe("3");

    await expect(
      assertFencingTokenCurrent({ workspaceId, fencingToken: BigInt(cloud.fencingToken) })
    ).rejects.toMatchObject({ code: "aborted" });
  });

  it("heartbeat with stale fencing token is fenced; release marks expired", async () => {
    const workspaceId = ws();
    const a = await acquireWriteLease({ workspaceId, nodeId: 111n });
    await expect(
      heartbeatWriteLease({ workspaceId, nodeId: 111n, fencingToken: 1n })
    ).rejects.toMatchObject({ code: "aborted" });

    const hb = await heartbeatWriteLease({
      workspaceId,
      nodeId: 111n,
      fencingToken: BigInt(a.fencingToken),
      syncCursor: "cursor-42",
    });
    expect(hb.lastSyncCursor).toBe("cursor-42");

    await releaseWriteLease({
      workspaceId,
      nodeId: 111n,
      fencingToken: BigInt(a.fencingToken),
    });
    const after = await getWriteLease(workspaceId);
    expect(after?.isExpired).toBe(true);
  });

  it("setFailoverPolicy flips AUTO↔MANUAL", async () => {
    const workspaceId = ws();
    await acquireWriteLease({ workspaceId, nodeId: 111n });
    await setFailoverPolicy({ workspaceId, policy: "MANUAL" });
    const v = await getWriteLease(workspaceId);
    expect(v?.failoverPolicy).toBe("MANUAL");
  });
});
