import { describe, it, expect, beforeEach } from "vitest";
import {
  createTestWorkspaceWithMember,
  makeTestTenantContext,
  deployWorkspaceAgentForProfile,
} from "./_helpers";
import { TenantContext } from "../../shared/types/tenant_context";
import { createProjectService } from "../services/project.service";
import { transitionProjectLifecycle } from "../services/project-lifecycle.service";
import { getStageSuggestion } from "../services/executive-role-activation.service";
import { activateWorkspaceExecutiveRole } from "../services/workspace-executive-role-activation.service";

describe("getStageSuggestion", () => {
  let founderCtx: TenantContext;
  let defaultProjectId: string;

  beforeEach(async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    defaultProjectId = ws.projectId;
    founderCtx = makeTestTenantContext({
      workspaceId: ws.workspaceId,
      userId: ws.userId,
      workforceMemberId: ws.userId,
      membershipRole: "founder",
      isAiAgent: false,
    });
  });

  it("suggests Workspace office enablement for the P0 roles of a new project", async () => {
    // chief_of_staff→operations, cfo→finance, cmo→marketing, cpo→product.
    await deployWorkspaceAgentForProfile(founderCtx, defaultProjectId, "operations");
    await deployWorkspaceAgentForProfile(founderCtx, defaultProjectId, "finance");
    await deployWorkspaceAgentForProfile(founderCtx, defaultProjectId, "marketing");
    await deployWorkspaceAgentForProfile(founderCtx, defaultProjectId, "product");

    const project = await createProjectService(founderCtx, { title: "Stage Suggestion Test" });

    const suggestion = await getStageSuggestion(founderCtx, project.id);
    expect(suggestion.stage).toBe("P0_DISCOVERY");
    // Office chưa bật ở Workspace → gợi ý hành động Workspace (không deploy).
    expect([...suggestion.workspaceOfficeToEnable].sort()).toEqual([
      "cfo",
      "chief_of_staff",
      "cmo",
      "cpo",
    ]);
    expect(suggestion.projectAgentsToDeploy).toEqual([]);
    expect(suggestion.stageEligibleRoles).toEqual([
      "chief_of_staff",
      "cfo",
      "cmo",
      "cpo",
    ]);
  });

  it("never suggests enabling an office whose underlying agent is unavailable workspace-wide", async () => {
    // Không deploy agent nào → mọi role UNAVAILABLE → không gợi ý bật office.
    const project = await createProjectService(founderCtx, { title: "No Agents Project" });

    const suggestion = await getStageSuggestion(founderCtx, project.id);
    expect(suggestion.stage).toBe("P0_DISCOVERY");
    expect(suggestion.workspaceOfficeToEnable).toEqual([]);
    // stageEligibleRoles chỉ mô tả preset stage, không phụ thuộc availability.
    expect(suggestion.stageEligibleRoles).toEqual([
      "chief_of_staff",
      "cfo",
      "cmo",
      "cpo",
    ]);
  });

  it("suggests Project Agent deployment for an ACTIVE office role that is not yet deployed to the Project", async () => {
    // Agent finance + office cfo ACTIVE ở Workspace, nhưng Project mới chưa có deployment.
    await deployWorkspaceAgentForProfile(founderCtx, defaultProjectId, "finance");
    await activateWorkspaceExecutiveRole(founderCtx, "cfo", {});

    const project = await createProjectService(founderCtx, { title: "Deploy Suggestion" });

    const suggestion = await getStageSuggestion(founderCtx, project.id);
    expect(suggestion.stage).toBe("P0_DISCOVERY");
    // Office đã ACTIVE nên không gợi ý bật lại — chỉ thiếu deployment Project.
    expect(suggestion.workspaceOfficeToEnable).not.toContain("cfo");
    expect(suggestion.projectAgentsToDeploy).toContain("cfo");
  });

  it("reflects the stage preset after a lifecycle transition without auto-activating anything", async () => {
    // Đủ agent nền cho preset P2 (operations, coding, security, legal, data, ai_governance).
    for (const profileKey of ["operations", "coding", "security", "legal", "data", "ai_governance"]) {
      await deployWorkspaceAgentForProfile(founderCtx, defaultProjectId, profileKey);
    }

    const project = await createProjectService(founderCtx, { title: "Stage P2 Test" });
    await transitionProjectLifecycle(founderCtx, project.id, {
      toStage: "P1_PROBLEM_VALIDATION",
      expectedStageVersion: 0,
    });
    await transitionProjectLifecycle(founderCtx, project.id, {
      toStage: "P2_SOLUTION_VALIDATION",
      expectedStageVersion: 1,
    });

    const suggestion = await getStageSuggestion(founderCtx, project.id);
    expect(suggestion.stage).toBe("P2_SOLUTION_VALIDATION");
    // P2 preset = coo, vpe, ciso, gc, cdo, caio — gợi ý bật office (chưa bật).
    expect(suggestion.stageEligibleRoles).toEqual(["coo", "vpe", "ciso", "gc", "cdo", "caio"]);
    expect([...suggestion.workspaceOfficeToEnable].sort()).toEqual([
      "caio",
      "cdo",
      "ciso",
      "coo",
      "gc",
      "vpe",
    ]);
    // Không có office nào ACTIVE nên không gợi ý deploy.
    expect(suggestion.projectAgentsToDeploy).toEqual([]);
  });

  it("rejects a project from another workspace with not found", async () => {
    const otherWs = await createTestWorkspaceWithMember({ role: "founder" });
    await expect(getStageSuggestion(founderCtx, otherWs.projectId)).rejects.toThrow(/not found/i);
  });
});
