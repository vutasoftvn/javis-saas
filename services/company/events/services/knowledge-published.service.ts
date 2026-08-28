import { APIError } from "encore.dev/api";
import { db } from "../../operations/db";
import { validateEnvelope, type BusinessEventEnvelope } from "../../shared/events/envelope";
import { appendOutboxEvent } from "../../shared/events/outbox.repository";

export interface IngestKnowledgePublishedRequest {
  envelope: BusinessEventEnvelope<Record<string, unknown>>;
  serviceToken?: string;
}

/**
 * Nhận `knowledge.source.published.v1` từ AgentOS (`apps/cosa`, review/publish
 * path) và ghi vào `integration.event_outbox` — dùng chung một outbox duy nhất
 * với các producer khác (P0). `apps/cosa` không ghi trực tiếp bảng này vì dùng
 * DB khác (`AGENT_CORE_DATABASE_URL`).
 */
export async function ingestKnowledgePublished(
  req: IngestKnowledgePublishedRequest,
  expectedToken: string = process.env.COSA_WORKER_SERVICE_TOKEN ?? ""
): Promise<{ stored: true }> {
  if (!expectedToken || req.serviceToken !== expectedToken) {
    throw APIError.unauthenticated("invalid service token");
  }
  validateEnvelope(req.envelope);
  if (req.envelope.eventType !== "knowledge.source.published.v1") {
    throw APIError.invalidArgument(
      `eventType must be knowledge.source.published.v1, got ${req.envelope.eventType}`
    );
  }
  await db.transaction((tx) => appendOutboxEvent(tx, req.envelope));
  return { stored: true };
}
