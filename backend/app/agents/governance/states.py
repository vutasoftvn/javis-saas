"""Máy trạng thái và quy tắc chuyển đổi trạng thái (State Machine & Transitions) cho Agent Runs, Plans và Steps trong COSA OS.

Tài liệu hóa và chuẩn hóa toàn bộ vòng đời thực thi của Agent, Kế hoạch và các Bước thực thi bằng tiếng Việt.
"""

from enum import Enum
from typing import Dict, Optional, Set, Union


class AgentRunStatus(str, Enum):
    """Trạng thái vòng đời thực thi của Agent Run."""
    CREATED = "created"                     # Khởi tạo
    PLANNING = "planning"                   # Đang lập kế hoạch
    READY = "ready"                         # Sẵn sàng thực thi
    RUNNING = "running"                     # Đang thực thi
    WAITING_TOOL = "waiting_tool"           # Đang chờ kết quả công cụ / sandbox
    WAITING_APPROVAL = "waiting_approval"   # Đang chờ Founder / con người phê duyệt
    EVALUATING = "evaluating"               # Đang đánh giá kết quả
    RETRYING = "retrying"                   # Đang thử lại sau lỗi tạm thời
    FALLBACK = "fallback"                   # Đang chuyển sang chiến lược dự phòng
    COMPLETED = "completed"                 # Hoàn thành thành công
    PARTIAL = "partial"                     # Hoàn thành một phần
    FAILED = "failed"                       # Thất bại (có thể thử lại)
    FAILED_FINAL = "failed_final"           # Thất bại vĩnh viễn (dừng hoàn toàn)
    CANCELLED = "cancelled"                 # Đã hủy bỏ
    SKIPPED = "skipped"                     # Đã bỏ qua


class AgentPlanStatus(str, Enum):
    """Trạng thái vòng đời của Kế hoạch thực thi (Agent Plan)."""
    DRAFT = "draft"                         # Bản nháp
    PLANNING = "planning"                   # Đang phân rã mục tiêu
    READY = "ready"                         # Đã sẵn sàng
    APPROVED = "approved"                   # Đã được duyệt
    IN_PROGRESS = "in_progress"             # Đang tiến hành
    RUNNING = "running"                     # Đang chạy
    WAITING_APPROVAL = "waiting_approval"   # Chờ phê duyệt bước rủi ro cao
    EVALUATING = "evaluating"               # Đang đánh giá kết quả
    COMPLETED = "completed"                 # Hoàn thành toàn bộ kế hoạch
    FAILED = "failed"                       # Thất bại
    FAILED_FINAL = "failed_final"           # Thất bại vĩnh viễn
    CANCELLED = "cancelled"                 # Đã hủy


class AgentPlanStepStatus(str, Enum):
    """Trạng thái của từng Bước thực thi (Plan Step)."""
    PENDING = "pending"                     # Đang chờ đến lượt
    CREATED = "created"                     # Đã tạo
    READY = "ready"                         # Sẵn sàng chạy
    RUNNING = "running"                     # Đang thực thi
    WAITING_TOOL = "waiting_tool"           # Đang chờ kết quả tool / webhook
    WAITING_APPROVAL = "waiting_approval"   # Đang chờ duyệt (L3A / L5)
    RETRYING = "retrying"                   # Đang tự động thử lại
    FALLBACK = "fallback"                   # Đang chạy handler dự phòng
    COMPLETED = "completed"                 # Bước thực thi hoàn tất thành công
    FAILED = "failed"                       # Thất bại
    FAILED_FINAL = "failed_final"           # Thất bại dứt điểm
    CANCELLED = "cancelled"                 # Bị hủy
    SKIPPED = "skipped"                     # Bị bỏ qua


