import json
import logging
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, desc, and_

from founder_os.validation.models import (
    CustomerInterviewSession,
    VerbatimQuote,
    ProblemSeverityScorecard,
    PainPattern,
    CustomerRoleEnum,
    AutopsyClusterType,
)
from founder_os.validation.schemas import (
    ProblemScorecardRequest,
    ProblemScorecardResponse,
    DataAutopsyResponse,
    RoleCoverageResponse,
)
from workforce.chat.worker_prompt import run_worker_prompt

logger = logging.getLogger(__name__)

AUTOPSY_PROMPT = """You are COSA AI Data Autopsy Engine (F3.md §13, §14, §18).

Analyze all verbatim customer quotes and interview evidence from a project.
Identify:
1. PATTERNS: Repeating pains, frictions, or behaviors across multiple interviews (e.g. 6/7 customers struggle with manual reporting).
2. NICHES: Small subgroups experiencing unusually intense pain or urgency.
3. SHOCKS: Findings that directly contradict typical founder assumptions (e.g. customers prefer spreadsheets over all-in-one platforms).
4. RECOMMENDED_PROBLEM_STATEMENT: A strict Problem Statement WITHOUT any product features or solution pitch.
   Format: "[Customer Segment] đang gặp [Problem cụ thể] khi [Context], dẫn đến [Consequence]. Hiện họ đang dùng [Alternative] nhưng gặp [Limitation]."
5. RECOMMENDED_JTBD: Jobs-to-be-Done across 3 dimensions:
   - functional_job: What tasks they need to accomplish
   - emotional_job: How they want to feel (reduce anxiety, feel in control)
   - social_job: How they want to be perceived by their team/peers

Return ONLY valid JSON matching this schema:
{
  "patterns": [
    {"title": "Pattern title", "summary": "Detailed pattern", "frequency_count": 4}
  ],
  "niches": [
    {"title": "Niche title", "summary": "Niche pain details", "frequency_count": 2}
  ],
  "shocks": [
    {"title": "Shock title", "summary": "Counter-intuitive discovery", "frequency_count": 3}
  ],
  "recommended_problem_statement": "Problem Statement string",
  "recommended_jtbd": {
    "functional_job": "...",
    "emotional_job": "...",
    "social_job": "..."
  }
}
"""

def _extract_json(text: str) -> dict:
    cleaned = text.strip()
    if "```json" in cleaned:
        cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in cleaned:
        cleaned = cleaned.split("```", 1)[1].split("```", 1)[0].strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start_idx = cleaned.find("{")
        end_idx = cleaned.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            return json.loads(cleaned[start_idx : end_idx + 1])
        raise


