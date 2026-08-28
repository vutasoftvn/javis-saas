import { api, Header } from "encore.dev/api";
import type { BusinessEventEnvelope } from "../shared/events/envelope";
import { ingestKnowledgePublished } from "./services/knowledge-published.service";

export interface KnowledgePublishedRequest {
  envelope: BusinessEventEnvelope<Record<string, unknown>>;
  serviceToken?: Header<"X-Service-Token">;
}

/**
 * `apps/cosa` review/publish path POSTs the reviewed `knowledge.source.published.v1`
 * envelope here; it is appended to the shared `integration.event_outbox`.
 * expose:true (called cross-app over HTTP) but guarded by X-Service-Token.
 */
export const knowledgePublishedEndpoint = api(
  { method: "POST", expose: true, path: "/events/internal/knowledge-published" },
  async (req: KnowledgePublishedRequest): Promise<{ stored: true }> => {
    return ingestKnowledgePublished({ envelope: req.envelope, serviceToken: req.serviceToken });
  }
);