# Bảng nhãn hiển thị tiếng Việt chuẩn hóa cho giao diện và báo cáo
RUN_STATUS_LABELS_VI: Dict[str, str] = {
    AgentRunStatus.CREATED.value: "Đã khởi tạo",
    AgentRunStatus.PLANNING.value: "Đang lập kế hoạch",
    AgentRunStatus.READY.value: "Sẵn sàng",
    AgentRunStatus.RUNNING.value: "Đang thực thi",
    AgentRunStatus.WAITING_TOOL.value: "Đang chờ công cụ",
    AgentRunStatus.WAITING_APPROVAL.value: "Chờ phê duyệt",
    AgentRunStatus.EVALUATING.value: "Đang đánh giá",
    AgentRunStatus.RETRYING.value: "Đang thử lại",
    AgentRunStatus.FALLBACK.value: "Đang chạy dự phòng",
    AgentRunStatus.COMPLETED.value: "Hoàn thành",
    AgentRunStatus.PARTIAL.value: "Hoàn thành một phần",
    AgentRunStatus.FAILED.value: "Thất bại",
    AgentRunStatus.FAILED_FINAL.value: "Thất bại vĩnh viễn",
    AgentRunStatus.CANCELLED.value: "Đã hủy bỏ",
    AgentRunStatus.SKIPPED.value: "Đã bỏ qua",
}

PLAN_STATUS_LABELS_VI: Dict[str, str] = {
    AgentPlanStatus.DRAFT.value: "Bản nháp",
    AgentPlanStatus.PLANNING.value: "Đang lập kế hoạch",
    AgentPlanStatus.READY.value: "Sẵn sàng",
    AgentPlanStatus.APPROVED.value: "Đã duyệt",
    AgentPlanStatus.IN_PROGRESS.value: "Đang tiến hành",
    AgentPlanStatus.RUNNING.value: "Đang thực thi",
    AgentPlanStatus.WAITING_APPROVAL.value: "Chờ phê duyệt",
    AgentPlanStatus.EVALUATING.value: "Đang đánh giá",
    AgentPlanStatus.COMPLETED.value: "Hoàn thành",
    AgentPlanStatus.FAILED.value: "Thất bại",
    AgentPlanStatus.FAILED_FINAL.value: "Thất bại vĩnh viễn",
    AgentPlanStatus.CANCELLED.value: "Đã hủy",
}

STEP_STATUS_LABELS_VI: Dict[str, str] = {
    AgentPlanStepStatus.PENDING.value: "Chờ thực hiện",
    AgentPlanStepStatus.CREATED.value: "Đã tạo",
    AgentPlanStepStatus.READY.value: "Sẵn sàng",
    AgentPlanStepStatus.RUNNING.value: "Đang chạy",
    AgentPlanStepStatus.WAITING_TOOL.value: "Chờ công cụ",
    AgentPlanStepStatus.WAITING_APPROVAL.value: "Chờ duyệt",
    AgentPlanStepStatus.RETRYING.value: "Đang thử lại",
    AgentPlanStepStatus.FALLBACK.value: "Chạy dự phòng",
    AgentPlanStepStatus.COMPLETED.value: "Hoàn thành",
    AgentPlanStepStatus.FAILED.value: "Thất bại",
    AgentPlanStepStatus.FAILED_FINAL.value: "Thất bại dứt điểm",
    AgentPlanStepStatus.CANCELLED.value: "Đã hủy",
    AgentPlanStepStatus.SKIPPED.value: "Đã bỏ qua",
}


