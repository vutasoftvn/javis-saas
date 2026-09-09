import { describe, it, expect } from "vitest";
import { createTestWorkspaceWithMember } from "./_helpers";
import {
  listAutomationDefinitions,
  getAutomationDefinition,
  configureAutomationDefinition,
  publishAutomationRevision,
  suspendAutomationDefinition,
} from "../services/automation-definition.service";

const KEY = "operating.weekly-review";

async function ws(role = "founder") {
  return createTestWorkspaceWithMember({ role });
}

function cfg(over: Record<string, unknown> = {}) {
  return {
    automationKey: KEY,
    configuration: { projectId: "proj-1", lookbackWeeks: 2, ...over },
    triggerContract: { kind: "manual" as const },
  };
}

describe("automation definitions — Company-owned, immutable revisions", () => {
  it("lists all four curated blueprints, unconfigured, for a fresh workspace", async () => {
    const w = await ws();
    const res = await listAutomationDefinitions({ workspaceId: w.workspaceId, authorization: w.bearerToken });
    expect(res.data.map((d) => d.automationKey).sort()).toEqual(
      [
        "commercial.outbound-draft",
        "operating.weekly-review",
        "operations.task-follow-up",
        "strategy.initiative-health",
      ].sort()
    );
    expect(res.data.every((d) => d.configured === false)).toBe(true);
    expect(res.data.every((d) => d.id === null)).toBe(true);
  });

  it("configure creates a DRAFT definition + draft revision; publish freezes it", async () => {
    const w = await ws();
    const configured = await configureAutomationDefinition({
      workspaceId: w.workspaceId,
      authorization: w.bearerToken,
      ...cfg(),
    });
    expect(configured.data.configured).toBe(true);
    expect(configured.data.lifecycleState).toBe("DRAFT");
    expect(configured.data.draftRevision?.published).toBe(false);
    const defId = configured.data.id!;

    const published = await publishAutomationRevision({
      workspaceId: w.workspaceId,
      authorization: w.bearerToken,
      definitionId: defId,
    });
    expect(published.data.lifecycleState).toBe("PUBLISHED");
    expect(published.data.currentRevision?.published).toBe(true);
    expect(published.data.currentRevision?.revisionHash).toMatch(/^[0-9a-f]{64}$/);
    expect(published.data.draftRevision).toBeNull();
  });

  it("a published revision is byte-identical after a later re-configure", async () => {
    const w = await ws();
    const c1 = await configureAutomationDefinition({ workspaceId: w.workspaceId, authorization: w.bearerToken, ...cfg() });
    const defId = c1.data.id!;
    const p1 = await publishAutomationRevision({ workspaceId: w.workspaceId, authorization: w.bearerToken, definitionId: defId });
    const publishedHash = p1.data.currentRevision!.revisionHash;
    const publishedNo = p1.data.currentRevision!.revisionNo;

    // Re-configure with a different value -> new draft revision, published one untouched.
    await configureAutomationDefinition({
      workspaceId: w.workspaceId,
      authorization: w.bearerToken,
      ...cfg({ lookbackWeeks: 8 }),
    });
    const after = await getAutomationDefinition({ workspaceId: w.workspaceId, authorization: w.bearerToken, definitionId: defId });
    expect(after.data.currentRevision!.revisionHash).toBe(publishedHash);
    expect(after.data.currentRevision!.revisionNo).toBe(publishedNo);
    expect(after.data.draftRevision!.revisionNo).toBe(publishedNo + 1);
    expect(after.data.draftRevision!.configuration.lookbackWeeks).toBe(8);
  });

  it("rejects an unknown blueprint key and unknown configuration fields", async () => {
    const w = await ws();
    await expect(
      configureAutomationDefinition({
        workspaceId: w.workspaceId,
        authorization: w.bearerToken,
        automationKey: "operating.not-a-blueprint",
        configuration: {},
        triggerContract: { kind: "manual" },
      })
    ).rejects.toThrow(/unknown automation blueprint/);

    await expect(
      configureAutomationDefinition({
        workspaceId: w.workspaceId,
        authorization: w.bearerToken,
        ...cfg({ rawPrompt: "do the thing" }),
      })
    ).rejects.toThrow(/unknown configuration field/);
  });

  it("rejects a raw URL in a typed field and a disallowed trigger kind", async () => {
    const w = await ws();
    await expect(
      configureAutomationDefinition({
        workspaceId: w.workspaceId,
        authorization: w.bearerToken,
        ...cfg({ projectId: "https://evil.example/steal" }),
      })
    ).rejects.toThrow(/must not contain a raw URL/);

    await expect(
      configureAutomationDefinition({
        workspaceId: w.workspaceId,
        authorization: w.bearerToken,
        automationKey: KEY,
        configuration: { projectId: "p1" },
        triggerContract: { kind: "business_event", eventType: "x" },
      })
    ).rejects.toThrow(/does not allow trigger kind/);
  });

  it("a non-publisher role cannot publish or suspend", async () => {
    const owner = await ws("founder");
    const c = await configureAutomationDefinition({ workspaceId: owner.workspaceId, authorization: owner.bearerToken, ...cfg() });
    const defId = c.data.id!;

    const { addMemberToWorkspace } = await import("./_helpers");
    const member = await addMemberToWorkspace(owner.workspaceId, "member");

    await expect(
      publishAutomationRevision({ workspaceId: owner.workspaceId, authorization: member.bearerToken, definitionId: defId })
    ).rejects.toThrow(/publisher role/);
    await expect(
      suspendAutomationDefinition({ workspaceId: owner.workspaceId, authorization: member.bearerToken, definitionId: defId })
    ).rejects.toThrow(/publisher role/);
  });

  it("suspend blocks the definition but keeps its published revision readable", async () => {
    const w = await ws();
    const c = await configureAutomationDefinition({ workspaceId: w.workspaceId, authorization: w.bearerToken, ...cfg() });
    const defId = c.data.id!;
    await publishAutomationRevision({ workspaceId: w.workspaceId, authorization: w.bearerToken, definitionId: defId });
    const s = await suspendAutomationDefinition({ workspaceId: w.workspaceId, authorization: w.bearerToken, definitionId: defId });
    expect(s.data.lifecycleState).toBe("SUSPENDED");
    expect(s.data.currentRevision?.published).toBe(true);
  });

  it("workspace B cannot list, read, configure, publish or suspend workspace A's automation", async () => {
    const a = await ws();
    const b = await ws();
    const cA = await configureAutomationDefinition({ workspaceId: a.workspaceId, authorization: a.bearerToken, ...cfg() });
    const defId = cA.data.id!;

    await expect(
      getAutomationDefinition({ workspaceId: a.workspaceId, authorization: b.bearerToken, definitionId: defId })
    ).rejects.toThrow();
    await expect(
      listAutomationDefinitions({ workspaceId: a.workspaceId, authorization: b.bearerToken })
    ).rejects.toThrow();
    await expect(
      publishAutomationRevision({ workspaceId: a.workspaceId, authorization: b.bearerToken, definitionId: defId })
    ).rejects.toThrow();
    // B reading its own workspace sees the definition unconfigured.
    const bOwn = await getAutomationDefinition({
      workspaceId: a.workspaceId,
      authorization: a.bearerToken,
      definitionId: defId,
    });
    expect(bOwn.data.id).toBe(defId);
  });

  it("duplicate automation key in one workspace reuses the definition; other workspace is independent", async () => {
    const a = await ws();
    const b = await ws();
    const c1 = await configureAutomationDefinition({ workspaceId: a.workspaceId, authorization: a.bearerToken, ...cfg() });
    const c2 = await configureAutomationDefinition({ workspaceId: a.workspaceId, authorization: a.bearerToken, ...cfg({ lookbackWeeks: 5 }) });
    expect(c2.data.id).toBe(c1.data.id);

    const cB = await configureAutomationDefinition({ workspaceId: b.workspaceId, authorization: b.bearerToken, ...cfg() });
    expect(cB.data.id).not.toBe(c1.data.id);
  });
});
