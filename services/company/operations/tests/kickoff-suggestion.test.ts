import { describe, it, expect, afterEach } from "vitest";
import { createProject } from "../handlers/project.handler";
import { createTestWorkspaceWithMember } from "./_helpers";
import {
  getProjectOperatingSetupEndpoint,
  putProjectOperatingSetupEndpoint,
  requestKickoffSuggestionEndpoint,
  applyKickoffSuggestionResultEndpoint,
} from "../strategy/handlers/project-operating-setup.handler";
import {
  dispatchKickoffSuggestionRun,
  setCustomKickoffSuggestionRunner,
} from "../strategy/services/kickoff-suggestion-cosa-client";

describe("kickoff-suggestion-cosa-client", () => {
  afterEach(() => {
    setCustomKickoffSuggestionRunner(null);
  });

  it("gọi runner tuỳ chỉnh khi được set (test injection seam)", async () => {
    let received: any = null;
    setCustomKickoffSuggestionRunner(async (payload) => {
      received = payload;
    });

    await dispatchKickoffSuggestionRun({
      workspaceId: "ws1",
      projectId: "p1",
      runId: "run-abc",
      targetCustomer: "Founder B2B SaaS",
      problemStatement: "Không biết validate ý tưởng",
      evidenceLevel: "NONE",
      selectedStage: "P0_DISCOVERY",
      stageDurationWeeks: 2,
    });

    expect(received).toEqual({
      workspaceId: "ws1",
      projectId: "p1",
      runId: "run-abc",
      targetCustomer: "Founder B2B SaaS",
      problemStatement: "Không biết validate ý tưởng",
      evidenceLevel: "NONE",
      selectedStage: "P0_DISCOVERY",
      stageDurationWeeks: 2,
    });
  });

  it("throw khi runner tuỳ chỉnh throw (không nuốt lỗi)", async () => {
    setCustomKickoffSuggestionRunner(async () => {
      throw new Error("cosa unreachable");
    });

    await expect(
      dispatchKickoffSuggestionRun({
        workspaceId: "ws1",
        projectId: "p1",
        runId: "run-abc",
        targetCustomer: "x",
        problemStatement: "y",
        evidenceLevel: "NONE",
        selectedStage: "P0_DISCOVERY",
        stageDurationWeeks: 2,
      })
    ).rejects.toThrow("cosa unreachable");
  });
});

describe("requestKickoffSuggestionEndpoint", () => {
  afterEach(() => {
    setCustomKickoffSuggestionRunner(null);
  });

  it("throw khi Bước 1 chưa đủ (targetCustomer/problemStatement/evidenceLevel rỗng)", async () => {
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Discovery",
    });

    await expect(
      requestKickoffSuggestionEndpoint({
        authorization: ws.bearerToken,
        workspaceId: ws.workspaceId,
        id: project.id,
      })
    ).rejects.toThrow();
  });

  it("set aiSuggestionStatus=dispatched và gọi cosa client khi Bước 1 đủ", async () => {
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Discovery",
    });
    await putProjectOperatingSetupEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
      targetCustomer: "Founder B2B SaaS",
      problemStatement: "Không biết validate ý tưởng",
      evidenceLevel: "NONE",
    });

    let dispatchedPayload: any = null;
    setCustomKickoffSuggestionRunner(async (payload) => {
      dispatchedPayload = payload;
    });

    const result = await requestKickoffSuggestionEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
    });
    expect(result.status).toBe("dispatched");
    expect(dispatchedPayload.projectId).toBe(project.id);
    expect(dispatchedPayload.targetCustomer).toBe("Founder B2B SaaS");
    expect(dispatchedPayload.runId).toBe(result.runId);

    const view = await getProjectOperatingSetupEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
    });
    expect(view.aiSuggestionStatus).toBe("dispatched");
  });

  it("set aiSuggestionStatus=failed khi cosa client throw, không throw endpoint ra ngoài", async () => {
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Discovery",
    });
    await putProjectOperatingSetupEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
      targetCustomer: "x",
      problemStatement: "y",
      evidenceLevel: "NONE",
    });

    setCustomKickoffSuggestionRunner(async () => {
      throw new Error("cosa down");
    });

    const result = await requestKickoffSuggestionEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
    });
    expect(result.status).toBe("failed");

    const view = await getProjectOperatingSetupEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
    });
    expect(view.aiSuggestionStatus).toBe("failed");
  });
});

describe("applyKickoffSuggestionResultEndpoint", () => {
  afterEach(() => {
    setCustomKickoffSuggestionRunner(null);
  });

  async function dispatchedProject() {
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Discovery",
    });
    await putProjectOperatingSetupEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
      targetCustomer: "x",
      problemStatement: "y",
      evidenceLevel: "NONE",
    });
    setCustomKickoffSuggestionRunner(async () => {});
    const { runId } = await requestKickoffSuggestionEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
    });
    return { ws, project, runId };
  }

  it("cập nhật outcome/actions khi runId khớp và status=completed", async () => {
    const { ws, project, runId } = await dispatchedProject();

    const result = await applyKickoffSuggestionResultEndpoint({
      id: project.id,
      runId,
      status: "completed",
      outcome: "Hoàn thành 5 cuộc phỏng vấn khách hàng mục tiêu",
      actions: ["Phỏng vấn 5 khách hàng mục tiêu", "Ghi chép pain point vào bảng theo dõi"],
      serviceToken: "local-dev-service-token",
    });

    expect(result.applied).toBe(true);
    const view = await getProjectOperatingSetupEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
    });
    expect(view.aiSuggestionStatus).toBe("completed");
    expect(view.aiSuggestedOutcome).toBe("Hoàn thành 5 cuộc phỏng vấn khách hàng mục tiêu");
    expect(view.aiSuggestedActions).toEqual([
      "Phỏng vấn 5 khách hàng mục tiêu",
      "Ghi chép pain point vào bảng theo dõi",
    ]);
  });

  it("no-op (applied=false) khi runId không khớp (đã bị request mới hơn ghi đè)", async () => {
    const { project } = await dispatchedProject();

    const result = await applyKickoffSuggestionResultEndpoint({
      id: project.id,
      runId: "run-khong-ton-tai",
      status: "completed",
      outcome: "x",
      actions: ["y"],
      serviceToken: "local-dev-service-token",
    });

    expect(result.applied).toBe(false);
  });

  it("cắt actions còn tối đa 3 và lọc action rỗng", async () => {
    const { ws, project, runId } = await dispatchedProject();

    await applyKickoffSuggestionResultEndpoint({
      id: project.id,
      runId,
      status: "completed",
      outcome: "x",
      actions: ["a", "  ", "b", "c", "d"],
      serviceToken: "local-dev-service-token",
    });

    const view = await getProjectOperatingSetupEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
    });
    expect(view.aiSuggestedActions).toEqual(["a", "b", "c"]);
  });

  it("throw unauthenticated khi thiếu serviceToken", async () => {
    const { project, runId } = await dispatchedProject();
    await expect(
      applyKickoffSuggestionResultEndpoint({
        id: project.id,
        runId,
        status: "completed",
      })
    ).rejects.toThrow();
  });

  it("throw unauthenticated khi serviceToken sai", async () => {
    const { project, runId } = await dispatchedProject();
    await expect(
      applyKickoffSuggestionResultEndpoint({
        id: project.id,
        runId,
        status: "completed",
        serviceToken: "wrong-token",
      })
    ).rejects.toThrow();
  });
});
