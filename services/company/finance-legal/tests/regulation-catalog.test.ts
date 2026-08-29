import { describe, expect, it } from "vitest";
import {
  listRegulationSources,
  listObligationTemplates,
  createRegulationVersion,
} from "../services/regulation-catalog.service";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";

const { regulationSources, regulationVersions } = schema;

describe("regulation-catalog service", () => {
  it("creates and lists regulation sources with versions", async () => {
    const sourceId = generateSnowflake();
    await db.insert(regulationSources).values({
      id: sourceId,
      sourceName: "Test Regulation Circular",
      issuer: "Ministry of Finance",
      number: `TEST-${Date.now()}/TT-BTC`,
      url: "https://example.gov.vn/test",
      layer: "CURRENT_LAW",
    });

    const ver = await createRegulationVersion({
      regulationSourceId: sourceId,
      version: "2026",
      effectiveFrom: "2026-01-01",
    });
    expect(ver.id).toBeTruthy();

    const sources = await listRegulationSources({ layer: "CURRENT_LAW" });
    const found = sources.find((s) => s.id === String(sourceId));
    expect(found).toBeDefined();
    expect(found?.versions.length).toBeGreaterThanOrEqual(1);
    expect(found?.versions[0].isActive).toBe(true);
  });

  it("filters out inactive sources when activeOnly=true", async () => {
    const sourceId = generateSnowflake();
    await db.insert(regulationSources).values({
      id: sourceId,
      sourceName: "Future Regulation Circular",
      issuer: "Ministry of Finance",
      number: `FUTURE-${Date.now()}/TT-BTC`,
      url: "https://example.gov.vn/future",
      layer: "CURRENT_LAW",
    });

    // Future version effective in 2099
    await createRegulationVersion({
      regulationSourceId: sourceId,
      version: "2099",
      effectiveFrom: "2099-01-01",
    });

    const activeSources = await listRegulationSources({ activeOnly: true });
    const found = activeSources.find((s) => s.id === String(sourceId));
    expect(found).toBeUndefined();
  });
});
