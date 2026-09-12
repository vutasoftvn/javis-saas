import { api, Header } from "encore.dev/api";
import {
  ingestLeadCaptureService,
  SignedLeadCaptureEvent,
  IngestLeadCaptureResult,
} from "../services/lead-capture.service";

export interface IngestLeadCaptureRequest extends SignedLeadCaptureEvent {
  keyId?: Header<"X-COSA-Landing-Key-Id">;
  timestamp?: Header<"X-COSA-Landing-Timestamp">;
  signature?: Header<"X-COSA-Landing-Signature">;
}

export const ingestLeadCapture = api(
  { method: "POST", path: "/commercial/lead-capture/:formKey/ingest", expose: true },
  async (req: IngestLeadCaptureRequest): Promise<IngestLeadCaptureResult> => {
    return ingestLeadCaptureService(
      req.formKey,
      {
        formKey: req.formKey,
        eventId: req.eventId,
        occurredAt: req.occurredAt,
        fieldValues: req.fieldValues,
        consent: req.consent,
      },
      {
        keyId: req.keyId,
        timestamp: req.timestamp,
        signature: req.signature,
      }
    );
  }
);
