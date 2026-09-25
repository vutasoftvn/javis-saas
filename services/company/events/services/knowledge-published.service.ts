import { APIError } from "encore.dev/api";
import { db } from "../../operations/db";
import { validateEnvelope, type BusinessEventEnvelope } from "../../shared/events/envelope";
import { appendOutboxEvent } from "../../shared/events/outbox.repository";
import { requireWorkerServiceAuth } from "../../shared/auth/worker-service-auth";

export interface IngestKnowledgePublishedRequest {
  envelope: BusinessEventEnvelope<Record<string, unknown>>;
  serviceToken?: string;
  authorization?: string;
}

/**
 * Nhận `knowledge.source.published.v1` từ AgentOS (`apps/cosa`, review/publish
 * path) và ghi vào `integration.event_outbox` — dùng chung một outbox duy nhất
 * với các producer khác (P0). `apps/cosa` không ghi trực tiếp bảng này vì dùng
 * DB khác (`AGENT_DATABASE_URL`).
 */
export async function ingestKnowledgePublished(
  req: IngestKnowledgePublishedRequest
): Promise<{ stored: true }> {
  // Worker JWT ký bởi apps/cosa (spec 2026-09-25 §5) — không còn so chuỗi token thô.
  await requireWorkerServiceAuth({ serviceToken: req.serviceToken, authorization: req.authorization });
  validateEnvelope(req.envelope);
  if (req.envelope.eventType !== "knowledge.source.published.v1") {
    throw APIError.invalidArgument(
      `eventType must be knowledge.source.published.v1, got ${req.envelope.eventType}`
    );
  }
  await db.transaction((tx) => appendOutboxEvent(tx, req.envelope));
  return { stored: true };
}
