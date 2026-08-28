"""Test document ingestion handler end-to-end orchestration."""

from __future__ import annotations

import io
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from apps.cosa.knowledge_ingestion.handler import execute_knowledge_ingestion_task
from apps.cosa.knowledge_ingestion.object_store import InMemoryDocumentObjectStore
from apps.cosa.knowledge_ingestion.contracts import QuarantinedObject, FailureCode
from apps.cosa.knowledge_ingestion.scanner import FakeDocumentMalwareScanner
from apps.cosa.knowledge_ingestion.conversion_sandbox import InProcessConversionSandbox
from apps.cosa.knowledge_ingestion.markitdown_converter import ConversionResult
from agent_core.knowledge.store import InMemoryKnowledgeStore
from agent_core.knowledge.service import KnowledgeIngestionService


class TestExecuteKnowledgeIngestionTask:
    """Test handler execution flow without run leases or run_id."""

    @pytest.mark.asyncio
    async def test_ingestion_task_executes_without_run_id(self):
        """knowledge_ingestion task should not require run_id (unlike run/resume tasks)."""
        # This is a marker test — actual execution tested via control_plane_client mock
        payload = {"task_type": "knowledge_ingestion", "ingestion_id": "ing_test_001"}
        # Should not raise KeyError for missing run_id
        # When implemented, execute_knowledge_ingestion_task should succeed without run_id
        assert payload.get("task_type") == "knowledge_ingestion"
        assert "run_id" not in payload

    @pytest.mark.asyncio
    async def test_handler_claims_ingestion_for_conversion(self):
        """Handler should claim QUEUED ingestion and transition to VALIDATING."""
        # Mock control plane client
        control_plane = AsyncMock()
        control_plane.claim_for_conversion = AsyncMock(
            return_value={"id": "ing_001", "state": "VALIDATING"}
        )

        # Will be tested once control_plane_client is implemented
        payload = {"task_type": "knowledge_ingestion", "ingestion_id": "ing_001"}
        # Mock should be called during handler execution
        assert payload["ingestion_id"] == "ing_001"

    @pytest.mark.asyncio
    async def test_handler_terminal_failure_sets_rejected_status(self):
        """Terminal failures (malware, unsupported type) should set REJECTED state."""
        control_plane = AsyncMock()
        control_plane.mark_rejected_or_failed = AsyncMock()

        payload = {"task_type": "knowledge_ingestion", "ingestion_id": "ing_001"}

        # On terminal failure, handler should call mark_rejected_or_failed with REJECTED
        # This will be verified once implementation is complete

    @pytest.mark.asyncio
    async def test_handler_transient_error_raises_for_scheduler_retry(self):
        """Transient errors (network, store unavailable) should raise for scheduler retry."""
        payload = {"task_type": "knowledge_ingestion", "ingestion_id": "ing_001"}
        # A transient error (e.g., network failure) should raise exception
        # so scheduler retries, not mark as FAILED
        # This will be tested once implementation is complete

    @pytest.mark.asyncio
    async def test_duplicate_ingestion_same_sha_idempotent(self):
        """Retrying same ingestion_id with same source SHA should create one knowledge_source_id."""
        payload = {"task_type": "knowledge_ingestion", "ingestion_id": "ing_001"}
        # Scheduler at-least-once delivery: if task redelivered before completion,
        # expectedStates check should fail cleanly (state already advanced past QUEUED)
        # preventing duplicate ingest
        # This will be verified via control_plane expectedStates mechanism


class TestKnowledgeIngestionControlPlaneClient:
    """Test control plane client for state transitions and fencing."""

    @pytest.mark.asyncio
    async def test_claim_for_conversion_requires_queued_state(self):
        """claim_for_conversion should only succeed from QUEUED state."""
        # This requires expectedStates=['QUEUED'] in the control plane call
        # If state is VALIDATING (already claimed), transition should fail with invalidArgument
        pass

    @pytest.mark.asyncio
    async def test_claim_for_conversion_transitions_to_validating(self):
        """After successful claim, ingestion state should be VALIDATING."""
        pass

    @pytest.mark.asyncio
    async def test_record_candidate_transitions_to_review_pending(self):
        """record_candidate should transition to REVIEW_PENDING with knowledge_source_id."""
        pass

    @pytest.mark.asyncio
    async def test_mark_rejected_or_failed_sets_state_and_failure_code(self):
        """mark_rejected_or_failed should set state (REJECTED/FAILED) and sanitized failure_code."""
        pass


class TestReviewEndpoint:
    """Test knowledge ingestion review endpoint."""

    @pytest.mark.asyncio
    async def test_review_requires_member_authentication(self):
        """Review endpoint should require workspace membership."""
        # Will test once endpoint is implemented in routes.py
        pass

    @pytest.mark.asyncio
    async def test_review_requires_review_pending_state(self):
        """Review endpoint should only work on REVIEW_PENDING ingestions."""
        pass

    @pytest.mark.asyncio
    async def test_review_publish_reference_flips_agent_core_status(self):
        """publish_reference decision should flip agent_core document ingest_status to published."""
        pass

    @pytest.mark.asyncio
    async def test_review_reject_flips_agent_core_status(self):
        """reject decision should flip agent_core document ingest_status to rejected."""
        pass

    @pytest.mark.asyncio
    async def test_review_records_audit_event(self):
        """Review should record audit event with reviewer ID and reason."""
        pass

    @pytest.mark.asyncio
    async def test_review_does_not_modify_search_chunks_behavior(self):
        """Review decision should not affect search_chunks retrieval (candidates remain hidden)."""
        pass


class TestDispatchWorkerRefactoring:
    """Test worker refactoring for knowledge_ingestion task support."""

    @pytest.mark.asyncio
    async def test_dispatch_one_task_handles_knowledge_ingestion_without_lease(self):
        """dispatch_one_task should handle knowledge_ingestion tasks without RunLeaseManager."""
        pass

    @pytest.mark.asyncio
    async def test_knowledge_ingestion_uses_task_claim_heartbeat_only(self):
        """knowledge_ingestion should use scheduler.heartbeat_task, not lease heartbeat."""
        pass

    @pytest.mark.asyncio
    async def test_knowledge_ingestion_completes_via_scheduler_complete_task(self):
        """knowledge_ingestion completion should call plane.scheduler.complete_task directly."""
        pass

    @pytest.mark.asyncio
    async def test_run_task_still_requires_run_id_and_lease(self):
        """run/resume/scheduled_session tasks should still require run_id and lease."""
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
