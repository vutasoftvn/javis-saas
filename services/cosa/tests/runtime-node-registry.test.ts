// M5 §1 — Runtime node registration + device key + heartbeat + computed presence.
import { afterEach, describe, expect, it } from "vitest";
import { inArray } from "drizzle-orm";
import { db, schema } from "../models/db";
import {
  registerRuntimeNode,
  heartbeatRuntimeNode,
  revokeRuntimeNode,
  listWorkspaceRuntimeNodes,
  assertNodeMayReceiveCommand,
  computePresence,
  PRESENCE_ONLINE_WITHIN_SEC,
  PRESENCE_DEGRADED_WITHIN_SEC,
} from "../services/runtime-node-registry.service";

const { workspaceRuntimeNodes } = schema;
const createdWorkspaces: bigint[] = [];

function ws(): bigint {
  const id = BigInt(Date.now()) * 1000n + BigInt(Math.floor(Math.random() * 1000));
  createdWorkspaces.push(id);
  return id;
}

afterEach(async () => {
  if (createdWorkspaces.length) {
    await db
      .delete(workspaceRuntimeNodes)
      .where(inArray(workspaceRuntimeNodes.workspaceId, createdWorkspaces.splice(0)));
  }
});

describe("runtime node registry (M5 §1)", () => {
  it("registers a node ONLINE with a minted snowflake node_id", async () => {
    const workspaceId = ws();
    const node = await registerRuntimeNode({
      workspaceId,
      deviceKeyFingerprint: "fp-abc",
      runtimeRole: "local_workspace_runtime",
      agentVersion: "1.2.3",
    });
    expect(node.nodeId).toMatch(/^\d+$/);
    expect(node.workspaceId).toBe(workspaceId.toString());
    expect(node.presence).toBe("ONLINE");
    expect(node.agentVersion).toBe("1.2.3");
  });

  it("register is idempotent per (workspace, fingerprint) — same node_id, refreshes version", async () => {
    const workspaceId = ws();
    const a = await registerRuntimeNode({
      workspaceId,
      deviceKeyFingerprint: "fp-1",
      runtimeRole: "local_workspace_runtime",
      agentVersion: "1.0.0",
    });
    const b = await registerRuntimeNode({
      workspaceId,
      deviceKeyFingerprint: "fp-1",
      runtimeRole: "local_workspace_runtime",
      agentVersion: "1.1.0",
    });
    expect(b.nodeId).toBe(a.nodeId);
    expect(b.agentVersion).toBe("1.1.0");

    const nodes = await listWorkspaceRuntimeNodes(workspaceId);
    expect(nodes).toHaveLength(1);
  });

  it("heartbeat requires matching device key fingerprint", async () => {
    const workspaceId = ws();
    const node = await registerRuntimeNode({
      workspaceId,
      deviceKeyFingerprint: "fp-real",
      runtimeRole: "local_workspace_runtime",
    });

    await expect(
      heartbeatRuntimeNode({
        nodeId: BigInt(node.nodeId),
        workspaceId,
        deviceKeyFingerprint: "fp-forged",
      })
    ).rejects.toMatchObject({ code: "permission_denied" });

    const ok = await heartbeatRuntimeNode({
      nodeId: BigInt(node.nodeId),
      workspaceId,
      deviceKeyFingerprint: "fp-real",
    });
    expect(ok.presence).toBe("ONLINE");
  });

  it("revoked node cannot heartbeat and is excluded from active list", async () => {
    const workspaceId = ws();
    const node = await registerRuntimeNode({
      workspaceId,
      deviceKeyFingerprint: "fp-x",
      runtimeRole: "local_workspace_runtime",
    });
    await revokeRuntimeNode({ nodeId: BigInt(node.nodeId), workspaceId });

    await expect(
      heartbeatRuntimeNode({
        nodeId: BigInt(node.nodeId),
        workspaceId,
        deviceKeyFingerprint: "fp-x",
      })
    ).rejects.toMatchObject({ code: "permission_denied" });

    expect(await listWorkspaceRuntimeNodes(workspaceId)).toHaveLength(0);
    expect(await listWorkspaceRuntimeNodes(workspaceId, { includeRevoked: true })).toHaveLength(1);

    // Đăng ký lại sau khi thu hồi ⇒ node MỚI (fingerprint cũ giờ không đụng unique partial index).
    const fresh = await registerRuntimeNode({
      workspaceId,
      deviceKeyFingerprint: "fp-x",
      runtimeRole: "local_workspace_runtime",
    });
    expect(fresh.nodeId).not.toBe(node.nodeId);
  });

  it("assertNodeMayReceiveCommand: unregistered / wrong key / offline all rejected", async () => {
    const workspaceId = ws();
    const node = await registerRuntimeNode({
      workspaceId,
      deviceKeyFingerprint: "fp-cmd",
      runtimeRole: "local_workspace_runtime",
    });

    // unknown node
    await expect(
      assertNodeMayReceiveCommand({
        nodeId: 999999999999n,
        workspaceId,
        deviceKeyFingerprint: "fp-cmd",
      })
    ).rejects.toMatchObject({ code: "permission_denied" });

    // wrong key
    await expect(
      assertNodeMayReceiveCommand({
        nodeId: BigInt(node.nodeId),
        workspaceId,
        deviceKeyFingerprint: "nope",
      })
    ).rejects.toMatchObject({ code: "permission_denied" });

    // fresh heartbeat ⇒ eligible
    const elig = await assertNodeMayReceiveCommand({
      nodeId: BigInt(node.nodeId),
      workspaceId,
      deviceKeyFingerprint: "fp-cmd",
    });
    expect(elig.presence).toBe("ONLINE");

    // simulate stale heartbeat ⇒ OFFLINE ⇒ failed_precondition
    await db
      .update(workspaceRuntimeNodes)
      .set({ lastHeartbeatAt: new Date(Date.now() - 10 * 60 * 1000) })
      .where(inArray(workspaceRuntimeNodes.nodeId, [BigInt(node.nodeId)]));
    await expect(
      assertNodeMayReceiveCommand({
        nodeId: BigInt(node.nodeId),
        workspaceId,
        deviceKeyFingerprint: "fp-cmd",
      })
    ).rejects.toMatchObject({ code: "failed_precondition" });
  });

  it("computePresence windows: fresh=ONLINE, mid=DEGRADED, stale/revoked/never=OFFLINE", () => {
    const now = new Date();
    const fresh = new Date(now.getTime() - (PRESENCE_ONLINE_WITHIN_SEC - 5) * 1000);
    const mid = new Date(now.getTime() - (PRESENCE_DEGRADED_WITHIN_SEC - 5) * 1000);
    const stale = new Date(now.getTime() - (PRESENCE_DEGRADED_WITHIN_SEC + 60) * 1000);
    expect(computePresence(fresh, null, now)).toBe("ONLINE");
    expect(computePresence(mid, null, now)).toBe("DEGRADED");
    expect(computePresence(stale, null, now)).toBe("OFFLINE");
    expect(computePresence(null, null, now)).toBe("OFFLINE");
    expect(computePresence(fresh, now, now)).toBe("OFFLINE"); // revoked
  });
});
