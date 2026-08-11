"""Tổng hợp usage/cost trực tiếp từ ai_runs - không có bảng ledger riêng vì ai_runs đã
đủ cột (workspace_id, provider, model, tokens, cost_estimate). Chỉ tính run đã hoàn tất
(status=completed): chỉ ghi/đếm cost khi provider đã thực sự trả lời xong, không ước
lượng cho run đang chạy dở hoặc thất bại."""

import uuid
from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.db.models import AIRun

ROLLING_WINDOW_DAYS = 30


def _aggregate(runs: list[AIRun]) -> dict:
    return {
        "runs": len(runs),
        "input_tokens": sum(r.input_tokens or 0 for r in runs),
        "output_tokens": sum(r.output_tokens or 0 for r in runs),
        "cost_estimate": float(sum(r.cost_estimate or 0 for r in runs)),
    }


def get_usage_summary(db: Session, workspace_id: uuid.UUID) -> dict:
    completed_runs = (
        db.query(AIRun)
        .filter(AIRun.workspace_id == workspace_id, AIRun.status == "completed")
        .all()
    )

    cutoff = datetime.utcnow() - timedelta(days=ROLLING_WINDOW_DAYS)
    rolling_runs = [r for r in completed_runs if r.finished_at and r.finished_at >= cutoff]

    by_provider: dict[str, list[AIRun]] = defaultdict(list)
    for run in completed_runs:
        by_provider[run.provider].append(run)

    return {
        "rolling_30d": _aggregate(rolling_runs),
        "all_time": _aggregate(completed_runs),
        "by_provider": {
            provider: _aggregate(runs) for provider, runs in by_provider.items()
        },
    }
