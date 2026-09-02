import { beforeAll, describe, expect, it } from "vitest";
import { eq } from "drizzle-orm";
import { registerPlatformUser } from "../services/auth.service";
import { provisionVentureWorkspace } from "../services/venture-workspace.service";
import { signPlatformToken, signWorkerServiceToken } from "../services/token.service";
import { registerRuntimeNode } from "../services/runtime-node-registry.service";
import { db, schema } from "../models/db";
import {
  getWorkspaceSessionContext,
  installWorkspaceConnector,
  listWorkspaceAuditEvents,
  listWorkspaceConnectors,
  listWorkspaceMembers,
  listWorkspaceRuntimeNodes,
  putWorkspaceSkillPolicy,
  revokeWorkspaceConnector,
} from "../handlers/workspace-settings.handler";

describe("Workspace Settings Endpoints", () => {
  let userId: string;
  let workspaceId: string;
  let validToken: string;

  beforeAll(async () => {
    const email = `settings-user-${Date.now()}@test.io`;
    const reg = await registerPlatformUser({
      email,
      password: "SecurePassword123",
      workspace_name: "Settings Test Venture",
    });
    userId = reg.user!.id;
    workspaceId = reg.platform_workspace_id!;
    validToken = reg.access_token;
  });

  it("lists workspace members truthfully", async () => {
    const res = await listWorkspaceMembers({
      workspaceId,
      authorization: `Bearer ${validToken}`,
    });
    expect(res.meta.dataState).toBe("populated");
    expect(res.data.length).toBeGreaterThanOrEqual(1);
    expect(res.data[0].roleId).toBe("founder");
  });

  it("handles connector installation, list and revocation without exposing secrets", async () => {
    // 1. Initially connectors list is empty
    const initList = await listWorkspaceConnectors({
      workspaceId,
      authorization: `Bearer ${validToken}`,
    });
    expect(initList.data).toEqual([]);
    expect(initList.meta.dataState).toBe("empty");

    // 2. Install connector
    const installRes = await installWorkspaceConnector({
      workspaceId,
      connectorKey: "google-drive",
      authorization: `Bearer ${validToken}`,
    });
    expect(installRes.data.connectorKey).toBe("google-drive");
    expect(installRes.data.state).toBe("enabled");
    expect(JSON.stringify(installRes)).not.toContain("secret");

    // 3. List connectors shows installed
    const listAfter = await listWorkspaceConnectors({
      workspaceId,
      authorization: `Bearer ${validToken}`,
    });
    expect(listAfter.data.length).toBe(1);
    expect(listAfter.data[0].connectorKey).toBe("google-drive");

    // 4. Revoke connector
    const revokeRes = await revokeWorkspaceConnector({
      workspaceId,
      connectorKey: "google-drive",
      authorization: `Bearer ${validToken}`,
    });
    expect(revokeRes.data.state).toBe("revoked");

    // 5. Audit events recorded installation and revocation
    const auditRes = await listWorkspaceAuditEvents({
      workspaceId,
      authorization: `Bearer ${validToken}`,
    });
    expect(auditRes.data.length).toBeGreaterThanOrEqual(2);
    expect(auditRes.data[0].targetKind).toBe("connector");
  });

  it("lists runtime nodes truthfully", async () => {
    const res = await listWorkspaceRuntimeNodes({
      workspaceId,
      authorization: `Bearer ${validToken}`,
    });
    expect(res.data).toBeDefined();
    expect(res.meta.sources[0].kind).toBe("control_plane");
  });

  it("rejects worker token on human settings route", async () => {
    const workerToken = signWorkerServiceToken("worker_1", workspaceId);
    await expect(
      listWorkspaceMembers({
        workspaceId,
        authorization: `Bearer ${workerToken}`,
      })
    ).rejects.toThrow(/invalid or expired platform token|unauthenticated/i);
  });
});

