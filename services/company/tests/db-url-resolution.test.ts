import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { readFileSync } from "node:fs";
import { resolveWorkspaceDatabaseUrl } from "../shared/db/client";

describe("resolveWorkspaceDatabaseUrl", () => {
  const originalWorkspaceUrl = process.env.WORKSPACE_DATABASE_URL;
  const originalCompanyUrl = process.env.COMPANY_DATABASE_URL;
  const originalDatabaseUrl = process.env.DATABASE_URL;
  const originalNodeEnv = process.env.NODE_ENV;

  beforeEach(() => {
    delete process.env.COMPANY_DATABASE_URL;
    delete process.env.WORKSPACE_DATABASE_URL;
    delete process.env.DATABASE_URL;
  });

  afterEach(() => {
    if (originalWorkspaceUrl !== undefined) {
      process.env.WORKSPACE_DATABASE_URL = originalWorkspaceUrl;
    } else {
      delete process.env.WORKSPACE_DATABASE_URL;
    }
    if (originalCompanyUrl !== undefined) {
      process.env.COMPANY_DATABASE_URL = originalCompanyUrl;
    } else {
      delete process.env.COMPANY_DATABASE_URL;
    }
    if (originalDatabaseUrl !== undefined) {
      process.env.DATABASE_URL = originalDatabaseUrl;
    } else {
      delete process.env.DATABASE_URL;
    }
    if (originalNodeEnv !== undefined) {
      process.env.NODE_ENV = originalNodeEnv;
    } else {
      delete process.env.NODE_ENV;
    }
  });

  it("throws descriptive error when WORKSPACE_DATABASE_URL is not set", () => {
    process.env.NODE_ENV = "development";
    expect(() => resolveWorkspaceDatabaseUrl()).toThrowError(/WORKSPACE_DATABASE_URL is required/);
  });

  it("error message does not contain hardcoded credentials", () => {
    try {
      resolveWorkspaceDatabaseUrl();
      expect.unreachable("should have thrown");
    } catch (err: any) {
      expect(err.message).not.toContain("cosa:cosa@");
      expect(err.message).toContain("WORKSPACE_DATABASE_URL");
    }
  });

  it("resolves WORKSPACE_DATABASE_URL when set", () => {
    process.env.WORKSPACE_DATABASE_URL = "postgresql://custom_user:pass@localhost:5433/custom_workspace";
    expect(resolveWorkspaceDatabaseUrl()).toBe("postgresql://custom_user:pass@localhost:5433/custom_workspace");
  });

  it("does not fall back to legacy COMPANY_DATABASE_URL or DATABASE_URL", () => {
    process.env.COMPANY_DATABASE_URL = "postgresql://legacy_user:pass@localhost:5433/company";
    process.env.DATABASE_URL = "postgresql://legacy_user:pass@localhost:5433/database";
    expect(() => resolveWorkspaceDatabaseUrl()).toThrowError(/WORKSPACE_DATABASE_URL is required/);
  });

  it("migration runner uses a dedicated WORKSPACE_MIGRATOR_DATABASE_URL, an advisory lock, and deterministic tie-breaking", () => {
    const source = readFileSync(new URL("../scripts/migrate.mjs", import.meta.url), "utf-8");

    expect(source).toContain("process.env.WORKSPACE_MIGRATOR_DATABASE_URL");
    expect(source).not.toContain("process.env.WORKSPACE_DATABASE_URL");
    expect(source).not.toContain("process.env.COMPANY_DATABASE_URL");
    expect(source).not.toContain("process.env.DATABASE_URL");
    expect(source).toContain("pg_advisory_lock");
    expect(source).toContain("localeCompare");
  });
});
