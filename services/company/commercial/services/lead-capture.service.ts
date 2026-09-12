import { APIError } from "encore.dev/api";
import { and, eq } from "drizzle-orm";
import * as crypto from "crypto";
import { db, schema } from "../models/db";
import { ProjectLeadRepository } from "./project-lead-repository";
import { generateSnowflake } from "../../shared/services/snowflake.service";

const { projectLeadCaptureForms, leadIngestionEvents } = schema;

export interface SignedLeadCaptureEvent {
  formKey: string;
  eventId: string;
  occurredAt: string;
  fieldValues: Record<string, unknown>;
  consent: {
    purpose: string;
    lawfulBasis?: string;
    policyVersion: string;
    acceptedAt: string;
  };
}

export interface IngestLeadCaptureResult {
  accepted: boolean;
  replayed?: boolean;
  eventId: string;
  leadId?: string;
}

export function canonicalJson(obj: unknown): string {
  if (obj === null || typeof obj !== "object") {
    return JSON.stringify(obj);
  }
  if (Array.isArray(obj)) {
    return `[${obj.map((item) => canonicalJson(item)).join(",")}]`;
  }
  const sortedKeys = Object.keys(obj as Record<string, unknown>).sort();
  const pairs = sortedKeys.map(
    (k) => `${JSON.stringify(k)}:${canonicalJson((obj as Record<string, unknown>)[k])}`
  );
  return `{${pairs.join(",")}}`;
}

// In-memory key store for registered public keys (Key ID -> PEM or KeyObject)
const publicKeys = new Map<string, string>();

export function registerLandingPublicKey(keyId: string, publicKeyPem: string): void {
  publicKeys.set(keyId, publicKeyPem);
}

export function verifyEd25519Signature(
  keyId: string,
  timestamp: string,
  payload: SignedLeadCaptureEvent,
  signatureBase64: string
): boolean {
  const pubKey = publicKeys.get(keyId) || process.env[`COSA_LANDING_PUBKEY_${keyId}`];
  if (!pubKey) return false;

  const dataToVerify = `${timestamp}.${canonicalJson(payload)}`;
  try {
    const signature = Buffer.from(signatureBase64, "base64");
    return crypto.verify(null, Buffer.from(dataToVerify), pubKey, signature);
  } catch {
    return false;
  }
}

const MAX_TIMESTAMP_SKEW_MS = 300 * 1000; // 5 minutes

export async function ingestLeadCaptureService(
  formKey: string,
  event: SignedLeadCaptureEvent,
  headers: {
    keyId?: string;
    timestamp?: string;
    signature?: string;
  }
): Promise<IngestLeadCaptureResult> {
  const { keyId, timestamp, signature } = headers;
  if (!keyId || !timestamp || !signature) {
    throw APIError.unauthenticated("Thiếu chữ ký xác thực Ed25519 (headers X-COSA-Landing-*)");
  }

  // 1. Kiểm tra timestamp skew
  const parsedTime = Date.parse(timestamp);
  if (isNaN(parsedTime) || Math.abs(Date.now() - parsedTime) > MAX_TIMESTAMP_SKEW_MS) {
    throw APIError.invalidArgument("Timestamp nằm ngoài giới hạn cho phép (skew > 5 phút)");
  }

  // 2. Tìm capture form
  const [form] = await db
    .select()
    .from(projectLeadCaptureForms)
    .where(eq(projectLeadCaptureForms.formKey, formKey))
    .limit(1);

  if (!form || !form.active) {
    throw APIError.notFound(`Không tìm thấy capture form '${formKey}' hoặc form đang bị vô hiệu hoá`);
  }

  if (form.publicVerificationKeyId !== keyId) {
    throw APIError.permissionDenied("Key ID không khớp với cấu hình của capture form");
  }

  // 3. Xác thực chữ ký Ed25519
  const isValid = verifyEd25519Signature(keyId, timestamp, event, signature);
  if (!isValid) {
    throw APIError.unauthenticated("Chữ ký Ed25519 không hợp lệ hoặc dữ liệu đã bị biến đổi");
  }

  const wsId = form.workspaceId;
  const projId = form.projectId;

  // 4. Kiểm tra replay protection (idempotency)
  const [existingEvent] = await db
    .select()
    .from(leadIngestionEvents)
    .where(
      and(
        eq(leadIngestionEvents.workspaceId, wsId),
        eq(leadIngestionEvents.leadSourceId, form.leadSourceId),
        eq(leadIngestionEvents.externalEventId, event.eventId)
      )
    )
    .limit(1);

  if (existingEvent) {
    return {
      accepted: true,
      replayed: true,
      eventId: event.eventId,
      leadId: existingEvent.leadId ? String(existingEvent.leadId) : undefined,
    };
  }

  // 5. Kiểm tra consent
  if (!event.consent || !event.consent.purpose || !event.consent.policyVersion) {
    throw APIError.invalidArgument("Thông tin đồng ý (consent) là bắt buộc");
  }

  if (event.consent.purpose !== form.requiredConsentPurpose) {
    throw APIError.invalidArgument(
      `Mục đích consent '${event.consent.purpose}' không khớp với yêu cầu của form (${form.requiredConsentPurpose})`
    );
  }

  // 6. Tách standard fields và custom fields từ fieldValues
  const fv = { ...(event.fieldValues || {}) };
  const name = String(fv["name"] || fv["fullName"] || "Anonymous Lead");
  const email = fv["email"] ? String(fv["email"]) : undefined;
  const phone = fv["phone"] ? String(fv["phone"]) : undefined;
  const company = fv["company"] ? String(fv["company"]) : undefined;

  delete fv["name"];
  delete fv["fullName"];
  delete fv["email"];
  delete fv["phone"];
  delete fv["company"];

  // 7. Thực hiện trong transaction
  return await db.transaction(async (tx) => {
    const eventDbId = generateSnowflake();
    const digest = crypto
      .createHash("sha256")
      .update(canonicalJson(event))
      .digest("hex");

    // Lưu ingestion event trước (lead_id null tạm thời) để thoả FK provenance_event_id
    await tx.insert(leadIngestionEvents).values({
      id: BigInt(eventDbId),
      workspaceId: wsId,
      projectId: projId,
      leadSourceId: form.leadSourceId,
      captureFormId: form.id,
      externalEventId: event.eventId,
      payloadDigest: `sha256:${digest}`,
      signatureKeyId: keyId,
      leadId: null,
    });

    // Tạo Lead qua repository trong cùng transaction
    const lead = await ProjectLeadRepository.createLead(
      String(wsId),
      String(projId),
      {
        name,
        email,
        phone,
        company,
        leadSourceId: String(form.leadSourceId),
        provenanceEventId: String(eventDbId),
        fieldValues: fv,
        consent: {
          purpose: event.consent.purpose,
          lawfulBasis: event.consent.lawfulBasis || "CONSENT",
          policyVersion: event.consent.policyVersion,
          capturedAt: event.consent.acceptedAt,
        },
      },
      tx
    );

    // Cập nhật lead_id trong ingestion event
    await tx
      .update(leadIngestionEvents)
      .set({ leadId: BigInt(lead.id) })
      .where(eq(leadIngestionEvents.id, BigInt(eventDbId)));

    return {
      accepted: true,
      eventId: event.eventId,
      leadId: lead.id,
    };
  });
}
