// Plan hub vận hành đợt 2 B5 (Task 6b) — đường assert connector theo
// `executionId` (schedule execution) thay cho `conversationId`: lịch nền
// không có conversation grant (mỗi execution tạo conversation mới), phải
// kiểm theo `connectorGrantIdsSnapshot` đã chốt lúc founder duyệt (Task 6).
import { describe, it, expect, beforeEach } from "vitest";
import { db, schema } from "../models/db";
import * as connectorSvc from "../services/workspace-connector.service";
import { assertConnectorEndpoint } from "../handlers/workspace-connector.handler";
import { createWorkspaceSchedule, runScheduleNow } from "../services/workspace-schedule.service";
import { signWorkerServiceToken } from "../services/token.service";

const { workspaceScheduleExecutions, connectorAuthorizations, workspaceConnectorInstallations } =
  schema;

function uniqueOrg(label: string): string {
  return `ws_${label}_${Date.now()}_${Math.random().toString(36).slice(2)}`;
}

async function seedInstallationAndAuthorization(input: {
  organizationId: string;
  principalId: string;
  connectorKey?: string;
  expiresAt?: Date;
  state?: "active" | "expired" | "revoked";
  installStatus?: "enabled" | "disabled";
  grantedScopes?: string[];
}) {
  const connectorKey = input.connectorKey || "email-read";
  const inst = await connectorSvc.installWorkspaceConnector({
    organizationId: input.organizationId,
    connectorKey,
    installedBy: input.principalId,
  });
  const secretRef = "secret://cosa-connectors/test/email-read";
  const auth = await connectorSvc.registerConnectorAuthorization({
    installationId: inst.id,
    organizationId: input.organizationId,
    principalId: input.principalId,
    secretRef,
    grantedScopes: input.grantedScopes || ["mail:read"],
    expiresAt: input.expiresAt || new Date(Date.now() + 3600_000),
  });
  if (input.state && input.state !== "active") {
    await db
      .update(connectorAuthorizations)
      .set({ state: input.state })
      .where(eq(connectorAuthorizations.id, auth.id));
  }
  // Disable installation SAU KHI đã đăng ký authorization (registerConnectorAuthorization
  // tự từ chối installation không "enabled").
  if (input.installStatus === "disabled") {
    await db
      .update(workspaceConnectorInstallations)
      .set({ status: "disabled" })
      .where(eq(workspaceConnectorInstallations.id, inst.id));
  }
  return { inst, auth: { ...auth, secretRef }, connectorKey };
}

async function seedExecutionWithSnapshot(input: {
  organizationId: string;
  connectorGrantIdsSnapshot: string[];
}): Promise<string> {
  const def = await createWorkspaceSchedule({
    organizationId: input.organizationId,
    createdBy: "user_1",
    scheduleKind: "daily",
    hour: 8,
    promptTemplate: "digest",
    projectId: "proj_1",
  });
  const execution = await runScheduleNow({
    scheduleId: def.id,
    organizationId: input.organizationId,
    principalId: "user_1",
  });
  await db
    .update(workspaceScheduleExecutions)
    .set({ connectorGrantIdsSnapshot: input.connectorGrantIdsSnapshot })
    .where(eq(workspaceScheduleExecutions.id, execution.id));
  return execution.id;
}

import { eq } from "drizzle-orm";

