export interface ProductMarketingDomain {
  readonly category: string | null;
  readonly positioningStatement: string | null;
  readonly alternatives: readonly Record<string, unknown>[];
  readonly differentiators: readonly Record<string, unknown>[];
  readonly brandVoice: Record<string, unknown>;
}

export interface IcpSegmentDomain {
  readonly id: string;
  readonly segment: string;
  readonly confidence: string;
  readonly evidenceIds: readonly string[];
}

export interface CustomerResearchThemeDomain {
  readonly id: string;
  readonly type: string;
  readonly summary: string;
  readonly confidence: string;
  readonly evidenceIds: readonly string[];
}

export interface CustomerLanguageDomain {
  readonly id: string;
  readonly quote: string;
  readonly sourceId: string | null;
  readonly capturedAt: string | null;
}

export interface MarketingEvidenceDomain {
  readonly id: string;
  readonly evidenceId: string;
  readonly kind: string;
  readonly sourceUrl: string | null;
  readonly capturedAt: string | null;
  readonly capturedBy: string | null;
  readonly confidence: string;
  readonly trust: string;
  readonly sensitivity: string;
}

export interface MarketingContextDomainModel {
  readonly id: string;
  readonly workspaceId: string;
  readonly revision: number;
  readonly status: string;
  readonly updatedByUserId: string | null;
  readonly reviewedByUserId: string | null;
  readonly reviewedAt: string | null;
  readonly sourceSkillId: string | null;
  readonly sourceSkillVersion: string | null;
  readonly sourceSkillHash: string | null;
  readonly productMarketing: ProductMarketingDomain;
  readonly icpSegments: readonly IcpSegmentDomain[];
  readonly customerResearchThemes: readonly CustomerResearchThemeDomain[];
  readonly customerLanguage: readonly CustomerLanguageDomain[];
  readonly evidence: readonly MarketingEvidenceDomain[];
  readonly offerArchitecture: Record<string, unknown> | null;
  readonly twelveWeekPlan: Record<string, unknown> | null;
  readonly createdAt: string;
  readonly updatedAt: string;
}
