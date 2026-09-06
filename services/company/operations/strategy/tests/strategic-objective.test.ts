import { describe, expect, it } from "vitest";
import { APIError } from "encore.dev/api";
import { createTestWorkspaceWithMember } from "../../tests/_helpers";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import type { TenantContext } from "../../../shared/types/tenant_context";
import {
  createStrategicObjective,
  getStrategicObjective,
  listStrategicObjectives,
  updateStrategicObjective,
  saveBscFocusScopes,
} from "../services/strategic-objective.service";
import { updateWorkspaceStrategySettings } from "../services/workspace-strategy-settings.service";
import { db } from "../../models/db";
import { projects } from "../../../shared/db/schema/operations";

function createMockTenantContext(
  overrides: Partial<TenantContext> & {
    workspaceId: string;
    userId: string;
    membershipRole: string;
  }
): TenantContext {
  return {
    permissions: [],
    correlationId: "test-corr-id",
    ...overrides,
  };
}

describe("strategic-objective service", () => {
  it("rejects activating an objective with title alone (missing success definition)", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const ctx = createMockTenantContext({
      workspaceId: ws.workspaceId,
      userId: ws.userId,
      membershipRole: "founder",
      permissions: ["*"],
    });

    // Create DRAFT without success definition
    const obj = await createStrategicObjective(ctx, {
      workspaceId: ws.workspaceId,
      title: "Trở thành số 1 thị trường SaaS",
    });
    expect(obj.status).toBe("DRAFT");

    // Attempt to activate without success definition
    await expect(
      updateStrategicObjective(ctx, {
        workspaceId: ws.workspaceId,
        id: obj.id,
        status: "ACTIVE",
      })
    ).rejects.toThrow("success definition");

    // Direct create as ACTIVE without success definition
    await expect(
      createStrategicObjective(ctx, {
        workspaceId: ws.workspaceId,
        title: "Trở thành số 1 thị trường SaaS",
        status: "ACTIVE",
      })
    ).rejects.toThrow("success definition");
  });

  it("activates an objective without BSC scope when bscMode is OFF", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const ctx = createMockTenantContext({
      workspaceId: ws.workspaceId,
      userId: ws.userId,
      membershipRole: "founder",
      permissions: ["*"],
    });

    // Default settings: bscMode is OFF
    const obj = await createStrategicObjective(ctx, {
      workspaceId: ws.workspaceId,
      title: "Tăng trưởng ARR lên 1 triệu USD",
      successDefinition: "Đạt 1,000,000 USD ARR tính đến Q4/2026 với 100 khách hàng B2B",
      status: "ACTIVE",
    });

    expect(obj.status).toBe("ACTIVE");
    expect(obj.settingsRevision).toBe(1);
  });

  it("rejects activation without active BSC focus scope when bscMode is REQUIRED", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const ctx = createMockTenantContext({
      workspaceId: ws.workspaceId,
      userId: ws.userId,
      membershipRole: "founder",
      permissions: ["*"],
    });

    // Configure workspace with bscMode = REQUIRED
    await updateWorkspaceStrategySettings(ctx, {
      workspaceId: ws.workspaceId,
      strategyMethod: "BSC_FILTER",
      bscMode: "REQUIRED",
      enabledBscPerspectives: ["FINANCIAL", "CUSTOMER"],
    });

    // Create DRAFT
    const obj = await createStrategicObjective(ctx, {
      workspaceId: ws.workspaceId,
      title: "Mở rộng phân khúc Enterprise",
      successDefinition: "Ký 20 hợp đồng Enterprise với ACV > 50,000 USD",
    });

    // Attempt to activate without adding BSC scopes
    await expect(
      updateStrategicObjective(ctx, {
        workspaceId: ws.workspaceId,
        id: obj.id,
        status: "ACTIVE",
      })
    ).rejects.toThrow("at least one active BSC focus scope");

    // Add BSC scope
    await saveBscFocusScopes(ctx, {
      workspaceId: ws.workspaceId,
      strategicObjectiveId: obj.id,
      scopes: [
        {
          perspective: "FINANCIAL",
          focusStatement: "Đạt dòng tiền tự do dương từ hợp đồng Enterprise",
        },
      ],
    });

    // Now activation succeeds
    const activated = await updateStrategicObjective(ctx, {
      workspaceId: ws.workspaceId,
      id: obj.id,
      status: "ACTIVE",
    });
    expect(activated.status).toBe("ACTIVE");
    expect(activated.bscFocusScopes?.length).toBe(1);
    expect(activated.bscFocusScopes?.[0].perspective).toBe("FINANCIAL");
  });

  it("rejects BSC scope with disabled perspective", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const ctx = createMockTenantContext({
      workspaceId: ws.workspaceId,
      userId: ws.userId,
      membershipRole: "founder",
      permissions: ["*"],
    });

    // Configure workspace with only FINANCIAL and CUSTOMER enabled
    await updateWorkspaceStrategySettings(ctx, {
      workspaceId: ws.workspaceId,
      strategyMethod: "BSC_FILTER",
      bscMode: "OPTIONAL",
      enabledBscPerspectives: ["FINANCIAL", "CUSTOMER"],
    });

    const obj = await createStrategicObjective(ctx, {
      workspaceId: ws.workspaceId,
      title: "Nâng cao chất lượng đội ngũ",
    });

    // Attempt to save scope with LEARNING_AND_GROWTH which is not enabled
    await expect(
      saveBscFocusScopes(ctx, {
        workspaceId: ws.workspaceId,
        strategicObjectiveId: obj.id,
        scopes: [
          {
            perspective: "LEARNING_AND_GROWTH",
            focusStatement: "Đào tạo 100% kỹ sư về AI Agent",
          },
        ],
      })
    ).rejects.toThrow("not enabled in workspace settings");
  });

  it("handles duplicate-perspective upsert behaviour cleanly", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const ctx = createMockTenantContext({
      workspaceId: ws.workspaceId,
      userId: ws.userId,
      membershipRole: "founder",
      permissions: ["*"],
    });

    await updateWorkspaceStrategySettings(ctx, {
      workspaceId: ws.workspaceId,
      strategyMethod: "BSC_FILTER",
      bscMode: "OPTIONAL",
      enabledBscPerspectives: ["FINANCIAL", "CUSTOMER"],
    });

    const obj = await createStrategicObjective(ctx, {
      workspaceId: ws.workspaceId,
      title: "Tăng trưởng doanh thu",
    });

    // Add initial FINANCIAL scope
    const [scope1] = await saveBscFocusScopes(ctx, {
      workspaceId: ws.workspaceId,
      strategicObjectiveId: obj.id,
      scopes: [
        {
          perspective: "FINANCIAL",
          focusStatement: "Tối ưu chi phí hạ tầng cloud",
        },
      ],
    });
    expect(scope1.focusStatement).toBe("Tối ưu chi phí hạ tầng cloud");
    expect(scope1.status).toBe("ACTIVE");

    // Upsert a new FINANCIAL scope for same objective -> updates/replaces active scope
    const [scope2] = await saveBscFocusScopes(ctx, {
      workspaceId: ws.workspaceId,
      strategicObjectiveId: obj.id,
      scopes: [
        {
          perspective: "FINANCIAL",
          focusStatement: "Cắt giảm 30% chi phí SaaS dư thừa",
        },
      ],
    });

    expect(scope2.id).toBe(scope1.id);
    expect(scope2.focusStatement).toBe("Cắt giảm 30% chi phí SaaS dư thừa");

    // Verify fetching objective shows exactly one active scope
    const reloaded = await getStrategicObjective(ws.workspaceId, obj.id);
    expect(reloaded.bscFocusScopes?.length).toBe(1);
    expect(reloaded.bscFocusScopes?.[0].focusStatement).toBe("Cắt giảm 30% chi phí SaaS dư thừa");
  });

  it("rejects linking a project from another workspace", async () => {
    const wsA = await createTestWorkspaceWithMember({ role: "founder" });
    const wsB = await createTestWorkspaceWithMember({ role: "founder" });

    const ctxA = createMockTenantContext({
      workspaceId: wsA.workspaceId,
      userId: wsA.userId,
      membershipRole: "founder",
      permissions: ["*"],
    });

    // Create project in Workspace B
    const projectBId = generateSnowflake();
    await db.insert(projects).values({
      id: projectBId,
      workspaceId: BigInt(wsB.workspaceId),
      title: "Dự án Workspace B",
      status: "ACTIVE",
    });

    // Workspace A attempts to link project from Workspace B
    await expect(
      createStrategicObjective(ctxA, {
        workspaceId: wsA.workspaceId,
        projectId: projectBId.toString(),
        title: "Mục tiêu chéo workspace",
      })
    ).rejects.toThrow("does not exist in workspace");
  });

  it("rejects updating or adding scope to an archived objective", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const ctx = createMockTenantContext({
      workspaceId: ws.workspaceId,
      userId: ws.userId,
      membershipRole: "founder",
      permissions: ["*"],
    });

    const obj = await createStrategicObjective(ctx, {
      workspaceId: ws.workspaceId,
      title: "Mục tiêu tạm thời",
    });

    // Archive it
    const archived = await updateStrategicObjective(ctx, {
      workspaceId: ws.workspaceId,
      id: obj.id,
      status: "ARCHIVED",
    });
    expect(archived.status).toBe("ARCHIVED");

    // Attempt to update title
    await expect(
      updateStrategicObjective(ctx, {
        workspaceId: ws.workspaceId,
        id: obj.id,
        title: "Đổi tên mục tiêu đã lưu trữ",
      })
    ).rejects.toThrow("Cannot update an archived strategic objective");

    // Attempt to add scope
    await expect(
      saveBscFocusScopes(ctx, {
        workspaceId: ws.workspaceId,
        strategicObjectiveId: obj.id,
        scopes: [
          {
            perspective: "FINANCIAL",
            focusStatement: "Không thể thêm vào mục tiêu archived",
          },
        ],
      })
    ).rejects.toThrow("Cannot add or update BSC focus scopes on an archived objective");
  });
});
