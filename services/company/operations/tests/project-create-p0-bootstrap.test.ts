import { describe, it, expect, beforeEach, vi } from "vitest";
import { APIError } from "encore.dev/api";
import { createTestWorkspaceWithMember, makeTestTenantContext } from "./_helpers";
import { TenantContext } from "../../shared/types/tenant_context";
import { createProjectService, getProjectService } from "../services/project.service";
import { bootstrapP0CoreForProject } from "../services/p0-core-bootstrap.service";

vi.mock("../services/p0-core-bootstrap.service", () => ({
  bootstrapP0CoreForProject: vi.fn(),
}));

/**
 * Bootstrap P0 Core chạy sau khi Project đã commit. Lỗi bootstrap không được làm
 * request tạo Project fail (client sẽ retry và tạo Project trùng).
 */
describe("createProjectService P0 Core bootstrap outcome", () => {
  let founderCtx: TenantContext;

  beforeEach(async () => {
    vi.mocked(bootstrapP0CoreForProject).mockReset();
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    founderCtx = makeTestTenantContext({
      workspaceId: ws.workspaceId,
      userId: ws.userId,
      workforceMemberId: ws.userId,
      membershipRole: "founder",
      isAiAgent: false,
    });
  });

  it("returns the created Project with INCOMPLETE status when bootstrap fails", async () => {
    vi.mocked(bootstrapP0CoreForProject).mockRejectedValue(
      APIError.failedPrecondition("P0_CORE_PROFILE_UNAVAILABLE: finance")
    );

    const project = await createProjectService(founderCtx, { title: "Greenfield", creationMode: "NEW" });

    expect(project.p0CoreBootstrap).toEqual({
      status: "INCOMPLETE",
      errorCode: "failed_precondition",
    });
    const stored = await getProjectService(founderCtx, project.id);
    expect(stored.title).toBe("Greenfield");
  });

  it("reports COMPLETE when bootstrap succeeds", async () => {
    vi.mocked(bootstrapP0CoreForProject).mockResolvedValue({
      projectId: "x",
      roleKeys: ["chief_of_staff", "cfo", "cmo", "cpo"],
    });

    const project = await createProjectService(founderCtx, { title: "Greenfield OK", creationMode: "NEW" });

    expect(project.p0CoreBootstrap).toEqual({ status: "COMPLETE" });
  });

  it("omits the status when no bootstrap is attempted (non-founder)", async () => {
    const adminCtx = { ...founderCtx, membershipRole: "admin" };

    const project = await createProjectService(adminCtx, { title: "Admin project", creationMode: "NEW" });

    expect(project.p0CoreBootstrap).toBeUndefined();
    expect(bootstrapP0CoreForProject).not.toHaveBeenCalled();
  });
});