# Ma trận các bước chuyển đổi hợp lệ cho AgentRun
RUN_ALLOWED_TRANSITIONS: Dict[str, Set[str]] = {
    AgentRunStatus.CREATED.value: {
        AgentRunStatus.CREATED.value,
        AgentRunStatus.PLANNING.value,
        AgentRunStatus.READY.value,
        AgentRunStatus.RUNNING.value,
        AgentRunStatus.CANCELLED.value,
    },
    AgentRunStatus.PLANNING.value: {
        AgentRunStatus.PLANNING.value,
        AgentRunStatus.READY.value,
        AgentRunStatus.RUNNING.value,
        AgentRunStatus.FAILED.value,
        AgentRunStatus.CANCELLED.value,
    },
    AgentRunStatus.READY.value: {
        AgentRunStatus.READY.value,
        AgentRunStatus.RUNNING.value,
        AgentRunStatus.WAITING_APPROVAL.value,
        AgentRunStatus.CANCELLED.value,
    },
    AgentRunStatus.RUNNING.value: {
        AgentRunStatus.RUNNING.value,
        AgentRunStatus.WAITING_TOOL.value,
        AgentRunStatus.WAITING_APPROVAL.value,
        AgentRunStatus.EVALUATING.value,
        AgentRunStatus.RETRYING.value,
        AgentRunStatus.FALLBACK.value,
        AgentRunStatus.COMPLETED.value,
        AgentRunStatus.PARTIAL.value,
        AgentRunStatus.FAILED.value,
        AgentRunStatus.FAILED_FINAL.value,
        AgentRunStatus.CANCELLED.value,
    },
    AgentRunStatus.WAITING_TOOL.value: {
        AgentRunStatus.WAITING_TOOL.value,
        AgentRunStatus.RUNNING.value,
        AgentRunStatus.RETRYING.value,
        AgentRunStatus.FALLBACK.value,
        AgentRunStatus.FAILED.value,
        AgentRunStatus.CANCELLED.value,
    },
    AgentRunStatus.WAITING_APPROVAL.value: {
        AgentRunStatus.WAITING_APPROVAL.value,
        AgentRunStatus.RUNNING.value,
        AgentRunStatus.FAILED.value,
        AgentRunStatus.FAILED_FINAL.value,
        AgentRunStatus.CANCELLED.value,
    },
    AgentRunStatus.EVALUATING.value: {
        AgentRunStatus.EVALUATING.value,
        AgentRunStatus.RUNNING.value,
        AgentRunStatus.COMPLETED.value,
        AgentRunStatus.PARTIAL.value,
        AgentRunStatus.FAILED.value,
        AgentRunStatus.FAILED_FINAL.value,
    },
    AgentRunStatus.RETRYING.value: {
        AgentRunStatus.RETRYING.value,
        AgentRunStatus.RUNNING.value,
        AgentRunStatus.FALLBACK.value,
        AgentRunStatus.COMPLETED.value,
        AgentRunStatus.PARTIAL.value,
        AgentRunStatus.FAILED.value,
        AgentRunStatus.FAILED_FINAL.value,
        AgentRunStatus.CANCELLED.value,
    },
    AgentRunStatus.FALLBACK.value: {
        AgentRunStatus.FALLBACK.value,
        AgentRunStatus.RUNNING.value,
        AgentRunStatus.COMPLETED.value,
        AgentRunStatus.PARTIAL.value,
        AgentRunStatus.FAILED.value,
        AgentRunStatus.FAILED_FINAL.value,
        AgentRunStatus.CANCELLED.value,
    },
    AgentRunStatus.COMPLETED.value: {AgentRunStatus.COMPLETED.value},
    AgentRunStatus.PARTIAL.value: {AgentRunStatus.PARTIAL.value},
    AgentRunStatus.FAILED.value: {
        AgentRunStatus.FAILED.value,
        AgentRunStatus.RETRYING.value,
        AgentRunStatus.FALLBACK.value,
        AgentRunStatus.FAILED_FINAL.value,
        AgentRunStatus.CREATED.value,
        AgentRunStatus.READY.value,
    },
    AgentRunStatus.FAILED_FINAL.value: {AgentRunStatus.FAILED_FINAL.value},
    AgentRunStatus.CANCELLED.value: {AgentRunStatus.CANCELLED.value},
    AgentRunStatus.SKIPPED.value: {AgentRunStatus.SKIPPED.value},
}

