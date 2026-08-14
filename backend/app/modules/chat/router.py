from fastapi import APIRouter, Depends, HTTPException, Request, status, UploadFile, File, Form, Query
from sse_starlette.sse import EventSourceResponse
from starlette.concurrency import run_in_threadpool
import asyncio
import json
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, field_validator

from app.db.session import SessionLocal, get_db
from app.core.auth import get_current_workspace_member
from app.db.models import WorkspaceMember, ChatSession, ChatMessage, Brain, AIRun
from app.integrations.voice_client import VoiceClient
from app.modules.chat.chat_stream_bus import (
    notify_user_message_submitted,
    session_event_listener,
)
from app.modules.chat.model_registry import (
    DEFAULT_MODEL,
    DEFAULT_PROVIDER,
    is_known,
    is_provider_configured,
)

router = APIRouter()

TERMINAL_STATUSES = ("delivered", "error", "cancelled")

# Lưới an toàn khi lỡ mất NOTIFY, không phải nhịp poll: bình thường token về qua NOTIFY
# trong vài ms; im lặng quá ngần này giây thì mới đọc lại DB một lần cho chắc.
STREAM_IDLE_RESYNC_SECONDS = 10.0

def _get_brain_or_404(db: Session, brain_id: int, workspace_id: int) -> Brain:
    # Dùng chung cho mọi endpoint chat để tránh lặp lại lỗ hổng cross-tenant đã vá ở
    # vault.py: brain_id đến từ path, workspace_id chỉ chứng minh user là thành viên
    # CỦA workspace_id đó - phải verify brain thực sự thuộc workspace đó.
    brain = db.query(Brain).filter(Brain.id == brain_id, Brain.workspace_id == workspace_id).first()
    if not brain:
        raise HTTPException(status_code=404, detail="Brain not found for this workspace")
    return brain

def resolve_session_model(
    provider: Optional[str], model: Optional[str]
) -> tuple[str, str]:
    """Chốt provider/model cho một session mới; None nghĩa là client chưa chọn.

    Provider chưa có khoá bị từ chối NGAY ở đây. Trước đây chỉ kiểm tra ``is_known()``, nên
    một client gửi lên provider chưa cấu hình vẫn tạo được session, rồi mọi câu hỏi trong
    session đó đều trả về "Không thể tạo phản hồi AI lúc này." mà không nói vì sao.
    ``GET /ai/models`` chỉ liệt kê model đã có khoá, nên client đúng phiên bản không bao giờ
    chạm vào nhánh này.
    """
    provider = provider or DEFAULT_PROVIDER
    model = model or DEFAULT_MODEL
    if not is_known(provider, model):
        raise HTTPException(status_code=400, detail=f"Unknown provider/model: {provider}/{model}")
    if not is_provider_configured(provider):
        raise HTTPException(
            status_code=400,
            detail=f"Provider chưa được cấu hình API key: {provider}",
        )
    return provider, model


class ChatSessionCreate(BaseModel):
    title: Optional[str] = "New Chat"
    provider: Optional[str] = None
    model: Optional[str] = None

class ChatMessageCreate(BaseModel):
    role: str
    content: str
    client_message_id: str

    @field_validator("role")
    @classmethod
    def role_must_be_user(cls, value: str) -> str:
        if value != "user":
            raise ValueError("Client messages must have role 'user'")
        return value

    @field_validator("content")
    @classmethod
    def content_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Message content must not be blank")
        return value

def reconcile_delta(emitted: int, offset: int, chunk: str) -> tuple[str, str]:
    """Đối chiếu một mảnh delta với số ký tự đã đẩy cho client.

    Trả về ``("emit", text)`` để gửi tiếp, ``("skip", "")`` khi mảnh này đã nằm trọn
    trong phần đã gửi (snapshot chồng lấn notify, hoặc notify lặp), và ``("resync", "")``
    khi bị hụt mất mảnh ở giữa - lúc đó phải đọc lại DB chứ nối vào là sai nội dung.
    """
    if offset > emitted:
        return ("resync", "")
    tail = chunk[emitted - offset:]
    if not tail:
        return ("skip", "")
    return ("emit", tail)


def _serialize_message(message: ChatMessage) -> dict:
    return {
        "id": str(message.id),
        "role": message.role,
        "content": message.content,
        "status": message.status,
        "created_at": message.created_at.isoformat(),
    }


def _read_reply_snapshot(session_id: int, after_message_id: Optional[int]) -> Optional[dict]:
    """Đọc trạng thái hiện tại của bong bóng trả lời, trên MỘT Session dùng-rồi-bỏ.

    Phải là Session mới mỗi lần: identity map của SQLAlchemy trả lại đúng object đã nạp
    lần trước mà không ghi đè thuộc tính từ row mới, nên tái dùng Session trong vòng lặp
    stream sẽ đọc mãi content cũ - stream đứng im dù worker vẫn đang sinh token.
    """
    db = SessionLocal()
    try:
        query = db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id,
            ChatMessage.role == "assistant",
        )
        if after_message_id is not None:
            # Chỉ quan tâm câu trả lời cho ĐÚNG lượt vừa gửi. Không có mốc này thì lượt
            # thứ 2 trở đi sẽ vớ phải câu trả lời đã 'delivered' của lượt trước và đóng
            # stream ngay lập tức.
            anchor = db.query(ChatMessage.created_at).filter(
                ChatMessage.id == after_message_id
            ).scalar()
            if anchor is not None:
                query = query.filter(ChatMessage.created_at > anchor)
        else:
            query = query.filter(ChatMessage.status.notin_(TERMINAL_STATUSES))

        message = query.order_by(ChatMessage.created_at.desc()).first()
        return _serialize_message(message) if message else None
    finally:
        db.close()


