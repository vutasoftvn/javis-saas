import { describe, expect, it } from "vitest";
import { sql } from "drizzle-orm";
import { db } from "../models/db";
import { listRegulationSources } from "../services/regulation-catalog.service";

describe("AI compliance schema and sources", () => {
  it("does not accept a non-advisory deployment", async () => {
    await expect(
      db.execute(
        sql`INSERT INTO legal.workspace_ai_deployments (id, workspace_id, system_version_id, mode, status, founder_member_id) VALUES (1, 1, 1, 'AUTONOMOUS', 'DRAFT', 1)`
      )
    ).rejects.toThrow();
  });

  it("creates official AI and data-protection sources at the intended layers", async () => {
    const sources = await listRegulationSources();
    expect(sources.find((x) => x.number === "134/2025/QH15")?.layer).toBe("CURRENT_LAW");
    expect(sources.find((x) => x.number === "804/QĐ-TTg")?.layer).toBe("POLICY_WATCH");
  });
});