# Ma trận các bước chuyển đổi hợp lệ cho AgentPlan
PLAN_ALLOWED_TRANSITIONS: Dict[str, Set[str]] = {
    AgentPlanStatus.DRAFT.value: {
        AgentPlanStatus.DRAFT.value,
        AgentPlanStatus.PLANNING.value,
        AgentPlanStatus.READY.value,
        AgentPlanStatus.APPROVED.value,
        AgentPlanStatus.IN_PROGRESS.value,
        AgentPlanStatus.RUNNING.value,
        AgentPlanStatus.CANCELLED.value,
    },
    AgentPlanStatus.PLANNING.value: {
        AgentPlanStatus.PLANNING.value,
        AgentPlanStatus.DRAFT.value,
        AgentPlanStatus.READY.value,
        AgentPlanStatus.APPROVED.value,
        AgentPlanStatus.CANCELLED.value,
    },
    AgentPlanStatus.READY.value: {
        AgentPlanStatus.READY.value,
        AgentPlanStatus.APPROVED.value,
        AgentPlanStatus.IN_PROGRESS.value,
        AgentPlanStatus.RUNNING.value,
        AgentPlanStatus.CANCELLED.value,
    },
    AgentPlanStatus.APPROVED.value: {
        AgentPlanStatus.APPROVED.value,
        AgentPlanStatus.IN_PROGRESS.value,
        AgentPlanStatus.RUNNING.value,
        AgentPlanStatus.COMPLETED.value,
        AgentPlanStatus.FAILED.value,
        AgentPlanStatus.FAILED_FINAL.value,
        AgentPlanStatus.CANCELLED.value,
    },
    AgentPlanStatus.IN_PROGRESS.value: {
        AgentPlanStatus.IN_PROGRESS.value,
        AgentPlanStatus.RUNNING.value,
        AgentPlanStatus.WAITING_APPROVAL.value,
        AgentPlanStatus.EVALUATING.value,
        AgentPlanStatus.COMPLETED.value,
        AgentPlanStatus.FAILED.value,
        AgentPlanStatus.FAILED_FINAL.value,
        AgentPlanStatus.CANCELLED.value,
    },
    AgentPlanStatus.RUNNING.value: {
        AgentPlanStatus.RUNNING.value,
        AgentPlanStatus.IN_PROGRESS.value,
        AgentPlanStatus.WAITING_APPROVAL.value,
        AgentPlanStatus.EVALUATING.value,
        AgentPlanStatus.COMPLETED.value,
        AgentPlanStatus.FAILED.value,
        AgentPlanStatus.FAILED_FINAL.value,
        AgentPlanStatus.CANCELLED.value,
    },
    AgentPlanStatus.WAITING_APPROVAL.value: {
        AgentPlanStatus.WAITING_APPROVAL.value,
        AgentPlanStatus.IN_PROGRESS.value,
        AgentPlanStatus.RUNNING.value,
        AgentPlanStatus.CANCELLED.value,
        AgentPlanStatus.FAILED.value,
        AgentPlanStatus.FAILED_FINAL.value,
    },
    AgentPlanStatus.EVALUATING.value: {
        AgentPlanStatus.EVALUATING.value,
        AgentPlanStatus.IN_PROGRESS.value,
        AgentPlanStatus.RUNNING.value,
        AgentPlanStatus.COMPLETED.value,
        AgentPlanStatus.FAILED.value,
        AgentPlanStatus.FAILED_FINAL.value,
    },
    AgentPlanStatus.COMPLETED.value: {AgentPlanStatus.COMPLETED.value},
    AgentPlanStatus.FAILED.value: {
        AgentPlanStatus.FAILED.value,
        AgentPlanStatus.IN_PROGRESS.value,
        AgentPlanStatus.RUNNING.value,
        AgentPlanStatus.DRAFT.value,
        AgentPlanStatus.FAILED_FINAL.value,
    },
    AgentPlanStatus.FAILED_FINAL.value: {AgentPlanStatus.FAILED_FINAL.value},
    AgentPlanStatus.CANCELLED.value: {AgentPlanStatus.CANCELLED.value},
}

