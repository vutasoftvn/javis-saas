import { describe, it, expect } from "vitest";
import * as crypto from "node:crypto";
import {
  buildSignedLeadCaptureEnvelope,
  canonicalJson,
} from "./cosa-company-lead-capture";

describe("cosa-company-lead-capture (Landing Ed25519 signing)", () => {
  it("builds a canonical signed envelope and verifies with public key", () => {
    const keyPair = crypto.generateKeyPairSync("ed25519", {
      publicKeyEncoding: { type: "spki", format: "pem" },
      privateKeyEncoding: { type: "pkcs8", format: "pem" },
    });

    const envelope = buildSignedLeadCaptureEnvelope({
      formKey: "landing-test-form",
      fieldValues: {
        email: "test@mivacorp.com",
        fullName: "Test User",
      },
      consent: {
        purpose: "early_access_waitlist",
        policyVersion: "2026.1",
        acceptedAt: "2026-09-12T10:00:00.000Z",
      },
      privateKeyPem: keyPair.privateKey,
      keyId: "landing-key-test",
      eventId: "fixed-event-id-123",
      occurredAt: "2026-09-12T10:00:00.000Z",
    });

    expect(envelope.headers["X-COSA-Landing-Key-Id"]).toBe("landing-key-test");
    expect(envelope.headers["X-COSA-Landing-Timestamp"]).toBe("2026-09-12T10:00:00.000Z");
    expect(envelope.headers["X-COSA-Landing-Signature"]).toBeDefined();

    // Verify signature directly
    const dataToVerify = `2026-09-12T10:00:00.000Z.${canonicalJson(envelope.event)}`;
    const sigBuffer = Buffer.from(envelope.headers["X-COSA-Landing-Signature"], "base64");
    const verified = crypto.verify(null, Buffer.from(dataToVerify), keyPair.publicKey, sigBuffer);

    expect(verified).toBe(true);
  });
});
