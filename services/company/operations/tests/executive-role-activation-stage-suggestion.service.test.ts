import { describe, it, expect, beforeEach } from "vitest";
import { createTestWorkspaceWithMember, makeTestTenantContext } from "./_helpers";
import { TenantContext } from "../../shared/types/tenant_context";
import { createProjectService } from "../services/project.service";
import { transitionProjectLifecycle } from "../services/project-lifecycle.service";
import { getStageSuggestion } from "../services/executive-role-activation.service";
import { activateWorkspaceExecutiveRole } from "../services/workspace-executive-role-activation.service";
import { activateProjectStartupTeamMember } from "../services/project-startup-team.service";

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

  async function enableProfiles(projectId: string, profileKeys: string[]): Promise<void> {
    for (const profileKey of profileKeys) {
      await activateProjectStartupTeamMember(founderCtx, projectId, profileKey, {
        expectedVersion: 1,
      });
    }
  }

  it("suggests the P0 roles for a new project (defaults to P0_DISCOVERY)", async () => {
    // chief_of_staff→operations, cfo→finance, cmo→marketing, cpo→product
    await enableProfiles(defaultProjectId, ["operations", "finance", "marketing", "product"]);
    const project = await createProjectService(founderCtx, { title: "Stage Suggestion Test" });

    const suggestion = await getStageSuggestion(founderCtx, project.id);
    expect(suggestion.stage).toBe("P0_DISCOVERY");
    expect([...suggestion.toActivate].sort()).toEqual(["cfo", "chief_of_staff", "cmo", "cpo"]);
    expect(suggestion.toSuggestDeactivate).toEqual([]);
  });

  it("never suggests a role whose underlying agent is unavailable workspace-wide", async () => {
    // Không bật profile nào → mọi role UNAVAILABLE → không gợi ý bật gì cả.
    const project = await createProjectService(founderCtx, { title: "No Agents Project" });

    const suggestion = await getStageSuggestion(founderCtx, project.id);
    expect(suggestion.stage).toBe("P0_DISCOVERY");
    expect(suggestion.toActivate).toEqual([]);
  });

  it("does not suggest deactivating a persistent role after moving to P2, and reflects the workspace-shared activation set for a second project", async () => {
    await enableProfiles(defaultProjectId, [
      "operations",
      "marketing",
      "coding",
      "security",
      "legal",
      "data",
      "ai_governance",
    ]);

    const projectA = await createProjectService(founderCtx, { title: "Stage P2 Test A" });
    const projectB = await createProjectService(founderCtx, { title: "Stage P2 Test B" });

    await activateWorkspaceExecutiveRole(founderCtx, "cmo", {});
    await activateWorkspaceExecutiveRole(founderCtx, "coo", {});

    await transitionProjectLifecycle(founderCtx, projectA.id, {
      toStage: "P1_PROBLEM_VALIDATION",
      expectedStageVersion: 0,
    });
    await transitionProjectLifecycle(founderCtx, projectA.id, {
      toStage: "P2_SOLUTION_VALIDATION",
      expectedStageVersion: 1,
    });

    const suggestionA = await getStageSuggestion(founderCtx, projectA.id);
    expect(suggestionA.stage).toBe("P2_SOLUTION_VALIDATION");
    // cmo là persistent, coo đã nằm trong preset P2 — cả 2 không bị gợi ý tắt.
    expect(suggestionA.toSuggestDeactivate).toEqual([]);
    expect(suggestionA.toActivate).toEqual(
      expect.arrayContaining(["vpe", "ciso", "gc", "cdo", "caio"])
    );
    // coo đã ACTIVE rồi nên không nằm trong danh sách cần bật.
    expect(suggestionA.toActivate).not.toContain("coo");

    // Project B vẫn ở P0 nhưng "thấy" coo đã ACTIVE (workspace-shared).
    const suggestionB = await getStageSuggestion(founderCtx, projectB.id);
    expect(suggestionB.stage).toBe("P0_DISCOVERY");
    expect(suggestionB.toActivate).not.toContain("cmo"); // đã ACTIVE workspace-wide
    // coo nằm ngoài preset P0 của Project B, NHƯNG Project A đang ở P2 vẫn cần
    // coo. Vì activation dùng chung cả Workspace, gợi ý tắt coo ở đây sẽ rút
    // mất role của Project A → không được gợi ý.
    expect(suggestionB.toSuggestDeactivate).toEqual([]);
  });

  it("suggests deactivating a non-persistent role that is active but outside the current stage preset", async () => {
    await enableProfiles(defaultProjectId, ["customer_support", "operations", "people"]);
    const project = await createProjectService(founderCtx, { title: "Deactivate Suggestion" });

    // cco (customer_support) ACTIVE, không persistent.
    await activateWorkspaceExecutiveRole(founderCtx, "cco", {});

    // P5_OPERATE_GROWTH preset = [chro] → cco nằm ngoài preset.
    for (const [toStage, expectedStageVersion] of [
      ["P1_PROBLEM_VALIDATION", 0],
      ["P2_SOLUTION_VALIDATION", 1],
      ["P3_BUILD_VALIDATE", 2],
      ["P4_GO_TO_MARKET", 3],
      ["P5_OPERATE_GROWTH", 4],
    ] as [string, number][]) {
      await transitionProjectLifecycle(founderCtx, project.id, {
        toStage,
        expectedStageVersion,
      });
    }

    const suggestion = await getStageSuggestion(founderCtx, project.id);
    expect(suggestion.stage).toBe("P5_OPERATE_GROWTH");
    expect(suggestion.toSuggestDeactivate).toContain("cco");
    expect(suggestion.toActivate).toContain("chro");
  });

  it("rejects a project from another workspace with not found", async () => {
    const otherWs = await createTestWorkspaceWithMember({ role: "founder" });
    await expect(getStageSuggestion(founderCtx, otherWs.projectId)).rejects.toThrow(/not found/i);
  });
});
