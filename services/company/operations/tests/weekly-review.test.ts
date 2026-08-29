import { describe, it, expect } from "vitest";
import {
  createWeeklyReviewService,
  listWeeklyReviewsService,
  completeWeeklyReviewService,
} from "../strategy/services/weekly-review.service";
import { generateSnowflake } from "../../shared/services/snowflake.service";

describe("Weekly Review Loop (Phase 5 / Release E)", () => {
  const wsId = generateSnowflake();

  it("creates, queries, and completes weekly review with event audit", async () => {
    const review = await createWeeklyReviewService({
      workspaceId: wsId,
      weekStartDate: "2026-08-25",
      summary: "Completed 3 user interviews. Runway is 18 months. TT58 mode 1 selected.",
      stageAssessment: "Stage S1 nearing completion criteria.",
      cashSummary: "Cash in: 50,000,000 VND; Cash out: 12,000,000 VND",
      obligationsSummary: "1 tax declaration due next week.",
    });

    expect(review.id).toBeDefined();
    expect(review.status).toBe("DRAFT");

    const list = await listWeeklyReviewsService(wsId);
    expect(list.length).toBeGreaterThan(0);
    expect(list[0].id).toBe(review.id);

    const completed = await completeWeeklyReviewService({
      reviewId: BigInt(review.id),
      completedBy: 7777n,
    });
    expect(completed.status).toBe("COMPLETED");
  });
});