# Ma trận các bước chuyển đổi hợp lệ cho AgentPlanStep
STEP_ALLOWED_TRANSITIONS: Dict[str, Set[str]] = {
    AgentPlanStepStatus.PENDING.value: {
        AgentPlanStepStatus.PENDING.value,
        AgentPlanStepStatus.READY.value,
        AgentPlanStepStatus.RUNNING.value,
        AgentPlanStepStatus.WAITING_APPROVAL.value,
        AgentPlanStepStatus.WAITING_TOOL.value,
        AgentPlanStepStatus.CANCELLED.value,
        AgentPlanStepStatus.SKIPPED.value,
    },
    AgentPlanStepStatus.CREATED.value: {
        AgentPlanStepStatus.CREATED.value,
        AgentPlanStepStatus.PENDING.value,
        AgentPlanStepStatus.READY.value,
        AgentPlanStepStatus.RUNNING.value,
        AgentPlanStepStatus.CANCELLED.value,
        AgentPlanStepStatus.SKIPPED.value,
    },
    AgentPlanStepStatus.READY.value: {
        AgentPlanStepStatus.READY.value,
        AgentPlanStepStatus.RUNNING.value,
        AgentPlanStepStatus.WAITING_APPROVAL.value,
        AgentPlanStepStatus.WAITING_TOOL.value,
        AgentPlanStepStatus.CANCELLED.value,
        AgentPlanStepStatus.SKIPPED.value,
    },
    AgentPlanStepStatus.RUNNING.value: {
        AgentPlanStepStatus.RUNNING.value,
        AgentPlanStepStatus.WAITING_TOOL.value,
        AgentPlanStepStatus.WAITING_APPROVAL.value,
        AgentPlanStepStatus.RETRYING.value,
        AgentPlanStepStatus.FALLBACK.value,
        AgentPlanStepStatus.COMPLETED.value,
        AgentPlanStepStatus.FAILED.value,
        AgentPlanStepStatus.FAILED_FINAL.value,
        AgentPlanStepStatus.CANCELLED.value,
        AgentPlanStepStatus.SKIPPED.value,
    },
    AgentPlanStepStatus.WAITING_TOOL.value: {
        AgentPlanStepStatus.WAITING_TOOL.value,
        AgentPlanStepStatus.RUNNING.value,
        AgentPlanStepStatus.RETRYING.value,
        AgentPlanStepStatus.FALLBACK.value,
        AgentPlanStepStatus.FAILED.value,
        AgentPlanStepStatus.FAILED_FINAL.value,
        AgentPlanStepStatus.CANCELLED.value,
    },
    AgentPlanStepStatus.WAITING_APPROVAL.value: {
        AgentPlanStepStatus.WAITING_APPROVAL.value,
        AgentPlanStepStatus.RUNNING.value,
        AgentPlanStepStatus.COMPLETED.value,
        AgentPlanStepStatus.FAILED.value,
        AgentPlanStepStatus.FAILED_FINAL.value,
        AgentPlanStepStatus.CANCELLED.value,
        AgentPlanStepStatus.SKIPPED.value,
    },
    AgentPlanStepStatus.RETRYING.value: {
        AgentPlanStepStatus.RETRYING.value,
        AgentPlanStepStatus.RUNNING.value,
        AgentPlanStepStatus.FALLBACK.value,
        AgentPlanStepStatus.COMPLETED.value,
        AgentPlanStepStatus.FAILED.value,
        AgentPlanStepStatus.FAILED_FINAL.value,
        AgentPlanStepStatus.CANCELLED.value,
    },
    AgentPlanStepStatus.FALLBACK.value: {
        AgentPlanStepStatus.FALLBACK.value,
        AgentPlanStepStatus.RUNNING.value,
        AgentPlanStepStatus.COMPLETED.value,
        AgentPlanStepStatus.FAILED.value,
        AgentPlanStepStatus.FAILED_FINAL.value,
        AgentPlanStepStatus.CANCELLED.value,
    },
    AgentPlanStepStatus.COMPLETED.value: {AgentPlanStepStatus.COMPLETED.value},
    AgentPlanStepStatus.FAILED.value: {
        AgentPlanStepStatus.FAILED.value,
        AgentPlanStepStatus.RETRYING.value,
        AgentPlanStepStatus.FALLBACK.value,
        AgentPlanStepStatus.FAILED_FINAL.value,
        AgentPlanStepStatus.PENDING.value,
        AgentPlanStepStatus.READY.value,
    },
    AgentPlanStepStatus.FAILED_FINAL.value: {AgentPlanStepStatus.FAILED_FINAL.value},
    AgentPlanStepStatus.CANCELLED.value: {AgentPlanStepStatus.CANCELLED.value},
    AgentPlanStepStatus.SKIPPED.value: {AgentPlanStepStatus.SKIPPED.value},
}


def _norm(status_val: Optional[Union[str, Enum]]) -> Optional[str]:
    """Chuẩn hóa giá trị trạng thái thành chuỗi viết thường không khoảng trắng."""
    if status_val is None:
        return None
    if isinstance(status_val, Enum):
        return str(status_val.value).lower()
    return str(status_val).lower().strip()


