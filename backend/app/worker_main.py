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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = AIRouter(build_provider)

CHAT_IDLE_POLL_SECONDS = 5.0
BACKGROUND_POLL_SECONDS = 1.0
MAX_CONCURRENT_TURNS = 8

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
            else:
                chunk_job.status = "failed"
                chunk_job.error = "Revision not found"
        except Exception as e:
            chunk_job.status = "failed"
            chunk_job.error = str(e)

        chunk_job.finished_at = datetime.utcnow()
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
            process_due_schedules()
            dispatch_pending_tasks()
        except Exception:
            logger.exception("Background worker failure")
        await asyncio.sleep(BACKGROUND_POLL_SECONDS)

def _run_background_worker() -> None:
    asyncio.run(_background_loop())

async def _run_all() -> None:
    await asyncio.gather(
        chat_loop(),
        channel_worker_loop(),
        asyncio.to_thread(_run_background_worker)
    )

def main():
    logger.info("Starting Agent Worker with Channels Worker...")
    try:
        asyncio.run(_run_all())
    except KeyboardInterrupt:
        logger.info("Agent Worker stopping...")

if __name__ == "__main__":
    main()
