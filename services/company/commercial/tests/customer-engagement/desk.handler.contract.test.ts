import { describe, expect, it } from "vitest";
import {
  createEngagementThreadApi,
  getEngagementThreadApi,
  listEngagementThreadsApi,
  sendEngagementPublicMessageApi,
  createDecisionRequestApi,
  recordDecisionApprovalApi,
  executeDecisionRequestApi,
} from "../../handlers/customer-engagement/desk.handler";

describe("customer engagement desk handler", () => {
  it("exports the authenticated desk entry points", () => {
    expect(createEngagementThreadApi).toBeDefined();
    expect(getEngagementThreadApi).toBeDefined();
    expect(listEngagementThreadsApi).toBeDefined();
    expect(sendEngagementPublicMessageApi).toBeDefined();
    expect(createDecisionRequestApi).toBeDefined();
    expect(recordDecisionApprovalApi).toBeDefined();
    expect(executeDecisionRequestApi).toBeDefined();
  });
});
