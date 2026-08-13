import asyncio
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.snowflake import generate_snowflake_id
from app.core.feature_flags import is_enabled, FLAG_NEXT_BEST_ACTION_V12

from app.modules.strategy.models import (
    NextActionCandidate,
    NextActionRanking,
    GateDecision,
    WeeklyCommitment,
    ProjectPestelImpact,
    Project,
    PortfolioDependency,
    ModelRunAudit,
)
from app.modules.chat.ai_router import ChatProvider, ChatTurn
from app.modules.chat.model_profiles import resolve_profile, build_profile_provider
from app.modules.chat.model_registry import is_provider_configured


logger = logging.getLogger(__name__)

AI_RERANK_SHORTLIST_SIZE = 5


class NextBestActionService:
    """CEO / Founder Next Best Action Recommendation Engine (mCOSA V12 Spec §37 & Sprint 9).

    Tối ưu hóa thứ tự ưu tiên các hành động điều hành (R0 Deterministic Formula + R2 AI Rerank).
    """

    def __init__(self, db: Session, workspace_id: int, user_id: int):
        self.db = db
        self.workspace_id = workspace_id
        self.user_id = user_id

    @staticmethod
    def compute_r0_score(urgency_score: float, impact_score: float, effort_score: float) -> float:
        """Công thức điểm R0 thuần quy tắc (Spec §37).

        R0 = (Urgency * 0.4) + (Impact * 0.4) + ((1.0 - Effort) * 0.2)
        """
        urgency = max(0.0, min(1.0, urgency_score))
        impact = max(0.0, min(1.0, impact_score))
        effort = max(0.0, min(1.0, effort_score))
        return round((urgency * 0.4) + (impact * 0.4) + ((1.0 - effort) * 0.2), 4)

    def generate_candidates_from_runtime(
        self,
        project_id: Optional[int] = None,
        portfolio_id: Optional[int] = None,
    ) -> List[NextActionCandidate]:
        candidates: List[NextActionCandidate] = []

        # 1. Quét các Stage Gate đang ở trạng thái Tạm giữ / Chờ đánh giá (Gate Decisions HOLD)
        gate_query = self.db.query(GateDecision).filter(
            GateDecision.workspace_id == self.workspace_id,
            GateDecision.decision == "HOLD",
        )
        if project_id:
            gate_query = gate_query.filter(GateDecision.project_id == project_id)

        for gate_dec in gate_query.all():
            cand = NextActionCandidate(
                id=generate_snowflake_id(),
                workspace_id=self.workspace_id,
                project_id=gate_dec.project_id,
                portfolio_id=portfolio_id,
                title="Đánh giá lại Gate Decision đang ở trạng thái HOLD",
                description=f"Cần xem xét bằng chứng mới để gỡ bỏ quyết định HOLD: {gate_dec.rationale}",
                category="STAGE_GATE_REVIEW",
                urgency_score=0.9,
                impact_score=0.85,
                effort_score=0.3,
                r0_score=self.compute_r0_score(0.9, 0.85, 0.3),
                status="proposed",
                created_at=datetime.utcnow(),
            )
            self.db.add(cand)
            candidates.append(cand)


        # 2. Quét rủi ro PESTEL âm tiêu cực lớn chưa có biện pháp giảm thiểu
        pestel_query = self.db.query(ProjectPestelImpact).filter(
            ProjectPestelImpact.workspace_id == self.workspace_id,
            ProjectPestelImpact.impact_type == "NEGATIVE",
            ProjectPestelImpact.impact_magnitude == "HIGH",
            ProjectPestelImpact.mitigation_or_leverage.is_(None),
        )
        if project_id:
            pestel_query = pestel_query.filter(ProjectPestelImpact.project_id == project_id)

        for p_imp in pestel_query.all():
            cand = NextActionCandidate(
                id=generate_snowflake_id(),
                workspace_id=self.workspace_id,
                project_id=p_imp.project_id,
                portfolio_id=portfolio_id,
                title="Giảm thiểu Rủi ro PESTEL Tiêu cực Rất lớn",
                description="Bổ sung phương án ứng phó cho tác động vĩ mô tiêu cực cấp độ HIGH",
                category="PESTEL_MITIGATION",
                urgency_score=0.85,
                impact_score=0.9,
                effort_score=0.5,
                r0_score=self.compute_r0_score(0.85, 0.9, 0.5),
                status="proposed",
                created_at=datetime.utcnow(),
            )
            self.db.add(cand)
            candidates.append(cand)

        self.db.commit()
        return candidates

    def evaluate_and_rank(
        self,
        project_id: Optional[int] = None,
        portfolio_id: Optional[int] = None,
        use_ai_rerank: bool = True,
    ) -> List[Dict[str, Any]]:
        """3-round ranking pipeline (Spec §37): R0 deterministic -> R1 transparent rules
        -> R2 AI/Terra rerank (best-effort; falls back to R1 order on any AI failure)."""
        # Tự động sinh ứng viên từ runtime state
        candidates = self.generate_candidates_from_runtime(project_id, portfolio_id)

        # Nếu chưa có ứng viên tự động, lấy các candidate đề xuất sẵn
        if not candidates:
            cand_query = self.db.query(NextActionCandidate).filter(
                NextActionCandidate.workspace_id == self.workspace_id,
                NextActionCandidate.status == "proposed",
            )
            if project_id:
                cand_query = cand_query.filter(NextActionCandidate.project_id == project_id)
            if portfolio_id:
                cand_query = cand_query.filter(NextActionCandidate.portfolio_id == portfolio_id)
            candidates = cand_query.all()

        # R0: công thức trọng số thuần túy
        for c in candidates:
            c.r0_score = self.compute_r0_score(c.urgency_score, c.impact_score, c.effort_score)

        # R1: quy tắc trọng số minh bạch bổ sung trên nền R0 (Dependency Unlock, Gate/Governance)
        r1_scored = self._apply_r1_rules(candidates)

        # R2: AI/Terra rerank cho shortlist, best-effort - không bao giờ làm hỏng kết quả R1
        ranking_round = "R1_RULES"
        final_scored = r1_scored
        if use_ai_rerank:
            final_scored, ranking_round = self._maybe_ai_rerank(r1_scored)

        # Lưu vết kết quả xếp hạng vào NextActionRanking
        rankings: List[Dict[str, Any]] = []
        for idx, (cand, score, reasoning) in enumerate(final_scored, start=1):
            ranking = NextActionRanking(
                id=generate_snowflake_id(),
                workspace_id=self.workspace_id,
                candidate_id=cand.id,
                ranking_round=ranking_round,
                rank_position=idx,
                composite_score=score,
                reasoning=f"#{idx}: {reasoning}",
                created_at=datetime.utcnow(),
            )
            self.db.add(ranking)
            rankings.append({
                "rank_position": idx,
                "candidate": self._serialize_candidate(cand),
                "composite_score": score,
                "reasoning": ranking.reasoning,
            })

        self.db.commit()
        return rankings

    def _apply_r1_rules(self, candidates: List[NextActionCandidate]) -> List[Tuple[NextActionCandidate, float, str]]:
        """R1: transparent weighted rules on top of R0 (Spec §37 - "Dependency Unlock",
        stage-gate/governance priority). Fully deterministic, no AI - kept explainable."""
        unlock_project_ids = {
            d.predecessor_project_id
            for d in self.db.query(PortfolioDependency)
            .filter(PortfolioDependency.workspace_id == self.workspace_id)
            .all()
        }

        scored: List[Tuple[NextActionCandidate, float, str]] = []
        for c in candidates:
            bonus = 0.0
            reasons = [f"R0={c.r0_score}"]

            if c.project_id and c.project_id in unlock_project_ids:
                bonus += 0.05
                reasons.append("Dependency Unlock +0.05 (giải phóng dự án đang phụ thuộc)")

            if c.category in ("STAGE_GATE_REVIEW", "GOVERNANCE_DECISION"):
                bonus += 0.03
                reasons.append(f"Category '{c.category}' +0.03 (ưu tiên quyết định quản trị/gate)")

            r1_score = round(min(1.0, c.r0_score + bonus), 4)
            reasons.insert(1, f"R1={r1_score}")
            scored.append((c, r1_score, "; ".join(reasons)))

        scored.sort(key=lambda t: t[1], reverse=True)
        return scored

    def _maybe_ai_rerank(
        self, r1_scored: List[Tuple[NextActionCandidate, float, str]]
    ) -> Tuple[List[Tuple[NextActionCandidate, float, str]], str]:
        """R2: AI/Terra rerank of the top shortlist (Spec §37, §40 STRATEGIC_ANALYZER profile).

        Best-effort only: any misconfiguration, provider error, or malformed AI response
        falls back to the R1 order unchanged. AI rerank must never be able to produce a
        worse or broken result than R1 - it can only reorder the same shortlist.
        """
        if not r1_scored:
            return r1_scored, "R1_RULES"

        provider_name, model_name = resolve_profile("STRATEGIC_ANALYZER")
        if not is_provider_configured(provider_name):
            return r1_scored, "R1_RULES"

        shortlist = r1_scored[:AI_RERANK_SHORTLIST_SIZE]
        rest = r1_scored[AI_RERANK_SHORTLIST_SIZE:]

        try:
            provider = build_profile_provider("STRATEGIC_ANALYZER")
            reranked_shortlist = self._call_ai_rerank(shortlist, provider, provider_name, model_name)
        except Exception:
            logger.warning("R2 AI rerank thất bại, giữ nguyên thứ hạng R1", exc_info=True)
            return r1_scored, "R1_RULES"

        if reranked_shortlist is None:
            return r1_scored, "R1_RULES"

        return reranked_shortlist + rest, "R2_AI_TERRA"

    def _call_ai_rerank(
        self,
        shortlist: List[Tuple[NextActionCandidate, float, str]],
        provider: ChatProvider,
        provider_name: str,
        model_name: str,
    ) -> Optional[List[Tuple[NextActionCandidate, float, str]]]:
        """Gọi STRATEGIC_ANALYZER để sắp xếp lại shortlist. Trả về None nếu output không hợp lệ."""
        by_id = {str(c.id): (c, score) for c, score, _ in shortlist}
        items_desc = "\n".join(
            f"- id={cid}, title={c.title!r}, category={c.category}, r1_score={score}"
            for cid, (c, score) in by_id.items()
        )
        prompt = (
            "Bạn là STRATEGIC_ANALYZER cho khả năng Next Best Action của COSA OS. "
            "Dưới đây là danh sách ứng viên hành động đã được xếp hạng sơ bộ theo quy tắc R1. "
            "Hãy sắp xếp lại theo mức độ ưu tiên chiến lược thực sự, xét thêm bối cảnh mà công "
            "thức số không nắm được (mức độ khẩn cấp thực tế, rủi ro dây chuyền). "
            "CHỈ trả về JSON, không giải thích thêm, đúng định dạng:\n"
            '{"ranking": [{"id": "<candidate_id>", "reasoning": "<lý do ngắn>"}, ...]}\n'
            "Ranking phải chứa đúng và đủ các id sau, không thêm/bớt:\n"
            f"{items_desc}"
        )

        turns = [ChatTurn(role="user", content=prompt)]
        start = datetime.utcnow()
        raw_text = asyncio.run(self._consume_stream(provider, turns))
        latency_ms = int((datetime.utcnow() - start).total_seconds() * 1000)

        parsed = self._parse_ai_ranking(raw_text, expected_ids=set(by_id.keys()))

        audit = ModelRunAudit(
            id=generate_snowflake_id(),
            workspace_id=self.workspace_id,
            model_profile=f"STRATEGIC_ANALYZER:{provider_name}/{model_name}",
            prompt_tokens=len(prompt) // 4,
            completion_tokens=len(raw_text) // 4,
            latency_ms=latency_ms,
            status="success" if parsed is not None else "invalid_output",
            created_at=datetime.utcnow(),
        )
        self.db.add(audit)

        if parsed is None:
            return None

        result: List[Tuple[NextActionCandidate, float, str]] = []
        for item in parsed:
            cand, r1_score = by_id[item["id"]]
            result.append((cand, r1_score, f"R2 AI/Terra: {item['reasoning']}"))
        return result

    @staticmethod
    async def _consume_stream(provider: ChatProvider, turns: List[ChatTurn]) -> str:
        chunks: List[str] = []
        async for event in provider.stream_chat(turns):
            if event.kind == "delta":
                chunks.append(event.content)
            elif event.kind == "failed":
                raise RuntimeError(f"AI provider stream failed: {event.error_code}")
        return "".join(chunks)

    @staticmethod
    def _parse_ai_ranking(raw_text: str, expected_ids: set) -> Optional[List[Dict[str, str]]]:
        try:
            start_idx = raw_text.index("{")
            end_idx = raw_text.rindex("}") + 1
            data = json.loads(raw_text[start_idx:end_idx])
            ranking = data["ranking"]
            got_ids = {str(item["id"]) for item in ranking}
            if got_ids != expected_ids:
                return None
            return [{"id": str(item["id"]), "reasoning": str(item.get("reasoning", ""))} for item in ranking]
        except Exception:
            return None

    def get_top_next_actions(self, limit: int = 5) -> List[Dict[str, Any]]:
        candidates = (
            self.db.query(NextActionCandidate)
            .filter(
                NextActionCandidate.workspace_id == self.workspace_id,
                NextActionCandidate.status.in_(["proposed", "accepted"]),
            )
            .order_by(NextActionCandidate.r0_score.desc())
            .limit(limit)
            .all()
        )
        return [self._serialize_candidate(c) for c in candidates]

    def update_action_status(self, candidate_id: int, status_val: str) -> Dict[str, Any]:
        cand = (
            self.db.query(NextActionCandidate)
            .filter(
                NextActionCandidate.id == candidate_id,
                NextActionCandidate.workspace_id == self.workspace_id,
            )
            .first()
        )
        if not cand:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NextActionCandidate not found")

        cand.status = status_val
        self.db.commit()
        self.db.refresh(cand)
        return self._serialize_candidate(cand)

    def _serialize_candidate(self, c: NextActionCandidate) -> Dict[str, Any]:
        return {
            "id": str(c.id),
            "project_id": str(c.project_id) if c.project_id else None,
            "portfolio_id": str(c.portfolio_id) if c.portfolio_id else None,
            "title": c.title,
            "description": c.description,
            "category": c.category,
            "urgency_score": c.urgency_score,
            "impact_score": c.impact_score,
            "effort_score": c.effort_score,
            "r0_score": c.r0_score,
            "status": c.status,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
