import { describe, it, expect } from "vitest";
import { createTestWorkspaceWithMember } from "./_helpers";
import {
  listAutomationDefinitionsEndpoint,
  configureAutomationDefinitionEndpoint,
  publishAutomationRevisionEndpoint,
  suspendAutomationDefinitionEndpoint,
} from "../handlers/automation-definition.handler";

const KEY = "operating.weekly-review";

describe("automation definition handlers — auth on the request path", () => {
  it("configure + publish + suspend flow through the endpoints", async () => {
    const w = await createTestWorkspaceWithMember({ role: "founder" });
    const configured = await configureAutomationDefinitionEndpoint({
      authorization: w.bearerToken,
      workspaceId: w.workspaceId,
      definitionId: "unused",
      automationKey: KEY,
      configuration: { projectId: "p1" },
      triggerContract: { kind: "manual" },
    });
    const defId = configured.data.id!;
    expect(configured.data.lifecycleState).toBe("DRAFT");

    const published = await publishAutomationRevisionEndpoint({
      authorization: w.bearerToken,
      workspaceId: w.workspaceId,
      definitionId: defId,
    });
    expect(published.data.lifecycleState).toBe("PUBLISHED");

    const suspended = await suspendAutomationDefinitionEndpoint({
      authorization: w.bearerToken,
      workspaceId: w.workspaceId,
      definitionId: defId,
    });
    expect(suspended.data.lifecycleState).toBe("SUSPENDED");
  });

  it("missing Authorization is rejected before any work happens", async () => {
    const w = await createTestWorkspaceWithMember({ role: "founder" });
    await expect(
      listAutomationDefinitionsEndpoint({
        authorization: undefined,
        workspaceId: w.workspaceId,
      })
    ).rejects.toThrow();
  });

  it("a foreign workspace token cannot reach the service", async () => {
    const a = await createTestWorkspaceWithMember({ role: "founder" });
    const b = await createTestWorkspaceWithMember({ role: "founder" });
    await expect(
      listAutomationDefinitionsEndpoint({
        authorization: b.bearerToken,
        workspaceId: a.workspaceId,
      })
    ).rejects.toThrow();
  });
});
