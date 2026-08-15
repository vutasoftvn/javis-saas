from typing import Any, Dict, List, Optional


class SalesReasoningCapability:
    """Capability for scoring prospect fit, qualifying leads, and prioritizing sales efforts."""

    @classmethod
    def score_prospects(
        cls,
        prospects: List[Dict[str, Any]],
        criteria: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        qualified = []
        for p in prospects:
            # Score computation based on title, industry, and size
            score = 70
            title = p.get("title", "").lower()
            if any(k in title for k in ("head", "director", "founder", "ceo", "vp")):
                score += 15
            if "ai" in p.get("industry", "").lower() or "tech" in p.get("industry", "").lower():
                score += 10

            item = {
                **p,
                "fit_score": min(score, 98),
                "qualification": "high_priority" if score >= 85 else "medium_priority",
                "recommended_angle": "Focus on AI automation & operational efficiency gains for founder teams.",
            }
            qualified.append(item)

        qualified.sort(key=lambda x: x["fit_score"], reverse=True)

        return {
            "status": "success",
            "scored_count": len(qualified),
            "high_priority_count": sum(1 for q in qualified if q["qualification"] == "high_priority"),
            "qualified_prospects": qualified,
            "summary": f"Scored {len(qualified)} prospects: {sum(1 for q in qualified if q['qualification'] == 'high_priority')} classified as high priority.",
        }
