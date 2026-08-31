// Facade re-exporting all marketing context domain services and DTOs

export {
  ProductMarketingDTO,
  UpdateProductMarketingParams,
  updateProductMarketingService,
} from "./product-marketing.service";

export {
  IcpSegmentDTO,
  CustomerResearchThemeDTO,
  CustomerLanguageDTO,
  MarketingContextEvidenceDTO,
  UpdateCustomerResearchParams,
  updateCustomerResearchService,
} from "./customer-research.service";

export {
  MarketingContextDTO,
  UpdateOfferArchitectureParams,
  UpdateTwelveWeekPlanParams,
  SubmitForReviewParams,
  ApproveContextParams,
  getOrCreateContextRow,
  assembleContextDTO,
  recordRevisionSnapshot,
  verifyOptimisticLock,
  getMarketingContextService,
  updateOfferArchitectureService,
  updateTwelveWeekPlanService,
  submitForReviewService,
  approveContextService,
} from "./marketing-snapshot.service";
