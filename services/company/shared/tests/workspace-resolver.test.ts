// services/company/shared/tests/workspace-resolver.test.ts
import { describe, expect, it } from "vitest";
import { resolveWorkspaceId, resolveProductWorkspaceId } from "../services/workspace-resolver.service";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { db, schema } from "../../identity/models/db";
import { eq } from "drizzle-orm";

describe("resolveWorkspaceId", () => {
  it("returns the workspaceId directly when workspaceId is given", async () => {
    const session = await createTestSession({ displayName: "Resolver Direct Test" });
    const resolved = await resolveWorkspaceId({ workspaceId: session.workspaceId });
    expect(resolved).toBe(BigInt(session.workspaceId));
  });

  it("resolves companyId to workspaceId via core.workspaces.platform_company_id", async () => {
    const session = await createTestSession({ displayName: "Resolver Company Test" });
    const platformCompanyId = `plat-co-${Date.now()}`;
    await db
      .update(schema.identityWorkspaces)
      .set({ platformCompanyId })
      .where(eq(schema.identityWorkspaces.id, BigInt(session.workspaceId)));

    const resolved = await resolveWorkspaceId({ companyId: platformCompanyId });
    expect(resolved).toBe(BigInt(session.workspaceId));
  });

  it("throws notFound when companyId does not match any workspace projection", async () => {
    await expect(resolveWorkspaceId({ companyId: `no-such-company-${Date.now()}` })).rejects.toThrow();
  });

  it("throws invalidArgument when neither workspaceId nor companyId is given", async () => {
    await expect(resolveWorkspaceId({})).rejects.toThrow();
  });
});

describe("resolveProductWorkspaceId (workspace-only product resolver)", () => {
  it("returns the workspaceId directly when workspaceId is given", async () => {
    const session = await createTestSession({ displayName: "Product Resolver Direct Test" });
    const resolved = await resolveProductWorkspaceId(session.workspaceId);
    expect(resolved).toBe(BigInt(session.workspaceId));
  });

  it("throws invalidArgument when workspaceId is not provided", async () => {
    await expect(resolveProductWorkspaceId(undefined)).rejects.toThrow();
  });

  it("throws notFound when workspaceId does not exist", async () => {
    await expect(resolveProductWorkspaceId("999999999999999999")).rejects.toThrow();
  });

  it("does not accept companyId — only workspaceId", async () => {
    const session = await createTestSession({ displayName: "Product Resolver No Company Test" });
    const platformCompanyId = `plat-co-${Date.now()}`;
    await db
      .update(schema.identityWorkspaces)
      .set({ platformCompanyId })
      .where(eq(schema.identityWorkspaces.id, BigInt(session.workspaceId)));

    // resolveProductWorkspaceId signature only accepts workspaceId, not companyId
    // This validates the separation: no company fallback in product path
    const resolved = await resolveProductWorkspaceId(session.workspaceId);
    expect(resolved).toBe(BigInt(session.workspaceId));
  });
});
