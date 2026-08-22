import logging

from sqlalchemy.orm import Session

from workforce.memory.redact import redact_text
from workforce.memory.service import get_gateway
from integrations.devices.models import DeveloperJob

logger = logging.getLogger("mcosa.agent_memory.claude_code_capture")

_TERMINAL_STATUSES = {"SUCCEEDED", "FAILED"}


async def capture_developer_job_completion(db: Session, workspace_id: int, job: DeveloperJob) -> None:
    """MEM-1 Claude Code PoC (spec §148-149) - capture on DeveloperJob
    completion, the natural point where "tool output / test logs / errors /
    decisions" already exists (worktree_path/diff_summary/test_results -
    `backend/app/modules/devices/models.py`).

    Only fires for terminal states - a job still QUEUED/RUNNING has nothing
    meaningful to capture yet. Never raises: a capture failure must not
    break the job-completion response to the calling device (spec §210.16 -
    "do not block WorkItem execution on memory compaction").
    """
    if job.status not in _TERMINAL_STATUSES:
        return

    event = {
        "workspace_id": workspace_id,
        "job_id": str(job.id),
        "title": job.title,
        "status": job.status,
        "diff_summary": redact_text(job.diff_summary) if job.diff_summary else None,
        # test_results is structured (dict), not free text - not run through
        # redact_text. A CI test-results payload embedding a raw secret in an
        # error message is a known gap, not yet handled.
        "test_results": job.test_results,
        "worktree_path": job.worktree_path,
    }

    try:
        gateway = get_gateway(db, workspace_id)
        await gateway.capture(event)
    except Exception:  # noqa: BLE001 - capture must never break the caller
        logger.exception("agent_memory capture failed for developer_job %s", job.id)
