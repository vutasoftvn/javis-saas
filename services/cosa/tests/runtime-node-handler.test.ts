// M5 §1 + §3 HTTP surface — register / heartbeat / revoke / list / route.
import { afterEach, describe, expect, it } from "vitest";
import { inArray } from "drizzle-orm";
import { db, schema } from "../models/db";
import { signWorkerServiceToken } from "../services/token.service";
import {
  registerRuntimeNodeEndpoint,
  heartbeatRuntimeNodeEndpoint,
  revokeRuntimeNodeEndpoint,
  listRuntimeNodesEndpoint,
  resolveRuntimeRouteEndpoint,
} from "../handlers/runtime-node.handler";

const { workspaceRuntimeNodes } = schema;
const usedWorkspaces: bigint[] = [];

function ws(): string {
  const id = BigInt(Date.now()) * 1000n + BigInt(Math.floor(Math.random() * 1000));
  usedWorkspaces.push(id);
  return id.toString();
}

function bearer(workspaceId: string): string {
  return `Bearer ${signWorkerServiceToken("local-node-worker", workspaceId)}`;
}

afterEach(async () => {
  if (usedWorkspaces.length) {
    await db
      .delete(workspaceRuntimeNodes)
      .where(inArray(workspaceRuntimeNodes.workspaceId, usedWorkspaces.splice(0)));
  }
});

describe("runtime node HTTP surface (M5 §1/§3)", () => {
  it("register requires a worker token scoped to the workspace", async () => {
    const workspaceId = ws();
    await expect(
      registerRuntimeNodeEndpoint({
        workspaceId,
        deviceKeyFingerprint: "fp",
        runtimeRole: "local_workspace_runtime",
        authorization: bearer("999999"), // wrong workspace
      })
    ).rejects.toMatchObject({ code: "permission_denied" });

    await expect(
      registerRuntimeNodeEndpoint({
        workspaceId,
        deviceKeyFingerprint: "fp",
        runtimeRole: "local_workspace_runtime",
      })
    ).rejects.toThrow(/authorization/i);
  });

  it("register → heartbeat → list round trip", async () => {
    const workspaceId = ws();
    const auth = bearer(workspaceId);
    const node = await registerRuntimeNodeEndpoint({
      workspaceId,
      deviceKeyFingerprint: "fp-1",
      runtimeRole: "local_workspace_runtime",
      agentVersion: "2.0.0",
      authorization: auth,
    });
    expect(node.presence).toBe("ONLINE");

    const hb = await heartbeatRuntimeNodeEndpoint({
      nodeId: node.nodeId,
      workspaceId,
      deviceKeyFingerprint: "fp-1",
      authorization: auth,
    });
    expect(hb.presence).toBe("ONLINE");

    const list = await listRuntimeNodesEndpoint({ workspaceId, authorization: auth });
    expect(list.nodes).toHaveLength(1);
    expect(list.nodes[0].nodeId).toBe(node.nodeId);
  });

  it("revoked node drops from list and cannot heartbeat", async () => {
    const workspaceId = ws();
    const auth = bearer(workspaceId);
    const node = await registerRuntimeNodeEndpoint({
      workspaceId,
      deviceKeyFingerprint: "fp-2",
      runtimeRole: "local_workspace_runtime",
      authorization: auth,
    });
    await revokeRuntimeNodeEndpoint({ nodeId: node.nodeId, workspaceId, authorization: auth });

    const list = await listRuntimeNodesEndpoint({ workspaceId, authorization: auth });
    expect(list.nodes).toHaveLength(0);

    await expect(
      heartbeatRuntimeNodeEndpoint({
        nodeId: node.nodeId,
        workspaceId,
        deviceKeyFingerprint: "fp-2",
        authorization: auth,
      })
    ).rejects.toMatchObject({ code: "permission_denied" });
  });

  it("route: REMOTE_ACCESS + local node ONLINE ⇒ LOCAL_RELAY", async () => {
    const workspaceId = ws();
    const auth = bearer(workspaceId);
    await registerRuntimeNodeEndpoint({
      workspaceId,
      deviceKeyFingerprint: "fp-r",
      runtimeRole: "local_workspace_runtime",
      authorization: auth,
    });
    const d = await resolveRuntimeRouteEndpoint({
      workspaceId,
      runtimeMode: "REMOTE_ACCESS",
      authorization: auth,
    });
    expect(d.target).toBe("LOCAL_RELAY");
    expect(d.cloudConsidered).toBe(false);
  });

  it("route: REMOTE_ACCESS + no registered local node ⇒ OFFLINE (không cloud-failover)", async () => {
    const workspaceId = ws();
    const auth = bearer(workspaceId);
    const d = await resolveRuntimeRouteEndpoint({
      workspaceId,
      runtimeMode: "REMOTE_ACCESS",
      authorization: auth,
    });
    expect(d.target).toBe("OFFLINE");
    expect(d.cloudConsidered).toBe(false);
  });

  it("route: REMOTE_ACCESS + local node stale heartbeat ⇒ OFFLINE", async () => {
    const workspaceId = ws();
    const auth = bearer(workspaceId);
    const node = await registerRuntimeNodeEndpoint({
      workspaceId,
      deviceKeyFingerprint: "fp-s",
      runtimeRole: "local_workspace_runtime",
      authorization: auth,
    });
    await db
      .update(workspaceRuntimeNodes)
      .set({ lastHeartbeatAt: new Date(Date.now() - 10 * 60 * 1000) })
      .where(inArray(workspaceRuntimeNodes.nodeId, [BigInt(node.nodeId)]));

    const d = await resolveRuntimeRouteEndpoint({
      workspaceId,
      runtimeMode: "REMOTE_ACCESS",
      authorization: auth,
    });
    expect(d.target).toBe("OFFLINE");
  });
});
