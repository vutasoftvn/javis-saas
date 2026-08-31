import { DrizzleMarketingRepository } from "../../infrastructure/marketing/drizzle-marketing.repository";
import { MarketingContextDomainModel } from "../../domain/marketing/marketing-context";

export interface UpdateProductMarketingInput {
  readonly workspaceId: string;
  readonly actorUserId: string;
  readonly category?: string;
  readonly positioningStatement?: string;
  readonly alternatives?: readonly Record<string, unknown>[];
  readonly differentiators?: readonly Record<string, unknown>[];
  readonly brandVoice?: Record<string, unknown>;
}

export class MarketingContextCommand {
  constructor(private readonly repo: DrizzleMarketingRepository = new DrizzleMarketingRepository()) {}

  async ensureContext(workspaceId: string, actorUserId: string): Promise<MarketingContextDomainModel> {
    return this.repo.getOrCreateContext(workspaceId, actorUserId);
  }
}