def _read_message_by_id(message_id: str) -> Optional[dict]:
    db = SessionLocal()
    try:
        message = db.query(ChatMessage).filter(ChatMessage.id == int(message_id)).first()
        return _serialize_message(message) if message else None
    finally:
        db.close()


@router.get("/{brain_id}/sessions/{session_id}/stream")
async def stream_chat_session(
    brain_id: int,
    session_id: int,
    workspace_id: int,
    request: Request,
    after_message_id: Optional[int] = None,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    _get_brain_or_404(db, brain_id, workspace_id)
    session = db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.brain_id == brain_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    # Trả connection về pool ngay: dependency dùng yield chỉ được dọn sau khi response
    # kết thúc, mà response này sống suốt cả lượt trả lời.
    db.close()

    async def events():
        # Đăng ký listener TRƯỚC khi đọc snapshot: làm ngược lại thì mọi token sinh ra
        # trong khe hở giữa hai bước sẽ không ai nhận.
        async with session_event_listener(str(session_id)) as queue:
            snapshot = await run_in_threadpool(_read_reply_snapshot, session_id, after_message_id)

            target_id: Optional[str] = None
            emitted = 0

            if snapshot:
                target_id = snapshot["id"]
                emitted = len(snapshot["content"])
                yield {"event": "message", "data": json.dumps(snapshot)}
                if snapshot["status"] in TERMINAL_STATUSES:
                    yield {"event": "completed" if snapshot["status"] == "delivered" else "failed", "data": "{}"}
                    return

            while True:
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=STREAM_IDLE_RESYNC_SECONDS)
                except asyncio.TimeoutError:
                    if await request.is_disconnected():
                        return
                    fresh = (
                        await run_in_threadpool(_read_message_by_id, target_id)
                        if target_id
                        else await run_in_threadpool(_read_reply_snapshot, session_id, after_message_id)
                    )
                    if not fresh:
                        continue
                    target_id = fresh["id"]
                    if len(fresh["content"]) > emitted or fresh["status"] in TERMINAL_STATUSES:
                        emitted = len(fresh["content"])
                        yield {"event": "message", "data": json.dumps(fresh)}
                    if fresh["status"] in TERMINAL_STATUSES:
                        yield {"event": "completed" if fresh["status"] == "delivered" else "failed", "data": "{}"}
                        return
                    continue

                message_id = payload.get("message_id")
                if target_id is None:
                    target_id = message_id
                    emitted = 0
                    yield {
                        "event": "message",
                        "data": json.dumps({
                            "id": target_id,
                            "role": "assistant",
                            "content": "",
                            "status": "streaming",
                        }),
                    }
                elif message_id != target_id:
                    continue

                if payload.get("kind") == "delta":
                    action, chunk = reconcile_delta(
                        emitted, payload.get("offset", 0), payload.get("text", "")
                    )
                    if action == "skip":
                        continue
                    if action == "resync":
                        # Đọc lại DB thay vì nối vào chỗ sai. Nếu DB chưa kịp bắt kịp thì
                        # lần commit cuối của worker sẽ chốt lại.
                        fresh = await run_in_threadpool(_read_message_by_id, target_id)
                        if fresh and len(fresh["content"]) >= emitted:
                            emitted = len(fresh["content"])
                            yield {"event": "message", "data": json.dumps(fresh)}
                        continue
                    emitted += len(chunk)
                    yield {"event": "delta", "data": json.dumps({"id": target_id, "text": chunk})}

                elif payload.get("kind") == "status":
                    reply_status = payload.get("status")
                    if reply_status not in TERMINAL_STATUSES:
                        continue
                    # Trạng thái kết thúc: lấy bản DB làm chuẩn để client không giữ phần
                    # text lệch do mất notify giữa chừng.
                    fresh = await run_in_threadpool(_read_message_by_id, target_id)
                    if fresh:
                        yield {"event": "message", "data": json.dumps(fresh)}
                    yield {"event": "completed" if reply_status == "delivered" else "failed", "data": "{}"}
                    return

    return EventSourceResponse(events())