class ProblemIntelligenceService:
    @staticmethod
    def get_or_calculate_scorecard(
        db: Session, workspace_id: int, project_id: int, override_data: Optional[ProblemScorecardRequest] = None
    ) -> ProblemScorecardResponse:
        """
        Lấy hoặc cập nhật Pain Severity Scorecard (50 điểm).
        Ngưỡng 40/50 là Playbook Heuristic (F2.md §4, §5).
        """
        scorecard = db.scalar(
            select(ProblemSeverityScorecard).where(
                and_(
                    ProblemSeverityScorecard.workspace_id == workspace_id,
                    ProblemSeverityScorecard.project_id == project_id,
                )
            )
        )

        if override_data:
            if not scorecard:
                scorecard = ProblemSeverityScorecard(
                    workspace_id=workspace_id,
                    project_id=project_id,
                )
                db.add(scorecard)

            scorecard.frequency_score = override_data.frequency_score
            scorecard.severity_score = override_data.severity_score
            scorecard.alternatives_score = override_data.alternatives_score
            scorecard.wtp_score = override_data.wtp_score
            scorecard.market_potential_score = override_data.market_potential_score
            scorecard.total_score = (
                override_data.frequency_score
                + override_data.severity_score
                + override_data.alternatives_score
                + override_data.wtp_score
                + override_data.market_potential_score
            )
            scorecard.interpretation_result = (
                "STRONG_PROBLEM_VALIDATION"
                if scorecard.total_score >= 40
                else "BELOW_RECOMMENDED_THRESHOLD"
            )
            scorecard.evidence_quality = "FOUNDER_ESTIMATE"
            scorecard.notes = override_data.notes
            db.commit()
            db.refresh(scorecard)
        elif not scorecard:
            # Tạo mặc định ban đầu nếu chưa có
            scorecard = ProblemSeverityScorecard(
                workspace_id=workspace_id,
                project_id=project_id,
                frequency_score=5,
                severity_score=5,
                alternatives_score=5,
                wtp_score=5,
                market_potential_score=5,
                total_score=25,
                interpretation_result="BELOW_RECOMMENDED_THRESHOLD",
                evidence_quality="UNVERIFIED",
            )
            db.add(scorecard)
            db.commit()
            db.refresh(scorecard)

        return ProblemScorecardResponse(
            id=scorecard.id,
            project_id=scorecard.project_id,
            frequency_score=scorecard.frequency_score,
            severity_score=scorecard.severity_score,
            alternatives_score=scorecard.alternatives_score,
            wtp_score=scorecard.wtp_score,
            market_potential_score=scorecard.market_potential_score,
            total_score=scorecard.total_score,
            framework_threshold=40,
            interpretation_result=scorecard.interpretation_result,
            evidence_quality=scorecard.evidence_quality,
            evidence_refs=scorecard.evidence_refs_jsonb or [],
            notes=scorecard.notes,
            updated_at=scorecard.updated_at,
        )

    @staticmethod
    def evaluate_role_coverage(
        db: Session, workspace_id: int, project_id: int
    ) -> RoleCoverageResponse:
        """
        Tính độ bao phủ vai trò người phỏng vấn (User, Buyer, Decision Maker, Influencer).
        Cảnh báo nếu thiếu Decision Maker trong B2B (F3.md §23).
        """
        stmt = select(CustomerInterviewSession).where(
            and_(
                CustomerInterviewSession.workspace_id == workspace_id,
                CustomerInterviewSession.project_id == project_id,
            )
        )
        sessions = list(db.scalars(stmt).all())

        user_c = sum(1 for s in sessions if s.role == CustomerRoleEnum.USER.value)
        buyer_c = sum(1 for s in sessions if s.role == CustomerRoleEnum.BUYER.value)
        dm_c = sum(1 for s in sessions if s.role == CustomerRoleEnum.DECISION_MAKER.value)
        inf_c = sum(1 for s in sessions if s.role == CustomerRoleEnum.INFLUENCER.value)
        total = len(sessions)

        has_dm_gap = (total >= 3 and dm_c == 0)
        warning_msg = None
        if has_dm_gap:
            warning_msg = "⚠ DECISION MAKER EVIDENCE GAP: Đã có phỏng vấn từ User/Buyer nhưng chưa có ý kiến từ người nắm ngân sách (Decision Maker)."

        return RoleCoverageResponse(
            project_id=project_id,
            user_count=user_c,
            buyer_count=buyer_c,
            decision_maker_count=dm_c,
            influencer_count=inf_c,
            total_interviews=total,
            has_decision_maker_gap=has_dm_gap,
            warning_message=warning_msg,
            coverage_status={
                "USER": user_c > 0,
                "BUYER": buyer_c > 0,
                "DECISION_MAKER": dm_c > 0,
                "INFLUENCER": inf_c > 0,
            }
        )

    @staticmethod
    async def run_data_autopsy(
        db: Session, workspace_id: int, project_id: int
    ) -> DataAutopsyResponse:
        """
        AI khám nghiệm toàn bộ trích dẫn phỏng vấn để bóc tách Pattern / Niche / Shock.
        """
        quotes_stmt = select(VerbatimQuote).where(
            and_(
                VerbatimQuote.workspace_id == workspace_id,
                VerbatimQuote.project_id == project_id,
            )
        )
        quotes = list(db.scalars(quotes_stmt).all())

        sessions_stmt = select(CustomerInterviewSession).where(
            and_(
                CustomerInterviewSession.workspace_id == workspace_id,
                CustomerInterviewSession.project_id == project_id,
            )
        )
        sessions = list(db.scalars(sessions_stmt).all())

        if not quotes:
            return DataAutopsyResponse(
                project_id=project_id,
                total_interviews=len(sessions),
                total_quotes=0,
                patterns=[],
                niches=[],
                shocks=[],
                recommended_problem_statement=None,
                recommended_jtbd=None,
            )

        quotes_text = "\n".join([
            f"- [{q.buying_signal_level or 'GENERAL'}] Quote: \"{q.raw_quote}\" | Interpretation: {q.interpretation or 'N/A'} | Tags: {','.join(q.tags_jsonb or [])}"
            for q in quotes
        ])

        user_prompt = f"Total Interviews: {len(sessions)}\nTotal Quotes: {len(quotes)}\n\nQuotes List:\n{quotes_text}"

        try:
            raw_res = await run_worker_prompt(
                system_prompt=AUTOPSY_PROMPT,
                user_prompt=user_prompt,
                temperature=0.2,
            )
            parsed = _extract_json(raw_res)

            # Lưu các pattern vào database
            for pat in parsed.get("patterns", []):
                db.add(PainPattern(
                    workspace_id=workspace_id,
                    project_id=project_id,
                    cluster_type=AutopsyClusterType.PATTERN.value,
                    title=pat.get("title", "Detected Pattern"),
                    description=pat.get("summary"),
                    frequency_count=pat.get("frequency_count", 1),
                ))

            for nic in parsed.get("niches", []):
                db.add(PainPattern(
                    workspace_id=workspace_id,
                    project_id=project_id,
                    cluster_type=AutopsyClusterType.NICHE.value,
                    title=nic.get("title", "Detected Niche"),
                    description=nic.get("summary"),
                    frequency_count=nic.get("frequency_count", 1),
                ))

            for shk in parsed.get("shocks", []):
                db.add(PainPattern(
                    workspace_id=workspace_id,
                    project_id=project_id,
                    cluster_type=AutopsyClusterType.SHOCK.value,
                    title=shk.get("title", "Detected Shock"),
                    description=shk.get("summary"),
                    frequency_count=shk.get("frequency_count", 1),
                ))

            db.commit()

            return DataAutopsyResponse(
                project_id=project_id,
                total_interviews=len(sessions),
                total_quotes=len(quotes),
                patterns=parsed.get("patterns", []),
                niches=parsed.get("niches", []),
                shocks=parsed.get("shocks", []),
                recommended_problem_statement=parsed.get("recommended_problem_statement"),
                recommended_jtbd=parsed.get("recommended_jtbd"),
            )
        except Exception as e:
            logger.error(f"Failed to run Data Autopsy: {e}")
            raise
