import { MarketingContextDomainModel } from "../../domain/marketing/marketing-context";
import { DrizzleMarketingRepository } from "../../infrastructure/marketing/drizzle-marketing.repository";

export class MarketingContextQuery {
  constructor(private readonly repo: DrizzleMarketingRepository = new DrizzleMarketingRepository()) {}

  async getContext(workspaceId: string): Promise<MarketingContextDomainModel | null> {
    return this.repo.getContext(workspaceId);
  }
}