describe("assertConnectorInvocationForExecution (B5 Task 6b)", () => {
  beforeEach(() => {
    process.env.COSA_CONNECTOR_ALLOWED_KEYS = "sandbox-read,email-read";
  });

  it("ok:true khi authorization id nằm trong snapshot, còn active", async () => {
    const organizationId = uniqueOrg("ok");
    const { auth, connectorKey } = await seedInstallationAndAuthorization({
      organizationId,
      principalId: "founder_1",
    });
    const executionId = await seedExecutionWithSnapshot({
      organizationId,
      connectorGrantIdsSnapshot: [auth.id],
    });

    const res = await connectorSvc.assertConnectorInvocationForExecution({
      organizationId,
      executionId,
      connectorKey,
      action: "email.digest.read",
      requiredScope: "mail:read",
    });

    expect(res.ok).toBe(true);
    expect(res.secretRef).toBe(auth.secretRef);
  });

  it("connector_reauth_required khi snapshot rỗng", async () => {
    const organizationId = uniqueOrg("empty");
    const executionId = await seedExecutionWithSnapshot({
      organizationId,
      connectorGrantIdsSnapshot: [],
    });

    const res = await connectorSvc.assertConnectorInvocationForExecution({
      organizationId,
      executionId,
      connectorKey: "sandbox-read",
    });

    expect(res.ok).toBe(false);
    expect(res.error).toBe("connector_reauth_required");
  });

  it("connector_reauth_required khi authorization trong snapshot đã hết hạn", async () => {
    const organizationId = uniqueOrg("expired");
    const { auth, connectorKey } = await seedInstallationAndAuthorization({
      organizationId,
      principalId: "founder_1",
      expiresAt: new Date(Date.now() - 1000),
    });
    const executionId = await seedExecutionWithSnapshot({
      organizationId,
      connectorGrantIdsSnapshot: [auth.id],
    });

    const res = await connectorSvc.assertConnectorInvocationForExecution({
      organizationId,
      executionId,
      connectorKey,
    });

    expect(res.ok).toBe(false);
    expect(res.error).toBe("connector_reauth_required");
  });

  it("connector_reauth_required khi authorization trong snapshot đã bị revoke", async () => {
    const organizationId = uniqueOrg("revoked");
    const { auth, connectorKey } = await seedInstallationAndAuthorization({
      organizationId,
      principalId: "founder_1",
      state: "revoked",
    });
    const executionId = await seedExecutionWithSnapshot({
      organizationId,
      connectorGrantIdsSnapshot: [auth.id],
    });

    const res = await connectorSvc.assertConnectorInvocationForExecution({
      organizationId,
      executionId,
      connectorKey,
    });

    expect(res.ok).toBe(false);
    expect(res.error).toBe("connector_reauth_required");
  });

  it("connector_installation_disabled khi installation đã bị disable", async () => {
    const organizationId = uniqueOrg("disabled");
    const { auth, connectorKey } = await seedInstallationAndAuthorization({
      organizationId,
      principalId: "founder_1",
      installStatus: "disabled",
    });
    const executionId = await seedExecutionWithSnapshot({
      organizationId,
      connectorGrantIdsSnapshot: [auth.id],
    });

    const res = await connectorSvc.assertConnectorInvocationForExecution({
      organizationId,
      executionId,
      connectorKey,
    });

    expect(res.ok).toBe(false);
    expect(res.error).toBe("connector_installation_disabled");
  });

  it("connector_scope_missing khi requiredScope không nằm trong grantedScopes", async () => {
    const organizationId = uniqueOrg("scope");
    const { auth, connectorKey } = await seedInstallationAndAuthorization({
      organizationId,
      principalId: "founder_1",
      grantedScopes: ["metadata"],
    });
    const executionId = await seedExecutionWithSnapshot({
      organizationId,
      connectorGrantIdsSnapshot: [auth.id],
    });

    const res = await connectorSvc.assertConnectorInvocationForExecution({
      organizationId,
      executionId,
      connectorKey,
      requiredScope: "mail:read",
    });

    expect(res.ok).toBe(false);
    expect(res.error).toBe("connector_scope_missing");
  });

  it("connector_reauth_required khi executionId thuộc organization khác (không cross-tenant)", async () => {
    const organizationId = uniqueOrg("tenant-a");
    const otherOrg = uniqueOrg("tenant-b");
    const { auth, connectorKey } = await seedInstallationAndAuthorization({
      organizationId: otherOrg,
      principalId: "founder_1",
    });
    const executionId = await seedExecutionWithSnapshot({
      organizationId: otherOrg,
      connectorGrantIdsSnapshot: [auth.id],
    });

    const res = await connectorSvc.assertConnectorInvocationForExecution({
      organizationId, // tenant khác với execution thật
      executionId,
      connectorKey,
    });

    expect(res.ok).toBe(false);
    expect(res.error).toBe("connector_reauth_required");
  });

  it("endpoint /cosa/connectors/assert dùng đường executionId khi có executionId, không cần conversationId", async () => {
    const organizationId = uniqueOrg("endpoint");
    const { auth, connectorKey } = await seedInstallationAndAuthorization({
      organizationId,
      principalId: "founder_1",
    });
    const executionId = await seedExecutionWithSnapshot({
      organizationId,
      connectorGrantIdsSnapshot: [auth.id],
    });

    const res = await assertConnectorEndpoint({
      authorization: `Bearer ${signWorkerServiceToken("worker-1")}`,
      organizationId,
      executionId,
      connectorKey,
    } as any);

    expect(res.ok).toBe(true);
    expect(res.secretRef).toBe(auth.secretRef);
  });
});
