import { describe, expect, it } from "vitest";
// @ts-expect-error script has no .d.ts
import { runCheck } from "../../../../scripts/check_company_boundaries.mjs";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";

describe("Company Operations Module Boundaries", () => {
  it("rejects domain layer importing Encore, DB, or outer layers", () => {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "company-bound-test-"));
    try {
      const domainDir = path.join(tmpDir, "operations", "domain");
      fs.mkdirSync(domainDir, { recursive: true });

      // Bad file: domain importing encore.dev
      fs.writeFileSync(
        path.join(domainDir, "bad-domain.ts"),
        `import { APIError } from "encore.dev/api";\nexport const x = 1;\n`
      );

      const violations = runCheck(tmpDir);
      expect(violations.some((v: string) => v.includes("DOMAIN_ENCORE_IMPORT"))).toBe(true);
    } finally {
      fs.rmSync(tmpDir, { recursive: true, force: true });
    }
  });

  it("passes for clean domain, application, and infrastructure separation", () => {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "company-bound-test-"));
    try {
      const domainDir = path.join(tmpDir, "operations", "domain");
      const appDir = path.join(tmpDir, "operations", "application");
      fs.mkdirSync(domainDir, { recursive: true });
      fs.mkdirSync(appDir, { recursive: true });

      fs.writeFileSync(
        path.join(domainDir, "clean-model.ts"),
        `export interface CleanModel { id: string; }\n`
      );

      fs.writeFileSync(
        path.join(appDir, "clean-use-case.ts"),
        `import { CleanModel } from "../domain/clean-model";\nexport class UseCase { run(m: CleanModel) {} }\n`
      );

      const violations = runCheck(tmpDir);
      expect(violations).toHaveLength(0);
    } finally {
      fs.rmSync(tmpDir, { recursive: true, force: true });
    }
  });
});
