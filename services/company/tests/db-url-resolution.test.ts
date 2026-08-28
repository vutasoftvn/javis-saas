import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { resolveCompanyDatabaseUrl } from "../shared/db/client";

describe("resolveCompanyDatabaseUrl", () => {
  const originalCompanyUrl = process.env.COMPANY_DATABASE_URL;
  const originalDatabaseUrl = process.env.DATABASE_URL;
  const originalNodeEnv = process.env.NODE_ENV;

  beforeEach(() => {
    delete process.env.COMPANY_DATABASE_URL;
    delete process.env.DATABASE_URL;
  });

  afterEach(() => {
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

  it("throws descriptive error when neither COMPANY_DATABASE_URL nor DATABASE_URL is set", () => {
    process.env.NODE_ENV = "development";
    expect(() => resolveCompanyDatabaseUrl()).toThrowError(
      /COMPANY_DATABASE_URL \(hoặc DATABASE_URL\) is required/
    );
  });

  it("error message does not contain hardcoded credentials", () => {
    try {
      resolveCompanyDatabaseUrl();
      expect.unreachable("should have thrown");
    } catch (err: any) {
      expect(err.message).not.toContain("cosa:cosa@");
      expect(err.message).toContain("COMPANY_DATABASE_URL");
    }
  });

  it("resolves COMPANY_DATABASE_URL when set", () => {
    process.env.COMPANY_DATABASE_URL = "postgresql://custom_user:pass@localhost:5433/custom_company";
    expect(resolveCompanyDatabaseUrl()).toBe("postgresql://custom_user:pass@localhost:5433/custom_company");
  });

  it("falls back to DATABASE_URL when set", () => {
    process.env.DATABASE_URL = "postgresql://db_user:pass@localhost:5433/db_company";
    expect(resolveCompanyDatabaseUrl()).toBe("postgresql://db_user:pass@localhost:5433/db_company");
  });
});
