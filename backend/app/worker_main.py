import asyncio
import logging
from app.db.session import SessionLocal
from app.modules.chat.ai_router import AIRouter
from app.modules.chat.chat_execution_service import claim_pending_messages, run_turn
from app.modules.chat.chat_stream_bus import ChatJobListener, PostgresChatEventPublisher
from app.modules.chat.providers import build_provider
from app.db.models import ChunkingJob, VaultRevision, DocumentChunk
from app.integrations.s3_client import get_object
from sqlalchemy import text
from datetime import datetime
from app.modules.tasks.scheduler_service import process_due_schedules
from app.modules.tasks.task_dispatcher import dispatch_pending_tasks
from app.services.channels.channel_worker import channel_worker_loop
from app.modules.integrations.zalo_qr_service import process_one_queued_qr_session
from app.core.worker_health import HEARTBEAT_INTERVAL_SECONDS, record_worker_heartbeat
from app.agents.execution.manager import execution_provider_manager
from app.agents.execution.service import run_execution_job
from app.agents.execution.models import ExecutionJob

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = AIRouter(build_provider)

CHAT_IDLE_POLL_SECONDS = 5.0
BACKGROUND_POLL_SECONDS = 1.0
EXECUTION_POLL_SECONDS = 2.0
MAX_CONCURRENT_TURNS = 8
MAX_CHUNKING_RETRIES = 3
MAX_CONCURRENT_EXECUTION_JOBS = 2
MAX_EXECUTION_RETRIES = 2

async def chat_loop() -> None:
    publisher = PostgresChatEventPublisher()
    listener = ChatJobListener()
    running: set[asyncio.Task] = set()

    while True:
        if len(running) >= MAX_CONCURRENT_TURNS:
            await asyncio.wait(running, return_when=asyncio.FIRST_COMPLETED)
            continue

        db = SessionLocal()
        try:
            claimed = claim_pending_messages(db, MAX_CONCURRENT_TURNS - len(running))
        except Exception:
            logger.exception("Chat worker failure")
            db.rollback()
            claimed = []
        finally:
            db.close()

        for message_id in claimed:
            task = asyncio.create_task(run_turn(SessionLocal, router, publisher, message_id))
            running.add(task)
            task.add_done_callback(running.discard)

        if claimed:
            continue

        try:
            await listener.wait(timeout=CHAT_IDLE_POLL_SECONDS)
        except Exception:
            logger.warning("Mất kênh đánh thức chat, tạm rơi về nhịp poll", exc_info=True)
            await listener.close()
            await asyncio.sleep(BACKGROUND_POLL_SECONDS)

async def process_chunking_jobs():
    db = SessionLocal()
    try:
        job_id = db.execute(
            text("SELECT id FROM chunking_jobs WHERE status = 'queued' FOR UPDATE SKIP LOCKED LIMIT 1")
        ).scalar()
        if not job_id:
            return

        chunk_job = db.query(ChunkingJob).filter(ChunkingJob.id == job_id).first()
        chunk_job.status = "processing"
        chunk_job.started_at = datetime.utcnow()
        db.commit()

        try:
            rev = db.query(VaultRevision).filter(VaultRevision.id == chunk_job.revision_id).first()
            if rev:
                content = get_object(rev.object_key).decode('utf-8')

                from app.modules.vault.chunking_service import chunk_markdown
                from app.modules.vault.embedding_service import generate_embeddings

                text_chunks = chunk_markdown(content)
                embeddings = await generate_embeddings(text_chunks)

                for i, text_chunk in enumerate(text_chunks):
                    dc = DocumentChunk(
                        revision_id=rev.id,
                        ordinal=i,
                        text=text_chunk,
                        embedding=embeddings[i]
                    )
                    db.add(dc)

                db.flush()
                for dc in db.query(DocumentChunk).filter(DocumentChunk.revision_id == rev.id).all():
                    db.execute(text("UPDATE document_chunks SET fts = to_tsvector('english', :text) WHERE id = :id"), {"text": dc.text, "id": dc.id})

                chunk_job.status = "completed"
                chunk_job.finished_at = datetime.utcnow()
            else:
                chunk_job.status = "failed"
                chunk_job.error = "Revision not found"
                chunk_job.finished_at = datetime.utcnow()
        except Exception as e:
            # Rollback trước: nếu lỗi xảy ra sau khi đã flush một phần DocumentChunk
            # (vd. fail giữa vòng lặp fts UPDATE), phần đó vẫn nằm trong transaction
            # chưa commit - không rollback thì lần retry sau sẽ chunk lại từ đầu và
            # tạo chunk trùng lặp trên cùng revision.
            db.rollback()
            chunk_job = db.query(ChunkingJob).filter(ChunkingJob.id == job_id).first()

            # Lỗi tạm thời (timeout embedding, S3 hiccup) không nên fail job vĩnh viễn
            # ngay lần đầu - trả lại 'queued' để nhịp poll sau tự nhặt lại, tới khi vượt
            # MAX_CHUNKING_RETRIES mới coi là dead-letter (status='failed' dừng hẳn).
            chunk_job.retry_count += 1
            chunk_job.error = str(e)
            if chunk_job.retry_count < MAX_CHUNKING_RETRIES:
                chunk_job.status = "queued"
                chunk_job.started_at = None
            else:
                chunk_job.status = "failed"
                chunk_job.finished_at = datetime.utcnow()
                logger.error(
                    "Chunking job %s fail vĩnh viễn sau %d lần retry: %s",
                    chunk_job.id, chunk_job.retry_count, e,
                )

        db.commit()
    except Exception:
        logger.exception("Chunking worker failure")
        db.rollback()
    finally:
        db.close()

