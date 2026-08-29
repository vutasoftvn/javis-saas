import { APIError } from "encore.dev/api";
import { eq, and, desc } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";

const { regulationSources, regulationVersions, legalObligationTemplates } = schema;

export interface RegulationVersionView {
  id: string;
  version: string;
  effectiveFrom: string;
  effectiveTo: string | null;
  isActive: boolean;
}

export interface RegulationSourceView {
  id: string;
  sourceName: string;
  issuer: string;
  number: string;
  url: string;
  layer: "CURRENT_LAW" | "POLICY_WATCH" | "PROFESSIONAL_REVIEW";
  versions: RegulationVersionView[];
}

export interface ObligationTemplateView {
  id: string;
  regulationVersionId: string;
  title: string;
  description: string | null;
  typicalDueOffsetDays: number | null;
  createdAt: string;
}

export async function listRegulationSources(filter?: {
  layer?: string;
  activeOnly?: boolean;
}): Promise<RegulationSourceView[]> {
  const sources = await db.select().from(regulationSources);
  const versions = await db.select().from(regulationVersions);

  const now = new Date().toISOString().split("T")[0]; // YYYY-MM-DD

  const versionMap = new Map<string, RegulationVersionView[]>();
  for (const v of versions) {
    const sId = String(v.regulationSourceId);
    const effFrom =
      typeof v.effectiveFrom === "string"
        ? v.effectiveFrom
        : new Date(v.effectiveFrom).toISOString().split("T")[0];
    const effTo = v.effectiveTo
      ? typeof v.effectiveTo === "string"
        ? v.effectiveTo
        : new Date(v.effectiveTo).toISOString().split("T")[0]
      : null;
    const isActive = effFrom <= now && (effTo === null || effTo > now);

    const list = versionMap.get(sId) || [];
    list.push({
      id: String(v.id),
      version: v.version,
      effectiveFrom: effFrom,
      effectiveTo: effTo,
      isActive,
    });
    versionMap.set(sId, list);
  }

  const results: RegulationSourceView[] = [];
  for (const s of sources) {
    if (filter?.layer && s.layer !== filter.layer) {
      continue;
    }
    const sVersions = versionMap.get(String(s.id)) || [];
    if (filter?.activeOnly) {
      const hasActive = sVersions.some((v) => v.isActive);
      if (!hasActive) continue;
    }
    results.push({
      id: String(s.id),
      sourceName: s.sourceName,
      issuer: s.issuer,
      number: s.number,
      url: s.url,
      layer: s.layer as any,
      versions: sVersions,
    });
  }

  return results;
}

export async function listObligationTemplates(
  regulationVersionId?: string
): Promise<ObligationTemplateView[]> {
  const query = regulationVersionId
    ? db
        .select()
        .from(legalObligationTemplates)
        .where(eq(legalObligationTemplates.regulationVersionId, BigInt(regulationVersionId)))
    : db.select().from(legalObligationTemplates);

  const rows = await query;
  return rows.map((r) => ({
    id: String(r.id),
    regulationVersionId: String(r.regulationVersionId),
    title: r.title,
    description: r.description,
    typicalDueOffsetDays: r.typicalDueOffsetDays,
    createdAt: r.createdAt.toISOString(),
  }));
}

export async function createRegulationVersion(p: {
  regulationSourceId: bigint;
  version: string;
  effectiveFrom: string;
  effectiveTo?: string;
  supersededById?: bigint;
}): Promise<{ id: string }> {
  const newId = generateSnowflake();
  await db.insert(regulationVersions).values({
    id: newId,
    regulationSourceId: p.regulationSourceId,
    version: p.version,
    effectiveFrom: p.effectiveFrom as any,
    effectiveTo: p.effectiveTo ? (p.effectiveTo as any) : null,
    supersededById: p.supersededById ?? null,
  });

  return { id: String(newId) };
}
