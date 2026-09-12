import * as crypto from "node:crypto";

export interface LeadConsent {
  purpose: string;
  lawfulBasis?: string;
  policyVersion: string;
  acceptedAt: string;
}

export interface SignedLeadCaptureEvent {
  formKey: string;
  eventId: string;
  occurredAt: string;
  fieldValues: Record<string, unknown>;
  consent: LeadConsent;
}

export interface SignedHeaders {
  "X-COSA-Landing-Key-Id": string;
  "X-COSA-Landing-Timestamp": string;
  "X-COSA-Landing-Signature": string;
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

export function buildSignedLeadCaptureEnvelope(params: {
  formKey: string;
  fieldValues: Record<string, unknown>;
  consent: LeadConsent;
  privateKeyPem: string;
  keyId: string;
  eventId?: string;
  occurredAt?: string;
}): { event: SignedLeadCaptureEvent; headers: SignedHeaders } {
  const eventId = params.eventId || crypto.randomUUID();
  const occurredAt = params.occurredAt || new Date().toISOString();
  const timestamp = occurredAt;

  const event: SignedLeadCaptureEvent = {
    formKey: params.formKey,
    eventId,
    occurredAt,
    fieldValues: params.fieldValues,
    consent: params.consent,
  };

  const payloadString = `${timestamp}.${canonicalJson(event)}`;
  const signature = crypto.sign(null, Buffer.from(payloadString), params.privateKeyPem);

  return {
    event,
    headers: {
      "X-COSA-Landing-Key-Id": params.keyId,
      "X-COSA-Landing-Timestamp": timestamp,
      "X-COSA-Landing-Signature": signature.toString("base64"),
    },
  };
}

export async function submitLeadToCompany(params: {
  companyApiUrl: string;
  formKey: string;
  fieldValues: Record<string, unknown>;
  consent: LeadConsent;
  privateKeyPem: string;
  keyId: string;
}): Promise<{ success: boolean; data?: unknown; error?: string }> {
  const { event, headers } = buildSignedLeadCaptureEnvelope(params);
  const url = `${params.companyApiUrl.replace(/\/$/, "")}/commercial/lead-capture/${encodeURIComponent(params.formKey)}/ingest`;

  try {
    const res = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...headers,
      },
      body: JSON.stringify(event),
    });

    if (!res.ok) {
      const errText = await res.text();
      return { success: false, error: `Company returned status ${res.status}: ${errText}` };
    }

    const data = await res.json();
    return { success: true, data };
  } catch (err: unknown) {
    return { success: false, error: err instanceof Error ? err.message : "Unknown network error" };
  }
}
