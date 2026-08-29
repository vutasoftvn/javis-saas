import { APIError } from "encore.dev/api";
import { eq, and } from "drizzle-orm";
import { db, schema } from "../models/db";

const {
  legalEntityProfiles,
  regulationSources,
  regulationVersions,
  legalObligationTemplates,
  applicabilityRules,
  legalObligationInstances,
} = schema;

export interface ApplicableObligationView {
  obligationTemplateId: string;
  title: string;
  description: string | null;
  typicalDueDate: string | null;
  ruleId: string;
  sourceRegulationNumber: string;
  sourceRegulationVersion: string;
  layer: "CURRENT_LAW" | "POLICY_WATCH" | "PROFESSIONAL_REVIEW";
  matchedPredicate: Record<string, any>;
  hasExistingInstance: boolean;
  existingInstanceId?: string;
  existingInstanceStatus?: string;
}

export async function assessApplicableObligations(
  workspaceId: bigint
): Promise<ApplicableObligationView[]> {
  // 1. Get entity profile status
  const profiles = await db
    .select()
    .from(legalEntityProfiles)
    .where(eq(legalEntityProfiles.workspaceId, workspaceId));

  const profile = profiles.length > 0 ? profiles[0] : null;
  const entityStatus = profile?.status || "DRAFT";

  // 2. Query active versions of regulation sources
  const now = new Date().toISOString().split("T")[0];
  const sources = await db.select().from(regulationSources);
  const versions = await db.select().from(regulationVersions);

  const activeVersions = new Map<
    string,
    { sourceNumber: string; layer: string; version: string }
  >();
  for (const s of sources) {
    const sVersions = versions.filter((v) => v.regulationSourceId === s.id);
    for (const v of sVersions) {
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
      if (isActive) {
        activeVersions.set(String(v.id), {
          sourceNumber: s.number,
          layer: s.layer,
          version: v.version,
        });
      }
    }
  }

  // 3. Query all rules and templates
  const rules = await db.select().from(applicabilityRules);
  const templates = await db.select().from(legalObligationTemplates);

  // 4. Query existing instances for this workspace
  const existingInstances = await db
    .select()
    .from(legalObligationInstances)
    .where(eq(legalObligationInstances.workspaceId, workspaceId));

  const instanceMap = new Map<string, typeof legalObligationInstances.$inferSelect>();
  for (const inst of existingInstances) {
    if (inst.templateId) {
      instanceMap.set(String(inst.templateId), inst);
    }
  }

  const results: ApplicableObligationView[] = [];

  for (const rule of rules) {
    const verInfo = activeVersions.get(String(rule.regulationVersionId));
    if (!verInfo) continue; // Source version expired

    const predicate = (rule.predicate || {}) as Record<string, any>;
    if (predicate.entity_status && predicate.entity_status !== entityStatus) {
      continue;
    }

    const template = templates.find((t) => t.id === rule.obligationTemplateId);
    if (!template) continue;

    const existing = instanceMap.get(String(template.id));
    let typicalDue: string | null = null;
    if (template.typicalDueOffsetDays) {
      const d = new Date();
      d.setDate(d.getDate() + template.typicalDueOffsetDays);
      typicalDue = d.toISOString().split("T")[0];
    }

    results.push({
      obligationTemplateId: String(template.id),
      title: template.title,
      description: template.description,
      typicalDueDate: typicalDue,
      ruleId: String(rule.id),
      sourceRegulationNumber: verInfo.sourceNumber,
      sourceRegulationVersion: verInfo.version,
      layer: verInfo.layer as any,
      matchedPredicate: predicate,
      hasExistingInstance: existing !== undefined,
      existingInstanceId: existing ? String(existing.id) : undefined,
      existingInstanceStatus: existing ? existing.status : undefined,
    });
  }

  return results;
}
