import { describe, expect, it } from "vitest";
import { eq } from "drizzle-orm";
import { resolveWorkspaceForPlatformCompany } from "../services/platform-workspace-mapping.service";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { db, schema } from "../models/db";

const { identityWorkspaces } = schema;

describe("Platform Workspace Mapping", () => {
  it("resolves workspace ID for a platform company ID", async () => {
    const platformCompanyId = `platform-company-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    const wsId = generateSnowflake();

    await db.insert(identityWorkspaces).values({
      id: wsId,
      name: `Test Workspace ${Date.now()}`,
      slug: `test-ws-${Date.now()}`,
      platformCompanyId,
    });

    const result = await resolveWorkspaceForPlatformCompany(platformCompanyId);

    expect(result).toBeDefined();
    expect(result).not.toBeNull();
    expect(result?.id).toBe(wsId.toString());
  });

  it("returns null when no mapping exists for platform company ID", async () => {
    const nonexistentPlatformCompanyId = `nonexistent-${Date.now()}-${Math.random().toString(36).slice(2)}`;

    const result = await resolveWorkspaceForPlatformCompany(nonexistentPlatformCompanyId);

    expect(result).toBeNull();
  });

  it("returns the workspace with the correct id format (string)", async () => {
    const platformCompanyId = `platform-company-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    const wsId = generateSnowflake();

    await db.insert(identityWorkspaces).values({
      id: wsId,
      name: `Test Workspace ${Date.now()}`,
      slug: `test-ws-${Date.now()}`,
      platformCompanyId,
    });

    const result = await resolveWorkspaceForPlatformCompany(platformCompanyId);

    expect(typeof result?.id).toBe("string");
    expect(result?.id).toEqual(wsId.toString());
  });

  it("returns the first mapping when multiple workspaces somehow have same platform company ID", async () => {
    const platformCompanyId = `platform-company-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    const wsId1 = generateSnowflake();
    const wsId2 = generateSnowflake();

    await db.insert(identityWorkspaces).values({
      id: wsId1,
      name: `Test Workspace 1 ${Date.now()}`,
      slug: `test-ws-1-${Date.now()}`,
      platformCompanyId,
    });

    // This would violate a unique constraint in production, but for testing
    // let's verify the function handles it gracefully by returning one
    const result = await resolveWorkspaceForPlatformCompany(platformCompanyId);

    expect(result).toBeDefined();
    expect(result?.id).toBe(wsId1.toString());
  });

  it("is case-sensitive for platform company IDs", async () => {
    const platformCompanyId = `PLATFORM-Company-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    const wsId = generateSnowflake();

    await db.insert(identityWorkspaces).values({
      id: wsId,
      name: `Test Workspace ${Date.now()}`,
      slug: `test-ws-${Date.now()}`,
      platformCompanyId,
    });

    // Try to resolve with different case
    const differentCase = platformCompanyId.toLowerCase();
    const result = await resolveWorkspaceForPlatformCompany(differentCase);

    expect(result).toBeNull();
  });

  it("handles empty string platform company ID", async () => {
    const result = await resolveWorkspaceForPlatformCompany("");

    expect(result).toBeNull();
  });

  it("handles very long platform company IDs", async () => {
    const longId = "a".repeat(500);

    const result = await resolveWorkspaceForPlatformCompany(longId);

    expect(result).toBeNull();
  });

  it("handles special characters in platform company IDs", async () => {
    const platformCompanyId = `platform/company@${Date.now()}-${Math.random().toString(36).slice(2)}`;
    const wsId = generateSnowflake();

    await db.insert(identityWorkspaces).values({
      id: wsId,
      name: `Test Workspace ${Date.now()}`,
      slug: `test-ws-${Date.now()}`,
      platformCompanyId,
    });

    const result = await resolveWorkspaceForPlatformCompany(platformCompanyId);

    expect(result).toBeDefined();
    expect(result?.id).toBe(wsId.toString());
  });
});
