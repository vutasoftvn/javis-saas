import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { and, eq } from "drizzle-orm";
import { db } from "../models/db";
import * as schema from "../../shared/db/schema/strategy";
import { createProject } from "../handlers/project.handler";
import { createTestWorkspaceWithMember } from "./_helpers";
import {
  getProjectOperatingSetupEndpoint,
  putProjectOperatingSetupEndpoint,
  requestKickoffSuggestionEndpoint,
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
