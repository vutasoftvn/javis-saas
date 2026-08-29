import { api, Header, APIError } from "encore.dev/api";
import { requireWorkerServiceAuth } from "../services/token.service";
import {
  registerRuntimeNode,
  heartbeatRuntimeNode,
  revokeRuntimeNode,
  listWorkspaceRuntimeNodes,
  RuntimeNodeView,
  RuntimeRole,
} from "../services/runtime-node-registry.service";
import {
  resolveRuntimeRoute,
  RouteDecision,
  RuntimeMode,
  SyncFreshness,
} from "../services/runtime-router.service";

// M5 §1 + §3 HTTP surface.
//
// Local Workspace Runtime Node xác thực bằng WORKER-SERVICE token (device holds a
// service token scoped tới workspace của nó) + trình `device_key_fingerprint`.
// Token `workspaceId` claim PHẢI khớp `workspaceId` trong request — đó là
// assertion membership ở tầng control-plane (membership người dùng do
// services/company chịu trách nhiệm).

function assertWorkspaceScopedWorker(
  authorization: string | undefined,
  workspaceId: string
): void {
  const payload = requireWorkerServiceAuth(authorization);
  const claim = (payload as { workspaceId?: string }).workspaceId;
  if (!claim || claim !== workspaceId) {
    throw APIError.permissionDenied("worker token không được scope tới workspace này");
  }
}

// ── POST /cosa/runtime/nodes/register ──

export interface RegisterRuntimeNodeParamsHttp {
  authorization?: Header<"Authorization">;
  workspaceId: string;
  deviceKeyFingerprint: string;
  runtimeRole: RuntimeRole;
  agentVersion?: string;
}

export const registerRuntimeNodeEndpoint = api(
  { method: "POST", path: "/cosa/runtime/nodes/register", expose: true },
  async (p: RegisterRuntimeNodeParamsHttp): Promise<RuntimeNodeView> => {
    assertWorkspaceScopedWorker(p.authorization, p.workspaceId);
    return registerRuntimeNode({
      workspaceId: BigInt(p.workspaceId),
      deviceKeyFingerprint: p.deviceKeyFingerprint,
      runtimeRole: p.runtimeRole,
      agentVersion: p.agentVersion,
    });
  }
);

// ── POST /cosa/runtime/nodes/heartbeat ──

export interface HeartbeatRuntimeNodeParamsHttp {
  authorization?: Header<"Authorization">;
  nodeId: string;
  workspaceId: string;
  deviceKeyFingerprint: string;
  agentVersion?: string;
}

export const heartbeatRuntimeNodeEndpoint = api(
  { method: "POST", path: "/cosa/runtime/nodes/heartbeat", expose: true },
  async (p: HeartbeatRuntimeNodeParamsHttp): Promise<RuntimeNodeView> => {
    assertWorkspaceScopedWorker(p.authorization, p.workspaceId);
    return heartbeatRuntimeNode({
      nodeId: BigInt(p.nodeId),
      workspaceId: BigInt(p.workspaceId),
      deviceKeyFingerprint: p.deviceKeyFingerprint,
      agentVersion: p.agentVersion,
    });
  }
);

// ── POST /cosa/runtime/nodes/revoke ──

export interface RevokeRuntimeNodeParamsHttp {
  authorization?: Header<"Authorization">;
  nodeId: string;
  workspaceId: string;
}

export const revokeRuntimeNodeEndpoint = api(
  { method: "POST", path: "/cosa/runtime/nodes/revoke", expose: true },
  async (p: RevokeRuntimeNodeParamsHttp): Promise<{ ok: true }> => {
    assertWorkspaceScopedWorker(p.authorization, p.workspaceId);
    await revokeRuntimeNode({ nodeId: BigInt(p.nodeId), workspaceId: BigInt(p.workspaceId) });
    return { ok: true };
  }
);

// ── GET /cosa/runtime/nodes ──

export interface ListRuntimeNodesParamsHttp {
  authorization?: Header<"Authorization">;
  workspaceId: string;
  includeRevoked?: boolean;
}

export interface ListRuntimeNodesResponse {
  nodes: RuntimeNodeView[];
}

export const listRuntimeNodesEndpoint = api(
  { method: "GET", path: "/cosa/runtime/nodes", expose: true },
  async (p: ListRuntimeNodesParamsHttp): Promise<ListRuntimeNodesResponse> => {
    assertWorkspaceScopedWorker(p.authorization, p.workspaceId);
    const nodes = await listWorkspaceRuntimeNodes(BigInt(p.workspaceId), {
      includeRevoked: p.includeRevoked,
    });
    return { nodes };
  }
);

// ── POST /cosa/runtime/route ── (M5 §3 wiring)
//
// `runtimeMode` do caller truyền (đọc từ services/company workspace record —
// authoritative ở đó). Endpoint resolve local node presence từ registry rồi gọi
// `resolveRuntimeRoute`. Không tự fetch company ở M5 (adapter cross-service để
// phiên sau).

export interface ResolveRouteParamsHttp {
  authorization?: Header<"Authorization">;
  workspaceId: string;
  runtimeMode: RuntimeMode;
  syncFreshness?: SyncFreshness;
}

export const resolveRuntimeRouteEndpoint = api(
  { method: "POST", path: "/cosa/runtime/route", expose: true },
  async (p: ResolveRouteParamsHttp): Promise<RouteDecision> => {
    assertWorkspaceScopedWorker(p.authorization, p.workspaceId);

    const nodes = await listWorkspaceRuntimeNodes(BigInt(p.workspaceId));
    const local =
      nodes.find((n) => n.runtimeRole === "local_workspace_runtime") ?? null;
    const cloud =
      nodes.find((n) => n.runtimeRole === "cloud_workspace_runtime") ?? null;

    // M5: node đã đăng ký + presence != OFFLINE ⇒ coi như đang giữ runtime lease
    // (per-run lease promotion/demotion là M6).
    const toNodeInput = (n: RuntimeNodeView | null) =>
      n ? { presence: n.presence, hasValidLease: n.presence !== "OFFLINE" } : null;

    return resolveRuntimeRoute({
      runtimeMode: p.runtimeMode,
      membershipValid: true, // đã assert qua worker token scope ở trên
      localNode: toNodeInput(local),
      cloudNode: toNodeInput(cloud),
      syncFreshness: p.syncFreshness,
    });
  }
);
