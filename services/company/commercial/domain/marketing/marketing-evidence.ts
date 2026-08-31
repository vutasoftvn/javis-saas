export interface MarketingEvidenceItem {
  readonly id: string;
  readonly workspaceId: string;
  readonly evidenceId: string;
  readonly kind: "interview" | "survey" | "analytics" | "competitor_teardown" | "other";
  readonly sourceUrl: string | null;
  readonly capturedAt: string | null;
  readonly capturedBy: string | null;
  readonly confidence: "high" | "medium" | "low";
  readonly trust: "verified" | "unverified" | "derived";
  readonly sensitivity: "public" | "confidential" | "internal";
}
