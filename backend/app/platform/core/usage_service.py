"""Tổng hợp usage/cost trực tiếp từ ai_runs - không có bảng ledger riêng vì ai_runs đã
đủ cột (workspace_id, provider, model, tokens, cost_estimate). Chỉ tính run đã hoàn tất
(status=completed): chỉ ghi/đếm cost khi provider đã thực sự trả lời xong, không ước
lượng cho run đang chạy dở hoặc thất bại."""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, Any

from sqlalchemy.orm import Session

from app.db.models import AIRun
from app.integrations.llm_providers.openrouter_service import fetch_openrouter_key_info
from app.workforce.chat.model_registry import get_model

ROLLING_WINDOW_DAYS = 30


def _aggregate(runs: list[AIRun]) -> dict:
    return {
        "runs": len(runs),
        "input_tokens": sum(r.input_tokens or 0 for r in runs),
        "output_tokens": sum(r.output_tokens or 0 for r in runs),
        "cost_estimate": float(sum(r.cost_estimate or 0 for r in runs)),
    }


def _model_label(provider: str, model: str) -> str:
    info = get_model(provider, model)
    if info and info.label:
        return info.label
    parts = model.split("/")
    return parts[-1].replace("-", " ").title()


def get_usage_summary(db: Session, workspace_id: int, period: str = "30d") -> dict:
    completed_runs = (
        db.query(AIRun)
        .filter(AIRun.workspace_id == workspace_id, AIRun.status == "completed")
        .all()
    )

    now = datetime.utcnow()
    day_cutoff = now - timedelta(days=1)
    week_cutoff = now - timedelta(days=7)
    month_cutoff = now - timedelta(days=30)

    today_runs = [r for r in completed_runs if r.finished_at and r.finished_at >= day_cutoff]
    week_runs = [r for r in completed_runs if r.finished_at and r.finished_at >= week_cutoff]
    month_runs = [r for r in completed_runs if r.finished_at and r.finished_at >= month_cutoff]

    p = (period or "30d").lower()
    if p in ("day", "1d", "today"):
        active_runs = today_runs
    elif p in ("week", "7d"):
        active_runs = week_runs
    elif p in ("month", "30d"):
        active_runs = month_runs
    else:
        active_runs = completed_runs

    by_provider_runs: dict[str, list[AIRun]] = defaultdict(list)
    by_provider_model_runs: dict[str, dict[str, list[AIRun]]] = defaultdict(lambda: defaultdict(list))

    for run in active_runs:
        by_provider_runs[run.provider].append(run)
        by_provider_model_runs[run.provider][run.model].append(run)

    by_provider_res: dict[str, Any] = {}
    for provider, runs in by_provider_runs.items():
        agg = _aggregate(runs)
        models_dict = {}
        for model_id, m_runs in by_provider_model_runs[provider].items():
            m_agg = _aggregate(m_runs)
            m_agg["label"] = _model_label(provider, model_id)
            models_dict[model_id] = m_agg
        agg["models"] = models_dict
        by_provider_res[provider] = agg

    from app.integrations.channels.models import WorkspaceSecret
    from app.integrations.channels.secrets_service import decrypt_for_workspace

    ws_secret = (
        db.query(WorkspaceSecret)
        .filter(WorkspaceSecret.workspace_id == workspace_id, WorkspaceSecret.key == "openrouter")
        .first()
    )
    is_custom_key = False
    custom_api_key = None
    if ws_secret and ws_secret.encrypted_value:
        decrypted = decrypt_for_workspace(workspace_id, ws_secret.encrypted_value)
        if decrypted:
            custom_api_key = decrypted
            is_custom_key = True

    openrouter_info = fetch_openrouter_key_info(api_key=custom_api_key)
    openrouter_info["is_custom_workspace_key"] = is_custom_key

    return {
        "period": period,
        "today": _aggregate(today_runs),
        "week_7d": _aggregate(week_runs),
        "rolling_30d": _aggregate(month_runs),
        "all_time": _aggregate(completed_runs),
        "current_period_summary": _aggregate(active_runs),
        "by_provider": by_provider_res,
        "openrouter_key_info": openrouter_info,
    }



