import { beforeAll, describe, expect, it } from "vitest";
import { registerPlatformUser } from "../services/auth.service";
import { signPlatformToken } from "../services/token.service";
import { db, schema } from "../models/db";
import {
  getWorkspaceCapabilityManifest,
  setWorkspaceSurfaceOverride,
  setWorkspaceModuleEnabled,
} from "../handlers/workspace-settings.handler";
import { installWorkspaceConnector } from "../handlers/workspace-settings.handler";

describe("Workspace Capability Manifest", () => {
  let wsId: string;
  let operatorToken: string;
  let outsiderToken: string;

  beforeAll(async () => {
    const op = await registerPlatformUser({
      email: `cap-op-${Date.now()}@test.io`,
      password: "SecurePassword123",
      workspace_name: "Capability Manifest Workspace",
    });
    wsId = op.platform_workspace_id!;
    operatorToken = op.access_token;

    const outsider = await registerPlatformUser({
      email: `cap-out-${Date.now()}@test.io`,
      password: "SecurePassword123",
      workspace_name: "Outsider Workspace",
    });
    outsiderToken = outsider.access_token;
  });

  it("returns the spec §7.1 shape with a version and typed surfaces", async () => {
    const res = await getWorkspaceCapabilityManifest({
      workspaceId: wsId,
      authorization: `Bearer ${operatorToken}`,
    });
    expect(res.data.version).toBeTruthy();
    expect(res.data.workspaceId).toBe(wsId);
    const board = res.data.surfaces.find((s) => s.surfaceKey === "founder_trial.board");
    expect(board).toBeDefined();
    expect(board!.surfaceStatus).toBe("AVAILABLE");
    expect(board!.contractEndpoint).toBe("strategy.founder_trial.board.read");
    expect(board!).toHaveProperty("moduleKey");
    expect(board!).toHaveProperty("featureKey");
    expect(board!).toHaveProperty("entitled");
    expect(Array.isArray(board!.reasons)).toBe(true);
  });

  it("planned surfaces are PLANNED with a null contract endpoint", async () => {
    const res = await getWorkspaceCapabilityManifest({
      workspaceId: wsId,
      authorization: `Bearer ${operatorToken}`,
    });
    const pestel = res.data.surfaces.find((s) => s.surfaceKey === "strategy.pestel");
    expect(pestel!.surfaceStatus).toBe("PLANNED");
    expect(pestel!.contractEndpoint).toBeNull();
  });

  it("finance cash liquidity is CONFIGURATION_REQUIRED until CAS connector enabled", async () => {
    const before = await getWorkspaceCapabilityManifest({
      workspaceId: wsId,
      authorization: `Bearer ${operatorToken}`,
    });
    const cashBefore = before.data.surfaces.find((s) => s.surfaceKey === "finance.cash_liquidity");
    expect(cashBefore!.surfaceStatus).toBe("CONFIGURATION_REQUIRED");
    expect(cashBefore!.reasons).toContain("connector_missing:cas");

    await installWorkspaceConnector({
      workspaceId: wsId,
      connectorKey: "cas",
      authorization: `Bearer ${operatorToken}`,
    } as any);

    const after = await getWorkspaceCapabilityManifest({
      workspaceId: wsId,
      authorization: `Bearer ${operatorToken}`,
    });
    const cashAfter = after.data.surfaces.find((s) => s.surfaceKey === "finance.cash_liquidity");
    expect(cashAfter!.surfaceStatus).toBe("AVAILABLE");
  });

  it("disabling the finance module makes finance surfaces UNAVAILABLE and unentitled", async () => {
    await setWorkspaceModuleEnabled({
      workspaceId: wsId,
      moduleKey: "finance",
      enabled: false,
      authorization: `Bearer ${operatorToken}`,
    });
    const res = await getWorkspaceCapabilityManifest({
      workspaceId: wsId,
      authorization: `Bearer ${operatorToken}`,
    });
    const budget = res.data.surfaces.find((s) => s.surfaceKey === "finance.project_budget");
    expect(budget!.entitled).toBe(false);
    expect(budget!.surfaceStatus).toBe("UNAVAILABLE");
    expect(budget!.reasons).toContain("module_disabled:finance");

    await setWorkspaceModuleEnabled({
      workspaceId: wsId,
      moduleKey: "finance",
      enabled: true,
      authorization: `Bearer ${operatorToken}`,
    });
  });

  it("operator override can downgrade but never force AVAILABLE", async () => {
    await setWorkspaceSurfaceOverride({
      workspaceId: wsId,
      surfaceKey: "founder_trial.board",
      statusOverride: "PILOT",
      reason: "trial cohort",
      authorization: `Bearer ${operatorToken}`,
    });
    const res = await getWorkspaceCapabilityManifest({
      workspaceId: wsId,
      authorization: `Bearer ${operatorToken}`,
    });
    const board = res.data.surfaces.find((s) => s.surfaceKey === "founder_trial.board");
    expect(board!.surfaceStatus).toBe("PILOT");
    expect(board!.reasons.some((r) => r.startsWith("operator_override"))).toBe(true);

    await expect(
      setWorkspaceSurfaceOverride({
        workspaceId: wsId,
        surfaceKey: "strategy.pestel",
        statusOverride: "AVAILABLE",
        authorization: `Bearer ${operatorToken}`,
      })
    ).rejects.toThrow();
  });

  it("rejects a caller who is not a workspace member", async () => {
    await expect(
      getWorkspaceCapabilityManifest({
        workspaceId: wsId,
        authorization: `Bearer ${outsiderToken}`,
      })
    ).rejects.toThrow();
  });

  it("rejects surface override from a non-operator member", async () => {
    const member = await registerPlatformUser({
      email: `cap-mem-${Date.now()}@test.io`,
      password: "SecurePassword123",
      workspace_name: "Member Home",
    });
    await db.insert(schema.workspaceMemberships).values({
      id: BigInt(Date.now()) * 1000n + BigInt(Math.floor(Math.random() * 1000)),
      workspaceId: BigInt(wsId),
      userId: BigInt(member.user!.id),
      roleId: "member",
    });
    const memberToken = signPlatformToken(member.user!.id);
    await expect(
      setWorkspaceSurfaceOverride({
        workspaceId: wsId,
        surfaceKey: "founder_trial.board",
        statusOverride: "UNAVAILABLE",
        authorization: `Bearer ${memberToken}`,
      })
    ).rejects.toThrow();
  });
});
