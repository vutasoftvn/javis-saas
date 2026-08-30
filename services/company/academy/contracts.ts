/**
 * Academy boundary contracts.
 *
 * ISOLATION RULES:
 * - Academy modules MUST NOT import from `operations/strategy` or `operations/handlers`.
 * - Strategy/evidence handlers MUST call assertNotAcademyReference() before any persistence.
 */

/** ACADEMY_ARTIFACT_SCHEME: the reserved URI scheme for all Academy-generated artifacts. */
export const ACADEMY_ARTIFACT_SCHEME = "academy-artifact://";

/** ACADEMY_ID_PREFIX: prefix that academy identifiers carry (academy_*). */
export const ACADEMY_ID_PREFIX = "academy_";

/** ACADEMY_TEMPLATE_KIND: the live artifact kind for exported templates. */
export const ACADEMY_TEMPLATE_DRAFT_KIND = "academy_template_draft";

/**
 * Asserts that a reference string is NOT an Academy reference.
 *
 * Throws if:
 * - ref starts with "academy-artifact://"
 * - ref starts with "academy_"
 *
 * Call this before any production evidence, gate evaluation, metric snapshot,
 * stage transition, task, pilot, or capability-enablement write.
 */
export function assertNotAcademyReference(ref: string | null | undefined, fieldName = "reference"): void {
  if (!ref) return;
  if (ref.startsWith(ACADEMY_ARTIFACT_SCHEME)) {
    throw new Error(
      `Production ${fieldName} cannot be an Academy artifact reference (academy-artifact://). ` +
      `Academy output is synthetic and must not enter the live evidence ledger.`
    );
  }
  if (ref.startsWith(ACADEMY_ID_PREFIX)) {
    throw new Error(
      `Production ${fieldName} cannot reference an Academy identifier (academy_*). ` +
      `Academy data is isolated from live projects, evidence, and gate evaluations.`
    );
  }
}

/**
 * Asserts that an artifact kind is NOT an Academy template draft.
 * Call before creating Evidence from a workspace artifact.
 */
export function assertNotAcademyTemplateDraft(kind: string | null | undefined, fieldName = "artifact kind"): void {
  if (!kind) return;
  if (kind === ACADEMY_TEMPLATE_DRAFT_KIND) {
    throw new Error(
      `Artifact of kind '${ACADEMY_TEMPLATE_DRAFT_KIND}' is ineligible for production evidence. ` +
      `A human must replace Academy template sources with independent real-world sources.`
    );
  }
}

/**
 * Returns true if a ref is an Academy artifact reference.
 * Safe to call anywhere for conditional checks.
 */
export function isAcademyReference(ref: string | null | undefined): boolean {
  if (!ref) return false;
  return ref.startsWith(ACADEMY_ARTIFACT_SCHEME) || ref.startsWith(ACADEMY_ID_PREFIX);
}
