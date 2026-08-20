"""
COSA Operational Trajectory Builder
Biên dịch chuỗi sự kiện AgentEvent thô thành Narrative Timeline cho Hologram Hub UI (Structure.md Mục 24).
"""
from typing import List, Optional
from agent_runtime.events.base import AgentEvent, EventType
from agent_runtime.trajectory.models import TrajectoryStep, TrajectoryStepType, TrajectoryTimeline


class TrajectoryBuilder:
    """Bộ xử lý chuyển đổi AgentEvent Stream -> Human Narrative"""

    @staticmethod
    def build_timeline(
        session_id: str, 
        profile_id: str, 
        events: List[AgentEvent],
        status: str = "active"
    ) -> TrajectoryTimeline:
        steps: List[TrajectoryStep] = []
        total_tools = 0
        total_duration_ms = 0
        artifacts_count = 0
        created_at = events[0].timestamp if events else ""

        for event in events:
            step = TrajectoryBuilder._event_to_step(event)
            if step:
                steps.append(step)

            if event.type == EventType.TOOL_COMPLETED:
                total_tools += 1
                total_duration_ms += event.metadata.get("duration_ms", 0)
            elif event.type == EventType.ARTIFACT_CREATED:
                artifacts_count += 1
            elif event.type == EventType.SESSION_COMPLETED:
                status = "completed"
            elif event.type == EventType.SESSION_FAILED:
                status = "failed"

        return TrajectoryTimeline(
            session_id=session_id,
            profile_id=profile_id,
            status=status,
            created_at=created_at,
            steps=steps,
            summary_metrics={
                "total_events": len(events),
                "total_tools_executed": total_tools,
                "total_duration_ms": total_duration_ms,
                "artifacts_count": artifacts_count,
            }
        )

    @staticmethod
    def _event_to_step(event: AgentEvent) -> Optional[TrajectoryStep]:
        payload = event.payload or {}
        metadata = event.metadata or {}

        if event.type == EventType.USER_MESSAGE:
            return TrajectoryStep(
                step_id=event.id,
                timestamp=event.timestamp,
                step_type=TrajectoryStepType.REQUEST_RECEIVED,
                title="Nhận yêu cầu từ người dùng",
                description=str(payload.get("message", ""))[:300],
                actor_id=event.actor.get("id", "user")
            )

        elif event.type == EventType.INTENT_DETECTED:
            intent_name = payload.get("intent", "general")
            return TrajectoryStep(
                step_id=event.id,
                timestamp=event.timestamp,
                step_type=TrajectoryStepType.INTENT_CLASSIFIED,
                title=f"Xác định ý định: {intent_name}",
                description=payload.get("description"),
                badge=payload.get("risk_level", "LOW")
            )

        elif event.type == EventType.CONTEXT_LOADED:
            scopes = payload.get("scopes", [])
            return TrajectoryStep(
                step_id=event.id,
                timestamp=event.timestamp,
                step_type=TrajectoryStepType.CONTEXT_LOADED,
                title=f"Nạp ngữ cảnh: {', '.join(scopes) if scopes else 'None'}",
                description=f"Ước tính tokens: {metadata.get('estimated_tokens', 0)}"
            )

        elif event.type == EventType.SKILL_LOADED:
            skill_id = payload.get("skill_id", "unknown_skill")
            return TrajectoryStep(
                step_id=event.id,
                timestamp=event.timestamp,
                step_type=TrajectoryStepType.SKILL_APPLIED,
                title=f"Kích hoạt kỹ năng: {skill_id}",
                description=payload.get("description")
            )

        elif event.type == EventType.TOOL_COMPLETED:
            tool_id = payload.get("tool_id", "unknown_tool")
            return TrajectoryStep(
                step_id=event.id,
                timestamp=event.timestamp,
                step_type=TrajectoryStepType.TOOL_EXECUTED,
                title=f"Thực thi công cụ: {tool_id}",
                tool_id=tool_id,
                duration_ms=metadata.get("duration_ms", 0),
                presenter_payload=payload.get("presenter_payload") or payload.get("data"),
                error=payload.get("error")
            )

        elif event.type == EventType.APPROVAL_REQUESTED:
            return TrajectoryStep(
                step_id=event.id,
                timestamp=event.timestamp,
                step_type=TrajectoryStepType.APPROVAL_PENDING,
                title=f"Yêu cầu phê duyệt quyền {payload.get('risk_level', 'HIGH')}",
                description=payload.get("action_summary", "Chờ Founder xác nhận"),
                badge=payload.get("risk_level", "HIGH"),
                presenter_payload=payload.get("action_payload")
            )

        elif event.type == EventType.APPROVAL_GRANTED:
            return TrajectoryStep(
                step_id=event.id,
                timestamp=event.timestamp,
                step_type=TrajectoryStepType.APPROVAL_RESOLVED,
                title="Tác vụ đã được phê duyệt",
                badge="APPROVED"
            )

        elif event.type == EventType.ARTIFACT_CREATED:
            return TrajectoryStep(
                step_id=event.id,
                timestamp=event.timestamp,
                step_type=TrajectoryStepType.ARTIFACT_CREATED,
                title=f"Tạo sản phẩm: {payload.get('artifact_name', 'Artifact')}",
                description=payload.get("artifact_path") or payload.get("summary")
            )

        elif event.type == EventType.ASSISTANT_MESSAGE:
            return TrajectoryStep(
                step_id=event.id,
                timestamp=event.timestamp,
                step_type=TrajectoryStepType.ASSISTANT_RESPONSE,
                title="Phản hồi từ Agent",
                description=str(payload.get("content", ""))[:300]
            )

        elif event.type == EventType.SESSION_COMPLETED:
            return TrajectoryStep(
                step_id=event.id,
                timestamp=event.timestamp,
                step_type=TrajectoryStepType.SESSION_COMPLETED,
                title="Phiên làm việc hoàn thành",
                badge="COMPLETED"
            )

        elif event.type == EventType.SESSION_FAILED:
            return TrajectoryStep(
                step_id=event.id,
                timestamp=event.timestamp,
                step_type=TrajectoryStepType.SESSION_FAILED,
                title="Phiên làm việc thất bại",
                badge="FAILED",
                error=payload.get("error")
            )

        return None