async def _background_loop() -> None:
    while True:
        try:
            await process_chunking_jobs()
            await asyncio.to_thread(process_one_queued_qr_session)
            process_due_schedules()
            dispatch_pending_tasks()
        except Exception:
            logger.exception("Background worker failure")
        await asyncio.sleep(BACKGROUND_POLL_SECONDS)


async def heartbeat_loop() -> None:
    while True:
        db = SessionLocal()
        try:
            record_worker_heartbeat(db)
        except Exception:
            logger.exception("Worker heartbeat failure")
            db.rollback()
        finally:
            db.close()
        await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)

async def process_one_execution_job(job_id: int) -> None:
    db = SessionLocal()
    try:
        await run_execution_job(db, job_id)
    except Exception as e:
        logger.exception(f"Execution job {job_id} error: {e}")
        try:
            job = db.query(ExecutionJob).filter(ExecutionJob.id == job_id).first()
            if job:
                job.retry_count += 1
                job.error_message = str(e)
                if job.retry_count < MAX_EXECUTION_RETRIES:
                    job.status = "queued"
                    job.started_at = None
                else:
                    job.status = "failed"
                    job.completed_at = datetime.utcnow()
                db.commit()
        except Exception:
            db.rollback()
    finally:
        db.close()


async def execution_loop() -> None:
    """Worker loop claiming and executing sandbox execution jobs."""
    await execution_provider_manager.start()
    running: set[asyncio.Task] = set()

    while True:
        if len(running) >= MAX_CONCURRENT_EXECUTION_JOBS:
            await asyncio.wait(running, return_when=asyncio.FIRST_COMPLETED)
            continue

        db = SessionLocal()
        claimed_id = None
        try:
            claimed_id = db.execute(
                text("SELECT id FROM execution_jobs WHERE status = 'queued' FOR UPDATE SKIP LOCKED LIMIT 1")
            ).scalar()
            if claimed_id:
                job = db.query(ExecutionJob).filter(ExecutionJob.id == claimed_id).first()
                if job:
                    job.status = "preparing"
                    job.started_at = datetime.utcnow()
                    db.commit()
        except Exception:
            logger.exception("Execution worker claim failure")
            db.rollback()
            claimed_id = None
        finally:
            db.close()

        if claimed_id:
            task = asyncio.create_task(process_one_execution_job(claimed_id))
            running.add(task)
            task.add_done_callback(running.discard)
            continue

        await asyncio.sleep(EXECUTION_POLL_SECONDS)


async def execution_cleanup_loop() -> None:
    """Periodic cleanup loop destroying orphaned or expired sandboxes every 600s (§30)."""
    while True:
        try:
            db = SessionLocal()
            try:
                now = datetime.utcnow()
                # Find expired running jobs
                expired_jobs = (
                    db.query(ExecutionJob)
                    .filter(
                        ExecutionJob.status.in_(["preparing", "running", "collecting"]),
                        ExecutionJob.expires_at.is_not(None),
                        ExecutionJob.expires_at < now,
                    )
                    .all()
                )
                for ej in expired_jobs:
                    ej.status = "failed"
                    ej.error_code = "EXEC_SANDBOX_TIMEOUT"
                    ej.error_message = "Execution job expired"
                    ej.completed_at = now
                    if ej.sandbox_id:
                        try:
                            provider = execution_provider_manager.get(ej.provider)
                            await provider.terminate(ej.sandbox_id)
                            ej.destroyed_at = now
                        except Exception:
                            pass
                db.commit()
            except Exception:
                logger.exception("Execution cleanup failure")
                db.rollback()
            finally:
                db.close()
        except Exception:
            pass

        await asyncio.sleep(600)


def _run_background_worker() -> None:
    asyncio.run(_background_loop())

async def _run_all() -> None:
    await asyncio.gather(
        chat_loop(),
        channel_worker_loop(),
        heartbeat_loop(),
        execution_loop(),
        execution_cleanup_loop(),
        asyncio.to_thread(_run_background_worker),
    )

def main():
    logger.info("Starting Agent Worker with Channels Worker and Execution Runtime...")
    try:
        asyncio.run(_run_all())
    except KeyboardInterrupt:
        logger.info("Agent Worker stopping...")

if __name__ == "__main__":
    main()
