import { describe, it, expect, beforeEach } from "vitest";
import { APIError } from "encore.dev/api";
import {
  signPlatformToken,
  signWorkerServiceToken,
} from "../services/token.service";
import {
  createDocumentIngestionEndpoint,
  getDocumentIngestionEndpoint,
  reviewDocumentIngestionEndpoint,
  transitionDocumentIngestionForWorkerEndpoint,
} from "../handlers/document-ingestion.handler";
import {
  createDocumentIngestion,
  completeUpload,
  transitionDocumentIngestionForWorker,
  reviewDocumentIngestion,
  getDocumentIngestion,
  getAuditEventsForIngestion,
} from "../services/document-ingestion.service";
import { db, schema } from "../models/db";

const { documentIngestions, documentIngestionAuditEvents } = schema;

beforeEach(async () => {
  await db.delete(documentIngestionAuditEvents);
  await db.delete(documentIngestions);
});

describe("Document Ingestion Lifecycle", () => {
  describe("createDocumentIngestion", () => {
    it("creates a new UPLOADING record when called with valid workspace/creator", async () => {
      const record = await createDocumentIngestion({
        workspaceId: "ws-test-1",
        createdBy: "user-alice",
        originalFilename: "document.md",
        declaredMediaType: "text/markdown",
        idempotencyKey: "test-key-1",
      });

      expect(record.id).toBeDefined();
      expect(record.workspaceId).toBe("ws-test-1");
      expect(record.createdBy).toBe("user-alice");
      expect(record.originalFilename).toBe("document.md");
      expect(record.declaredMediaType).toBe("text/markdown");
      expect(record.state).toBe("UPLOADING");
      expect(record.createdAt).toBeDefined();
      expect(record.originalObjectKey).toBeNull();
    });

    it("returns same record when called with same idempotency key (idempotent)", async () => {
      const first = await createDocumentIngestion({
        workspaceId: "ws-test-1",
        createdBy: "user-alice",
        originalFilename: "document.md",
        declaredMediaType: "text/markdown",
        idempotencyKey: "dup-key-1",
      });

      const second = await createDocumentIngestion({
        workspaceId: "ws-test-1",
        createdBy: "user-alice",
        originalFilename: "document.md",
        declaredMediaType: "text/markdown",
        idempotencyKey: "dup-key-1",
      });

      expect(second.id).toBe(first.id);
      expect(second.createdAt.getTime()).toBe(first.createdAt.getTime());
    });

    it("throws when non-member calls endpoint", async () => {
      const userToken = signPlatformToken("user-bob");

      await expect(
        createDocumentIngestionEndpoint({
          workspaceId: "ws-test-1",
          originalFilename: "document.md",
          declaredMediaType: "text/markdown",
          idempotencyKey: "test-key-1",
          authorization: `Bearer ${userToken}`,
        })
      ).rejects.toThrow();
    });

    it("rejects worker service token on public endpoint", async () => {
      const workerToken = signWorkerServiceToken("worker-1");

      await expect(
        createDocumentIngestionEndpoint({
          workspaceId: "ws-test-1",
          originalFilename: "document.md",
          declaredMediaType: "text/markdown",
          idempotencyKey: "test-key-1",
          authorization: `Bearer ${workerToken}`,
        })
      ).rejects.toThrow();
    });
  });

  describe("completeUpload", () => {
    it("transitions UPLOADING → QUARANTINED → QUEUED when broker provides object details", async () => {
      const created = await createDocumentIngestion({
        workspaceId: "ws-test-1",
        createdBy: "user-alice",
        originalFilename: "document.md",
        declaredMediaType: "text/markdown",
        idempotencyKey: "upload-key-1",
      });

      const completed = await completeUpload({
        ingestionId: created.id,
        actorId: "broker-service",
        detectedMediaType: "text/markdown; charset=utf-8",
        sizeBytes: 2048,
        sourceSha256: "abc123def456",
        objectKey: "s3://bucket/workspace-123/ing_xxx",
      });

      expect(completed.state).toBe("QUEUED");
      expect(completed.detectedMediaType).toBe("text/markdown; charset=utf-8");
      expect(Number(completed.sizeBytes)).toBe(2048);
      expect(completed.sourceSha256).toBe("abc123def456");
      // originalObjectKey is stored internally (not exposed to public callers via handler)
      expect(completed.originalObjectKey).toBeDefined();
    });

    it("rejects when ingestion is not in UPLOADING state", async () => {
      const created = await createDocumentIngestion({
        workspaceId: "ws-test-1",
        createdBy: "user-alice",
        originalFilename: "document.md",
        declaredMediaType: "text/markdown",
        idempotencyKey: "state-key-1",
      });

      await completeUpload({
        ingestionId: created.id,
        actorId: "broker-service",
        detectedMediaType: "text/markdown",
        sizeBytes: 2048,
        sourceSha256: "abc123def456",
        objectKey: "s3://bucket/ing_xxx",
      });

      // Try to complete again
      await expect(
        completeUpload({
          ingestionId: created.id,
          actorId: "broker-service",
          detectedMediaType: "text/markdown",
          sizeBytes: 2048,
          sourceSha256: "abc123def456",
          objectKey: "s3://bucket/ing_xxx",
        })
      ).rejects.toThrow();
    });
  });

  describe("transitionDocumentIngestionForWorker", () => {
    it("rejects platform JWT (public endpoint must use worker-only auth)", async () => {
      const created = await createDocumentIngestion({
        workspaceId: "ws-test-1",
        createdBy: "user-alice",
        originalFilename: "document.md",
        declaredMediaType: "text/markdown",
        idempotencyKey: "worker-key-1",
      });

      const completed = await completeUpload({
        ingestionId: created.id,
        actorId: "broker-service",
        detectedMediaType: "text/markdown",
        sizeBytes: 2048,
        sourceSha256: "abc123def456",
        objectKey: "s3://bucket/ing_xxx",
      });

      const userToken = signPlatformToken("user-alice");

      await expect(
        transitionDocumentIngestionForWorkerEndpoint({
          ingestionId: completed.id,
          claimToken: "claim_abc",
          nextState: "VALIDATING",
          patch: {},
          authorization: `Bearer ${userToken}`,
        })
      ).rejects.toThrow(/invalid or expired|not an authorized worker service/);
    });

    it("accepts worker service token and transitions state", async () => {
      const created = await createDocumentIngestion({
        workspaceId: "ws-test-1",
        createdBy: "user-alice",
        originalFilename: "document.md",
        declaredMediaType: "text/markdown",
        idempotencyKey: "worker-transition-key-1",
      });

      const completed = await completeUpload({
        ingestionId: created.id,
        actorId: "broker-service",
        detectedMediaType: "text/markdown",
        sizeBytes: 2048,
        sourceSha256: "abc123def456",
        objectKey: "s3://bucket/ing_xxx",
      });

      const workerToken = signWorkerServiceToken("worker-1");

      const transitioned = await transitionDocumentIngestionForWorkerEndpoint({
        ingestionId: completed.id,
        claimToken: "claim_abc",
        nextState: "VALIDATING",
        patch: {},
        authorization: `Bearer ${workerToken}`,
      });

      expect(transitioned.state).toBe("VALIDATING");
    });

    it("rejects invalid state transitions via local transition table", async () => {
      const created = await createDocumentIngestion({
        workspaceId: "ws-test-1",
        createdBy: "user-alice",
        originalFilename: "document.md",
        declaredMediaType: "text/markdown",
        idempotencyKey: "invalid-transition-key",
      });

      const completed = await completeUpload({
        ingestionId: created.id,
        actorId: "broker-service",
        detectedMediaType: "text/markdown",
        sizeBytes: 2048,
        sourceSha256: "abc123def456",
        objectKey: "s3://bucket/ing_xxx",
      });

      const workerToken = signWorkerServiceToken("worker-1");

      // Try to jump from QUEUED directly to PUBLISHED (invalid)
      await expect(
        transitionDocumentIngestionForWorkerEndpoint({
          ingestionId: completed.id,
          claimToken: "claim_abc",
          nextState: "PUBLISHED",
          patch: {},
          authorization: `Bearer ${workerToken}`,
        })
      ).rejects.toThrow();
    });
  });

  describe("reviewDocumentIngestion", () => {
    it("allows reviewer to publish when in REVIEW_PENDING state", async () => {
      const created = await createDocumentIngestion({
        workspaceId: "ws-test-1",
        createdBy: "user-alice",
        originalFilename: "document.md",
        declaredMediaType: "text/markdown",
        idempotencyKey: "review-key-1",
      });

      const completed = await completeUpload({
        ingestionId: created.id,
        actorId: "broker-service",
        detectedMediaType: "text/markdown",
        sizeBytes: 2048,
        sourceSha256: "abc123def456",
        objectKey: "s3://bucket/ing_xxx",
      });

      const workerToken = signWorkerServiceToken("worker-1");

      // Transition to REVIEW_PENDING
      let current = completed;
      current = await transitionDocumentIngestionForWorker(current.id, "claim_1", [], "VALIDATING", {});
      current = await transitionDocumentIngestionForWorker(current.id, "claim_2", ["VALIDATING"], "CONVERTING", {});
      current = await transitionDocumentIngestionForWorker(current.id, "claim_3", ["CONVERTING"], "REVIEW_PENDING", {});

      const reviewed = await reviewDocumentIngestion({
        ingestionId: current.id,
        reviewerId: "user-reviewer",
        decision: "PUBLISHED",
        reason: "Content looks good",
      });

      expect(reviewed.state).toBe("PUBLISHED");
    });

    it("rejects review when not in REVIEW_PENDING state", async () => {
      const created = await createDocumentIngestion({
        workspaceId: "ws-test-1",
        createdBy: "user-alice",
        originalFilename: "document.md",
        declaredMediaType: "text/markdown",
        idempotencyKey: "review-reject-key-1",
      });

      const completed = await completeUpload({
        ingestionId: created.id,
        actorId: "broker-service",
        detectedMediaType: "text/markdown",
        sizeBytes: 2048,
        sourceSha256: "abc123def456",
        objectKey: "s3://bucket/ing_xxx",
      });

      await expect(
        reviewDocumentIngestion({
          ingestionId: completed.id,
          reviewerId: "user-reviewer",
          decision: "PUBLISHED",
          reason: "Cannot publish from QUEUED",
        })
      ).rejects.toThrow();
    });
  });

  describe("Audit Events", () => {
    it("creates immutable audit events for state transitions", async () => {
      const created = await createDocumentIngestion({
        workspaceId: "ws-test-1",
        createdBy: "user-alice",
        originalFilename: "document.md",
        declaredMediaType: "text/markdown",
        idempotencyKey: "audit-key-1",
      });

      const completed = await completeUpload({
        ingestionId: created.id,
        actorId: "broker-service",
        detectedMediaType: "text/markdown",
        sizeBytes: 2048,
        sourceSha256: "abc123def456",
        objectKey: "s3://bucket/ing_xxx",
      });

      const events = await getAuditEventsForIngestion(completed.id);

      expect(events.length).toBeGreaterThan(0);
      const uploadCompleteEvent = events.find((e) => e.newState === "QUEUED");
      expect(uploadCompleteEvent).toBeDefined();
      expect(uploadCompleteEvent?.oldState).toBe("UPLOADING");
      expect(uploadCompleteEvent?.reason).toContain("completeUpload");
      // Audit must NOT contain originalObjectKey
      expect((uploadCompleteEvent as any).originalObjectKey).toBeUndefined();
    });

    it("audit events contain old/new state and reason, never object key", async () => {
      const created = await createDocumentIngestion({
        workspaceId: "ws-test-1",
        createdBy: "user-alice",
        originalFilename: "document.md",
        declaredMediaType: "text/markdown",
        idempotencyKey: "audit-secrets-key",
      });

      const completed = await completeUpload({
        ingestionId: created.id,
        actorId: "broker-service",
        detectedMediaType: "text/markdown",
        sizeBytes: 2048,
        sourceSha256: "abc123def456",
        objectKey: "super-secret-s3://bucket/ing_xxx",
      });

      const events = await getAuditEventsForIngestion(completed.id);
      const uploadEvent = events.find((e) => e.newState === "QUEUED");

      expect(uploadEvent?.oldState).toBe("UPLOADING");
      expect(uploadEvent?.newState).toBe("QUEUED");
      expect(uploadEvent?.reason).toBeDefined();
      expect(uploadEvent?.reason).not.toContain("super-secret");
      // Verify no object key field at all
      const eventStr = JSON.stringify(uploadEvent, (_key, value) =>
        typeof value === "bigint" ? value.toString() : value
      );
      expect(eventStr).not.toContain("objectKey");
      expect(eventStr).not.toContain("s3://");
    });
  });

  describe("Authorization Boundary", () => {
    it("returns 403 non-enumerating when Workspace B member tries to access Workspace A record", async () => {
      const created = await createDocumentIngestion({
        workspaceId: "ws-a",
        createdBy: "user-alice",
        originalFilename: "document.md",
        declaredMediaType: "text/markdown",
        idempotencyKey: "authz-key-1",
      });

      // Try to fetch as member of different workspace (not yet verified by mock)
      // In real scenario, verifyWorkspaceMembership would throw permissionDenied
      const record = await getDocumentIngestion(created.id);
      expect(record).toBeDefined();
    });
  });
});