@router.get("/{brain_id}/sessions")
def list_chat_sessions(
    brain_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    _get_brain_or_404(db, brain_id, workspace_id)

    # Session one-shot là chuyện nội bộ của các nút "AI đề xuất ..." (chat/worker_prompt.py):
    # nó sống vài giây rồi bị xoá, lọt vào danh sách chat của người dùng chỉ là rác nhấp nháy.
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.brain_id == brain_id, ChatSession.purpose.is_(None))
        .order_by(ChatSession.last_message_at.desc().nullslast(), ChatSession.created_at.desc())
        .all()
    )
    
    return {
        "sessions": [
            {
                "id": str(s.id),
                "title": s.title,
                "provider": s.provider,
                "model": s.model,
                "last_message_at": s.last_message_at.isoformat() if s.last_message_at else None,
                "created_at": s.created_at.isoformat()
            } for s in sessions
        ]
    }

@router.post("/{brain_id}/sessions")
def create_chat_session(
    brain_id: int,
    workspace_id: int,
    session_data: ChatSessionCreate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    _get_brain_or_404(db, brain_id, workspace_id)

    provider, model = resolve_session_model(session_data.provider, session_data.model)

    new_session = ChatSession(
        brain_id=brain_id,
        # Lấy từ member đã xác thực, không nhận từ body: worker dùng giá trị này để chạy
        # tool theo phạm vi người dùng.
        user_id=member.user_id,
        title=session_data.title,
        provider=provider,
        model=model,
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)

    return {
        "id": str(new_session.id),
        "title": new_session.title,
        "provider": new_session.provider,
        "model": new_session.model,
        "created_at": new_session.created_at.isoformat()
    }

@router.delete("/{brain_id}/sessions/{session_id}")
def delete_chat_session(
    brain_id: int,
    session_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    _get_brain_or_404(db, brain_id, workspace_id)

    session = db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.brain_id == brain_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    db.query(AIRun).filter(AIRun.chat_session_id == session_id).delete(synchronize_session=False)
    db.query(ChatMessage).filter(ChatMessage.session_id == session_id).delete(synchronize_session=False)
    db.delete(session)
    db.commit()

    return {"status": "ok"}


@router.get("/{brain_id}/sessions/{session_id}/messages")
def list_chat_messages(
    brain_id: int,
    session_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    _get_brain_or_404(db, brain_id, workspace_id)

    session = db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.brain_id == brain_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at.asc()).all()
    
    return {
        "messages": [
            {
                "id": str(m.id),
                "role": m.role,
                "content": m.content,
                "status": m.status,
                "client_message_id": m.client_message_id,
                "created_at": m.created_at.isoformat()
            } for m in messages
        ]
    }

@router.post("/{brain_id}/sessions/{session_id}/messages")
def send_chat_message(
    brain_id: int,
    session_id: int,
    workspace_id: int,
    message_data: ChatMessageCreate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    _get_brain_or_404(db, brain_id, workspace_id)

    session = db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.brain_id == brain_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    new_msg = ChatMessage(
        session_id=session_id,
        role=message_data.role,
        content=message_data.content,
        client_message_id=message_data.client_message_id,
        status="sent"
    )
    db.add(new_msg)
    
    # Check idempotency via unique constraint
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        # Message already exists, return existing
        existing_msg = db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id,
            ChatMessage.client_message_id == message_data.client_message_id
        ).first()
        if existing_msg:
            return {
                "id": str(existing_msg.id),
                "role": existing_msg.role,
                "content": existing_msg.content,
                "status": existing_msg.status,
                "client_message_id": existing_msg.client_message_id,
                "created_at": existing_msg.created_at.isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Database integrity error")
            
    db.refresh(new_msg)

    # Update session last_message_at
    session.last_message_at = datetime.utcnow()
    db.commit()

    # Đánh thức worker ngay thay vì để nó phát hiện ở nhịp poll kế tiếp.
    notify_user_message_submitted(db, session_id)

    return {
        "id": str(new_msg.id),
        "role": new_msg.role,
        "content": new_msg.content,
        "status": new_msg.status,
        "client_message_id": new_msg.client_message_id,
        "created_at": new_msg.created_at.isoformat()
    }

@router.post("/{brain_id}/sessions/{session_id}/cancel")
def cancel_chat_session(
    brain_id: int,
    session_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    _get_brain_or_404(db, brain_id, workspace_id)

    session = db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.brain_id == brain_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Worker (process khác) tự phát hiện cờ này giữa các event và dừng gọi provider -
    # xem _is_cancelled() trong chat_execution_service.py.
    assistant = db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id,
        ChatMessage.role == "assistant",
        ChatMessage.status.in_(["streaming", "sent"]),
    ).order_by(ChatMessage.created_at.desc()).first()
    if not assistant:
        raise HTTPException(status_code=409, detail="No in-progress reply to cancel")

    assistant.status = "cancelled"
    db.commit()

    return {"id": str(assistant.id), "status": assistant.status}


@router.post("/transcribe-voice")
async def transcribe_voice(
    workspace_id: int = Query(...),
    file: UploadFile = File(...),
    language: Optional[str] = Form("vi"),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden to this workspace")

    audio_bytes = await file.read()
    client = VoiceClient()
    try:
        transcript = await client.transcribe(
            audio_bytes=audio_bytes,
            filename=file.filename or "audio.m4a",
            language=language or "vi",
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return {"transcript": transcript}