def validate_run_transition(old_status: Optional[Union[str, AgentRunStatus]], new_status: Union[str, AgentRunStatus]) -> str:
    """Kiểm tra tính hợp lệ khi chuyển đổi trạng thái AgentRun."""
    new_norm = _norm(new_status)
    if not new_norm:
        raise ValueError("Trạng thái mới của AgentRun không được để trống (New run status cannot be empty)")
    old_norm = _norm(old_status)
    if not old_norm:
        return new_norm
    if old_norm == new_norm:
        return new_norm
    allowed = RUN_ALLOWED_TRANSITIONS.get(old_norm, set())
    if new_norm not in allowed:
        old_vi = RUN_STATUS_LABELS_VI.get(old_norm, old_norm)
        new_vi = RUN_STATUS_LABELS_VI.get(new_norm, new_norm)
        raise ValueError(
            f"Chuyển đổi trạng thái AgentRun không hợp lệ từ '{old_norm}' ({old_vi}) sang '{new_norm}' ({new_vi})"
        )
    return new_norm


def validate_plan_transition(old_status: Optional[Union[str, AgentPlanStatus]], new_status: Union[str, AgentPlanStatus]) -> str:
    """Kiểm tra tính hợp lệ khi chuyển đổi trạng thái AgentPlan."""
    new_norm = _norm(new_status)
    if not new_norm:
        raise ValueError("Trạng thái mới của AgentPlan không được để trống (New plan status cannot be empty)")
    old_norm = _norm(old_status)
    if not old_norm:
        return new_norm
    if old_norm == new_norm:
        return new_norm
    allowed = PLAN_ALLOWED_TRANSITIONS.get(old_norm, set())
    if new_norm not in allowed:
        old_vi = PLAN_STATUS_LABELS_VI.get(old_norm, old_norm)
        new_vi = PLAN_STATUS_LABELS_VI.get(new_norm, new_norm)
        raise ValueError(
            f"Chuyển đổi trạng thái AgentPlan không hợp lệ từ '{old_norm}' ({old_vi}) sang '{new_norm}' ({new_vi})"
        )
    return new_norm


def validate_step_transition(old_status: Optional[Union[str, AgentPlanStepStatus]], new_status: Union[str, AgentPlanStepStatus]) -> str:
    """Kiểm tra tính hợp lệ khi chuyển đổi trạng thái AgentPlanStep."""
    new_norm = _norm(new_status)
    if not new_norm:
        raise ValueError("Trạng thái mới của Bước thực thi không được để trống (New plan step status cannot be empty)")
    old_norm = _norm(old_status)
    if not old_norm:
        return new_norm
    if old_norm == new_norm:
        return new_norm
    allowed = STEP_ALLOWED_TRANSITIONS.get(old_norm, set())
    if new_norm not in allowed:
        old_vi = STEP_STATUS_LABELS_VI.get(old_norm, old_norm)
        new_vi = STEP_STATUS_LABELS_VI.get(new_norm, new_norm)
        raise ValueError(
            f"Chuyển đổi trạng thái AgentPlanStep không hợp lệ từ '{old_norm}' ({old_vi}) sang '{new_norm}' ({new_vi})"
        )
    return new_norm


def get_run_status_label_vi(status: Union[str, AgentRunStatus]) -> str:
    """Lấy nhãn tiếng Việt cho trạng thái AgentRun."""
    norm = _norm(status)
    return RUN_STATUS_LABELS_VI.get(norm or "", str(status))


def get_plan_status_label_vi(status: Union[str, AgentPlanStatus]) -> str:
    """Lấy nhãn tiếng Việt cho trạng thái AgentPlan."""
    norm = _norm(status)
    return PLAN_STATUS_LABELS_VI.get(norm or "", str(status))


def get_step_status_label_vi(status: Union[str, AgentPlanStepStatus]) -> str:
    """Lấy nhãn tiếng Việt cho trạng thái AgentPlanStep."""
    norm = _norm(status)
    return STEP_STATUS_LABELS_VI.get(norm or "", str(status))
