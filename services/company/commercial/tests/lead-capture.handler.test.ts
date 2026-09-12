import { describe, it, expect, beforeAll } from "vitest";
import * as crypto from "crypto";
import { db } from "../models/db";
import { projects } from "../../shared/db/schema/operations";
import { leadSources, projectLeadCaptureForms } from "../../shared/db/schema/commercial";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import {
  registerLandingPublicKey,
  canonicalJson,
} from "../services/lead-capture.service";
import { ingestLeadCapture } from "../handlers/lead-capture.handler";

describe("lead-capture.handler (Ed25519 signed ingestion)", () => {
  let keyPair: { publicKey: string; privateKey: string };
  const KEY_ID = "landing-test-key-1";

  beforeAll(() => {
    keyPair = crypto.generateKeyPairSync("ed25519", {
      publicKeyEncoding: { type: "spki", format: "pem" },
      privateKeyEncoding: { type: "pkcs8", format: "pem" },
    });
    registerLandingPublicKey(KEY_ID, keyPair.publicKey);
  });

  async function setupForm(workspaceId: string) {
    const projId = generateSnowflake();
    await db.insert(projects).values({ id: projId, workspaceId: BigInt(workspaceId), title: "Landing Project" });

    const sourceId = generateSnowflake();
    await db.insert(leadSources).values({
      id: sourceId,
      workspaceId: BigInt(workspaceId),
      projectId: projId,
      sourceType: "landing_form",
      label: "Early Access Form",
    });

    const formKey = `early-access-${Date.now()}`;
    const formId = generateSnowflake();
    await db.insert(projectLeadCaptureForms).values({
      id: formId,
      workspaceId: BigInt(workspaceId),
      projectId: projId,
      leadSourceId: sourceId,
      formKey,
      publicVerificationKeyId: KEY_ID,
      requiredConsentPurpose: "early_access_waitlist",
      requiredConsentVersion: "2026.1",
      active: true,
    });

    return { formKey, projectId: projId.toString() };
  }

  function signPayload(payload: any, timestamp: string, privateKey: string): string {
    const dataToSign = `${timestamp}.${canonicalJson(payload)}`;
    return crypto.sign(null, Buffer.from(dataToSign), privateKey).toString("base64");
  }

  it("successfully ingests valid signed landing event and prevents replay", async () => {
    const s = await createTestSession({ role: "admin" });
    const { formKey } = await setupForm(s.workspaceId);

    const eventId = `evt_${Date.now()}`;
    const timestamp = new Date().toISOString();
    const event = {
      formKey,
      eventId,
      occurredAt: timestamp,
      fieldValues: {
        fullName: "Beta Tester",
        email: "tester@example.com",
        company: "Beta Org",
      },
      consent: {
        purpose: "early_access_waitlist",
        policyVersion: "2026.1",
        acceptedAt: timestamp,
      },
    };

    const signature = signPayload(event, timestamp, keyPair.privateKey);

    const result = await ingestLeadCapture({
      ...event,
      keyId: KEY_ID,
      timestamp,
      signature,
    });

    expect(result.accepted).toBe(true);
    expect(result.eventId).toBe(eventId);
    expect(result.leadId).toBeDefined();

    // Replay with identical eventId
    const replayResult = await ingestLeadCapture({
      ...event,
      keyId: KEY_ID,
      timestamp,
      signature,
    });

    expect(replayResult.accepted).toBe(true);
    expect(replayResult.replayed).toBe(true);
    expect(replayResult.leadId).toBe(result.leadId);
  });

  it("rejects invalid signature", async () => {
    const s = await createTestSession({ role: "admin" });
    const { formKey } = await setupForm(s.workspaceId);

    const timestamp = new Date().toISOString();
    const event = {
      formKey,
      eventId: `evt_bad_sig_${Date.now()}`,
      occurredAt: timestamp,
      fieldValues: { fullName: "Hacker" },
      consent: {
        purpose: "early_access_waitlist",
        policyVersion: "2026.1",
        acceptedAt: timestamp,
      },
    };

    await expect(
      ingestLeadCapture({
        ...event,
        keyId: KEY_ID,
        timestamp,
        signature: "invalid-signature-base64",
      })
    ).rejects.toThrow(/Chữ ký Ed25519 không hợp lệ/);
  });

  it("rejects timestamp outside allowed skew (skew > 5 minutes)", async () => {
    const s = await createTestSession({ role: "admin" });
    const { formKey } = await setupForm(s.workspaceId);

    const oldTimestamp = new Date(Date.now() - 10 * 60 * 1000).toISOString(); // 10 minutes ago
    const event = {
      formKey,
      eventId: `evt_skew_${Date.now()}`,
      occurredAt: oldTimestamp,
      fieldValues: { fullName: "Late Guy" },
      consent: {
        purpose: "early_access_waitlist",
        policyVersion: "2026.1",
        acceptedAt: oldTimestamp,
      },
    };

    const signature = signPayload(event, oldTimestamp, keyPair.privateKey);

    await expect(
      ingestLeadCapture({
        ...event,
        keyId: KEY_ID,
        timestamp: oldTimestamp,
        signature,
      })
    ).rejects.toThrow(/Timestamp nằm ngoài giới hạn/);
  });

  it("rejects mismatched consent purpose", async () => {
    const s = await createTestSession({ role: "admin" });
    const { formKey } = await setupForm(s.workspaceId);

    const timestamp = new Date().toISOString();
    const event = {
      formKey,
      eventId: `evt_consent_${Date.now()}`,
      occurredAt: timestamp,
      fieldValues: { fullName: "Wrong Consent" },
      consent: {
        purpose: "unrelated_newsletter",
        policyVersion: "2026.1",
        acceptedAt: timestamp,
      },
    };

    const signature = signPayload(event, timestamp, keyPair.privateKey);

    await expect(
      ingestLeadCapture({
        ...event,
        keyId: KEY_ID,
        timestamp,
        signature,
      })
    ).rejects.toThrow(/không khớp với yêu cầu của form/);
  });
});
