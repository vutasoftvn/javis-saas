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
      .where(inArray(workspaceExecutionLeases.organizationId, used.splice(0)));
  }
});

describe("workspace execution lease (M6 §2)", () => {
  it("first acquire ⇒ epoch 1 + fencing token; same node renews in place", async () => {
    const organizationId = ws();
    const a = await acquireWriteLease({ organizationId: organizationId, nodeId: 111n });
    expect(a.leaseEpoch).toBe("1");
    expect(BigInt(a.fencingToken)).toBeGreaterThan(0n);

    const b = await acquireWriteLease({ organizationId: organizationId, nodeId: 111n });
    expect(b.leaseEpoch).toBe("1"); // renew, epoch không đổi
    expect(b.fencingToken).toBe(a.fencingToken);
  });

  it("another node cannot steal a live lease", async () => {
    const organizationId = ws();
    await acquireWriteLease({ organizationId: organizationId, nodeId: 111n, ttlSec: 60 });
    await expect(
      acquireWriteLease({ organizationId: organizationId, nodeId: 222n })
    ).rejects.toMatchObject({ code: "failed_precondition" });
  });

  it("expired lease ⇒ another local node takes over with epoch+1 + new fencing token", async () => {
    const organizationId = ws();
    const a = await acquireWriteLease({ organizationId: organizationId, nodeId: 111n, ttlSec: 60 });
    // force expiry
    await db
      .update(workspaceExecutionLeases)
      .set({ leaseExpiresAt: new Date(Date.now() - 1000) })
      .where(inArray(workspaceExecutionLeases.organizationId, [organizationId]));

    const b = await acquireWriteLease({ organizationId: organizationId, nodeId: 222n });
    expect(b.leaseEpoch).toBe("2");
    expect(BigInt(b.fencingToken)).toBeGreaterThan(BigInt(a.fencingToken));

    // stale fencing token của node cũ bị reject
    await expect(
      assertFencingTokenCurrent({ organizationId: organizationId, fencingToken: BigInt(a.fencingToken) })
    ).rejects.toMatchObject({ code: "aborted" });
    // token hiện hành OK
    const ok = await assertFencingTokenCurrent({
      organizationId: organizationId,
      fencingToken: BigInt(b.fencingToken),
    });
    expect(ok.leaseEpoch).toBe("2");
  });

  it("promoteCloudRuntime rejected while local lease is live", async () => {
    const organizationId = ws();
    await acquireWriteLease({ organizationId: organizationId, nodeId: 111n, ttlSec: 60 });
    await expect(
      promoteCloudRuntime({ organizationId: organizationId, cloudNodeId: 999n, syncFreshness: "FRESH" })
    ).rejects.toMatchObject({ code: "failed_precondition" });
  });

  it("promoteCloudRuntime: expired local lease + FRESH sync + AUTO ⇒ cloud gets epoch+1", async () => {
    const organizationId = ws();
    const a = await acquireWriteLease({ organizationId: organizationId, nodeId: 111n, ttlSec: 60 });
    await db
      .update(workspaceExecutionLeases)
      .set({ leaseExpiresAt: new Date(Date.now() - 1000) })
      .where(inArray(workspaceExecutionLeases.organizationId, [organizationId]));

    const c = await promoteCloudRuntime({
      organizationId: organizationId,
      cloudNodeId: 999n,
      syncFreshness: "FRESH",
    });
    expect(c.activeRuntimeRole).toBe("cloud_workspace_runtime");
    expect(c.leaseEpoch).toBe("2");
    expect(BigInt(c.fencingToken)).toBeGreaterThan(BigInt(a.fencingToken));
  });

  it("promoteCloudRuntime rejected when sync freshness not FRESH", async () => {
    const organizationId = ws();
    await acquireWriteLease({ organizationId: organizationId, nodeId: 111n, ttlSec: 60 });
    await db
      .update(workspaceExecutionLeases)
      .set({ leaseExpiresAt: new Date(Date.now() - 1000) })
      .where(inArray(workspaceExecutionLeases.organizationId, [organizationId]));

    await expect(
      promoteCloudRuntime({ organizationId: organizationId, cloudNodeId: 999n, syncFreshness: "STALE" })
    ).rejects.toMatchObject({ code: "failed_precondition" });
  });

  it("MANUAL failover policy blocks autonomous cloud promotion", async () => {
    const organizationId = ws();
    await acquireWriteLease({
      organizationId: organizationId,
      nodeId: 111n,
      ttlSec: 60,
      failoverPolicy: "MANUAL",
    });
    await db
      .update(workspaceExecutionLeases)
      .set({ leaseExpiresAt: new Date(Date.now() - 1000) })
      .where(inArray(workspaceExecutionLeases.organizationId, [organizationId]));

    await expect(
      promoteCloudRuntime({ organizationId: organizationId, cloudNodeId: 999n, syncFreshness: "FRESH" })
    ).rejects.toMatchObject({ code: "failed_precondition" });
  });

  it("local reclaim after cloud wrote ⇒ new epoch fences the cloud token", async () => {
    const organizationId = ws();
    await acquireWriteLease({ organizationId: organizationId, nodeId: 111n, ttlSec: 60 });
    await db
      .update(workspaceExecutionLeases)
      .set({ leaseExpiresAt: new Date(Date.now() - 1000) })
      .where(inArray(workspaceExecutionLeases.organizationId, [organizationId]));
    const cloud = await promoteCloudRuntime({
      organizationId: organizationId,
      cloudNodeId: 999n,
      syncFreshness: "FRESH",
    });
    // cloud lease expires, local comes back
    await db
      .update(workspaceExecutionLeases)
      .set({ leaseExpiresAt: new Date(Date.now() - 1000) })
      .where(inArray(workspaceExecutionLeases.organizationId, [organizationId]));
    const local2 = await acquireWriteLease({ organizationId: organizationId, nodeId: 111n });
    expect(local2.leaseEpoch).toBe("3");

    await expect(
      assertFencingTokenCurrent({ organizationId: organizationId, fencingToken: BigInt(cloud.fencingToken) })
    ).rejects.toMatchObject({ code: "aborted" });
  });

  it("heartbeat with stale fencing token is fenced; release marks expired", async () => {
    const organizationId = ws();
    const a = await acquireWriteLease({ organizationId: organizationId, nodeId: 111n });
    await expect(
      heartbeatWriteLease({ organizationId: organizationId, nodeId: 111n, fencingToken: 1n })
    ).rejects.toMatchObject({ code: "aborted" });

    const hb = await heartbeatWriteLease({
      organizationId: organizationId,
      nodeId: 111n,
      fencingToken: BigInt(a.fencingToken),
      syncCursor: "cursor-42",
    });
    expect(hb.lastSyncCursor).toBe("cursor-42");

    await releaseWriteLease({
      organizationId: organizationId,
      nodeId: 111n,
      fencingToken: BigInt(a.fencingToken),
    });
    const after = await getWriteLease(organizationId);
    expect(after?.isExpired).toBe(true);
  });

  it("setFailoverPolicy flips AUTO↔MANUAL", async () => {
    const organizationId = ws();
    await acquireWriteLease({ organizationId: organizationId, nodeId: 111n });
    await setFailoverPolicy({ organizationId: organizationId, policy: "MANUAL" });
    const v = await getWriteLease(organizationId);
    expect(v?.failoverPolicy).toBe("MANUAL");
  });
});
