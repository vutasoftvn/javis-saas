from typing import Any, Dict, List, Optional


class MarketingReasoningCapability:
    """Reasoning capability for analyzing marketing channel effectiveness, CAC, and conversion bottlenecks."""

    @classmethod
    def analyze_funnel_bottlenecks(
        cls,
        funnel_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        data = funnel_data or {}
        stages = data.get("stages", [
            {"stage": "impressions", "count": 10000},
            {"stage": "clicks", "count": 800},
            {"stage": "leads", "count": 80},
            {"stage": "opportunities", "count": 12},
            {"stage": "closed_won", "count": 3},
        ])

        bottlenecks = []
        for i in range(len(stages) - 1):
            curr_stage = stages[i]
            next_stage = stages[i + 1]
            curr_cnt = curr_stage.get("count", 0)
            next_cnt = next_stage.get("count", 0)
            rate = (next_cnt / curr_cnt) if curr_cnt > 0 else 0.0
            if rate < 0.15:
                bottlenecks.append({
                    "from_stage": curr_stage.get("stage"),
                    "to_stage": next_stage.get("stage"),
                    "conversion_rate": round(rate, 4),
                    "recommendation": f"Optimize conversion from {curr_stage.get('stage')} to {next_stage.get('stage')}.",
                })

        return {
            "status": "success",
            "stages_analyzed": len(stages),
            "bottlenecks": bottlenecks,
            "summary": f"Identified {len(bottlenecks)} conversion bottleneck(s) in marketing funnel.",
        }