// Task 4 — Persist Workspace Skill Policy tại COSA Control Plane.
describe("Workspace Skill Policy Endpoints (Task 4)", () => {
  let founderToken: string;
  let workspaceId: string;
  let outsiderToken: string;

  beforeAll(async () => {
    const email = `skill-policy-founder-${Date.now()}@test.io`;
    const reg = await registerPlatformUser({
      email,
      password: "SecurePassword123",
      workspace_name: "Skill Policy Test Venture",
    });
    workspaceId = reg.platform_workspace_id!;
    founderToken = reg.access_token;

    // Người dùng khác, không thuộc workspace trên — dùng để test rejection.
    const outsiderEmail = `skill-policy-outsider-${Date.now()}@test.io`;
    const outsiderReg = await registerPlatformUser({
      email: outsiderEmail,
      password: "SecurePassword123",
      workspace_name: "Outsider Venture",
    });
    outsiderToken = outsiderReg.access_token;
  });

  it("persists a skill policy and increments revision", async () => {
    const first = await putWorkspaceSkillPolicy({
      workspaceId,
      skillKey: "lead_enricher",
      authorization: `Bearer ${founderToken}`,
      enabled: true,
      config: {},
    });
    expect(first.data.revision).toBe(1);
    expect(first.data.skillKey).toBe("lead_enricher");
    expect(first.meta.sources[0].kind).toBe("control_plane");

    const second = await putWorkspaceSkillPolicy({
      workspaceId,
      skillKey: "lead_enricher",
      authorization: `Bearer ${founderToken}`,
      enabled: false,
      config: {},
    });
    expect(second.data.revision).toBe(first.data.revision + 1);
    expect(second.data.enabled).toBe(false);
  });

  it("rejects a non-member mutation", async () => {
    await expect(
      putWorkspaceSkillPolicy({
        workspaceId,
        authorization: `Bearer ${outsiderToken}`,
        skillKey: "lead_enricher",
        enabled: true,
        config: {},
      })
    ).rejects.toThrow(/permission/i);
  });

  it("records an audit event on every skill policy mutation", async () => {
    await putWorkspaceSkillPolicy({
      workspaceId,
      skillKey: "growth_hacking",
      authorization: `Bearer ${founderToken}`,
      enabled: true,
      config: { max_autonomy: "supervised" },
    });

    const auditRes = await listWorkspaceAuditEvents({
      workspaceId,
      authorization: `Bearer ${founderToken}`,
    });

    const skillPolicyEvent = auditRes.data.find((e) => e.targetKind === "skill_policy" && e.targetId === "growth_hacking");
    expect(skillPolicyEvent).toBeDefined();
    expect(skillPolicyEvent!.eventType).toBe("skill_policy.updated");
  });
});

// Task 3 (Frontend Trust and UX Hardening) — GET .../session-context phải là
// nguồn sự thật DUY NHẤT cho workspace/role/runtimeMode/presence: server tự
// tính lại mọi giá trị, không nhận runtimeMode/role/presence từ request.
describe("Workspace Session Context Endpoint (Task 3 — Frontend Trust and UX Hardening)", () => {
  let founderToken: string;
  let workspaceId: string;
  let outsiderToken: string;

  beforeAll(async () => {
    const email = `session-context-founder-${Date.now()}@test.io`;
    const reg = await registerPlatformUser({
      email,
      password: "SecurePassword123",
      workspace_name: "Session Context Test Venture",
    });
    workspaceId = reg.platform_workspace_id!;
    founderToken = reg.access_token;

    const outsiderEmail = `session-context-outsider-${Date.now()}@test.io`;
    const outsiderReg = await registerPlatformUser({
      email: outsiderEmail,
      password: "SecurePassword123",
      workspace_name: "Session Context Outsider Venture",
    });
    outsiderToken = outsiderReg.access_token;
  });

  it("returns only the authenticated member workspace session context", async () => {
    const ctx = await getWorkspaceSessionContext({
      workspaceId,
      authorization: `Bearer ${founderToken}`,
    });

    expect(ctx.workspaceId).toBe(workspaceId);
    expect(ctx.role).toBe("founder");
    expect(ctx.asOf).toMatch(/Z$/);
    // Chưa đăng ký runtime node nào ⇒ mặc định trung thực LOCAL_ONLY/OFFLINE,
    // không suy diễn ra một cloud target ngầm nào.
    expect(ctx.runtimeMode).toBe("LOCAL_ONLY");
    expect(ctx.presenceStatus).toBe("OFFLINE");
    expect(ctx.lastHeartbeatAt).toBeNull();
  });

  it("denies a member of another workspace", async () => {
    await expect(
      getWorkspaceSessionContext({
        workspaceId,
        authorization: `Bearer ${outsiderToken}`,
      })
    ).rejects.toThrow(/permission/i);
  });

  it("reports REMOTE_ACCESS/OFFLINE when the local runtime node is registered but unreachable — no implicit cloud target", async () => {
    const node = await registerRuntimeNode({
      workspaceId: BigInt(workspaceId),
      deviceKeyFingerprint: `session-context-device-${Date.now()}`,
      runtimeRole: "local_workspace_runtime",
    });

    // Giả lập heartbeat đã quá cũ (vượt ngưỡng DEGRADED 120s) bằng cách ghi
    // thẳng xuống DB thật — presence hiệu lực phải được TÍNH LẠI ở service
    // theo độ tươi của lastHeartbeatAt, không đọc thẳng cột presence_status.
    const staleHeartbeat = new Date(Date.now() - 200_000);
    await db
      .update(schema.workspaceRuntimeNodes)
      .set({ lastHeartbeatAt: staleHeartbeat })
      .where(eq(schema.workspaceRuntimeNodes.nodeId, BigInt(node.nodeId)));

    const ctx = await getWorkspaceSessionContext({
      workspaceId,
      authorization: `Bearer ${founderToken}`,
    });

    expect(ctx.presenceStatus).toBe("OFFLINE");
    expect(ctx.runtimeMode).toBe("REMOTE_ACCESS");
    expect(ctx.runtimeMode).not.toBe("CLOUD_CONTINUITY");
    expect(ctx.lastHeartbeatAt).toBe(staleHeartbeat.toISOString());
  });
});
