"""Stuck & Loop Detector for COSA Agent Runtime (§P0.6, C1/C2 Spec).

Detects unproductive repetitive behavior (SAME_ACTION_LOOP, SAME_ERROR_LOOP, TOOL_PING_PONG)
and enforces mitigation policies before runaway resource consumption occurs.
"""

from dataclasses import dataclass
import json
import logging
from typing import Optional, List

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.governance.models import AgentToolCall

logger = logging.getLogger(__name__)


class StuckAnalysisResult(BaseModel):
    is_stuck: bool = False
    loop_type: Optional[str] = None  # SAME_ACTION_LOOP, SAME_ERROR_LOOP, TOOL_PING_PONG
    repeated_count: int = 0
    suggested_action: str = "PROCEED"  # PROCEED, OBSERVE, WARN_CHANGE_STRATEGY, ABORT_RUN
    detail: str = ""


class StuckDetector:
    """Detects repeating tool call loops and infinite recovery cycles."""

    @classmethod
    def analyze_run(
        cls,
        db: Session,
        run_id: int,
        history_window: int = 10,
    ) -> StuckAnalysisResult:
        """Scan recent tool calls for a run to identify repetitive loop patterns."""
        tool_calls = db.execute(
            select(AgentToolCall)
            .where(AgentToolCall.run_id == run_id)
            .order_by(AgentToolCall.started_at.asc())
        ).scalars().all()

        if len(tool_calls) < 2:
            return StuckAnalysisResult(is_stuck=False, suggested_action="PROCEED")

        recent = tool_calls[-history_window:]

        # 1. Check SAME_ACTION_LOOP (identical tool + args)
        action_signatures = [
            f"{tc.tool_name}:{json.dumps(tc.input_jsonb or {}, sort_keys=True)}"
            for tc in recent
        ]

        if len(action_signatures) >= 3:
            last_sig = action_signatures[-1]
            consecutive_same_action = 0
            for sig in reversed(action_signatures):
                if sig == last_sig:
                    consecutive_same_action += 1
                else:
                    break

            if consecutive_same_action >= 5:
                return StuckAnalysisResult(
                    is_stuck=True,
                    loop_type="SAME_ACTION_LOOP",
                    repeated_count=consecutive_same_action,
                    suggested_action="ABORT_RUN",
                    detail=f"Identical action executed {consecutive_same_action} times consecutively.",
                )
            elif consecutive_same_action >= 3:
                return StuckAnalysisResult(
                    is_stuck=True,
                    loop_type="SAME_ACTION_LOOP",
                    repeated_count=consecutive_same_action,
                    suggested_action="WARN_CHANGE_STRATEGY",
                    detail=f"Action repeated {consecutive_same_action} times; strategy change required.",
                )
            elif consecutive_same_action >= 2:
                return StuckAnalysisResult(
                    is_stuck=False,
                    loop_type="SAME_ACTION_LOOP",
                    repeated_count=consecutive_same_action,
                    suggested_action="OBSERVE",
                    detail=f"Action repeated {consecutive_same_action} times; observing.",
                )

        # 2. Check SAME_ERROR_LOOP (consecutive error status with identical error messages)
        error_calls = [tc for tc in recent if tc.status == "error"]
        if len(error_calls) >= 3:
            error_msgs = [
                json.dumps(tc.output_jsonb or {}, sort_keys=True)
                for tc in error_calls
            ]
            last_err = error_msgs[-1]
            consecutive_same_error = sum(1 for m in error_msgs[-3:] if m == last_err)
            if consecutive_same_error >= 3:
                return StuckAnalysisResult(
                    is_stuck=True,
                    loop_type="SAME_ERROR_LOOP",
                    repeated_count=consecutive_same_error,
                    suggested_action="ABORT_RUN" if len(error_calls) >= 5 else "WARN_CHANGE_STRATEGY",
                    detail=f"Same error encountered {consecutive_same_error} times repeatedly.",
                )

        # 3. Check TOOL_PING_PONG (A -> B -> A -> B pattern)
        if len(recent) >= 4:
            tool_names = [tc.tool_name for tc in recent]
            if (
                tool_names[-1] == tool_names[-3]
                and tool_names[-2] == tool_names[-4]
                and tool_names[-1] != tool_names[-2]
            ):
                return StuckAnalysisResult(
                    is_stuck=True,
                    loop_type="TOOL_PING_PONG",
                    repeated_count=4,
                    suggested_action="WARN_CHANGE_STRATEGY",
                    detail=f"Ping-pong cycle detected between {tool_names[-1]} and {tool_names[-2]}.",
                )

        return StuckAnalysisResult(is_stuck=False, suggested_action="PROCEED")
