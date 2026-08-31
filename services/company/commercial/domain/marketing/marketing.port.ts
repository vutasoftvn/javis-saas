export interface MarketingContextRecord {
  readonly id: string;
  readonly workspaceId: string;
  readonly idealCustomerProfile: string | null;
  readonly valueProposition: string | null;
  readonly positioning: string | null;
  readonly brandVoice: string | null;
  readonly competitors: readonly string[];
  readonly updatedAt: Date;
}

export interface MarketingPort {
  getContext(workspaceId: string): Promise<MarketingContextRecord | null>;
  updateContext(
    workspaceId: string,
    params: Partial<Omit<MarketingContextRecord, "id" | "workspaceId" | "updatedAt">>
  ): Promise<MarketingContextRecord>;
}
