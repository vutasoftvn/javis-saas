import { describe, expect, it } from "vitest";
import fs from "node:fs";
import path from "node:path";

describe("Automation No-LLM & Determinism Guard", () => {
  it("should ensure automation/ directory contains 0 LLM imports, 0 eval, 0 new Function", () => {
    const automationDir = path.resolve(__dirname, "../../services/customer-engagement/automation");
    const files = fs.readdirSync(automationDir).filter((f) => f.endsWith(".ts"));

    expect(files.length).toBeGreaterThan(0);

    const forbiddenPatterns = [
      /\beval\s*\(/i,
      /\bnew\s+Function\b/i,
      /\bFunction\s*\(/i,
      /require\s*\(['"].*llm/i,
      /import.*from\s*['"].*(openai|deepseek|litellm|anthropic)/i,
    ];

    for (const file of files) {
      const content = fs.readFileSync(path.join(automationDir, file), "utf-8");
      for (const pattern of forbiddenPatterns) {
        const matches = content.match(pattern);
        expect(
          matches,
          `File ${file} must not contain forbidden pattern: ${pattern.toString()}`
        ).toBeNull();
      }
    }
  });
});
