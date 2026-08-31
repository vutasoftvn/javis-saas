import { describe, expect, it } from "vitest";
// @ts-expect-error script has no .d.ts
import { runCheck } from "../../../../scripts/check_company_boundaries.mjs";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";

describe("Company Commercial Module Boundaries", () => {
  it("rejects application use-case importing HTTP handlers", () => {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "company-comm-test-"));
    try {
      const appDir = path.join(tmpDir, "commercial", "application", "marketing");
      fs.mkdirSync(appDir, { recursive: true });

      // Bad file: application importing handler
      fs.writeFileSync(
        path.join(appDir, "bad-app.ts"),
        `import { someHandler } from "../../handlers/marketing.handler";\nexport const x = 1;\n`
      );

      const violations = runCheck(tmpDir);
      expect(violations.some((v: string) => v.includes("APPLICATION_HANDLER_IMPORT"))).toBe(true);
    } finally {
      fs.rmSync(tmpDir, { recursive: true, force: true });
    }
  });

  it("passes for clean commercial domain and application separation", () => {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "company-comm-test-"));
    try {
      const domainDir = path.join(tmpDir, "commercial", "domain", "marketing");
      const appDir = path.join(tmpDir, "commercial", "application", "marketing");
      fs.mkdirSync(domainDir, { recursive: true });
      fs.mkdirSync(appDir, { recursive: true });

      fs.writeFileSync(
        path.join(domainDir, "marketing-context.ts"),
        `export interface MarketingContext { id: string; }\n`
      );

      fs.writeFileSync(
        path.join(appDir, "context-query.ts"),
        `import { MarketingContext } from "../../domain/marketing/marketing-context";\nexport class Query {}\n`
      );

      const violations = runCheck(tmpDir);
      expect(violations).toHaveLength(0);
    } finally {
      fs.rmSync(tmpDir, { recursive: true, force: true });
    }
  });
});
