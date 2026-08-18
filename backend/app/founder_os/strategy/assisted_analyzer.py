import json
import logging
import re
from datetime import datetime
from typing import Optional, Dict, Any, List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.snowflake import generate_snowflake_id
from app.core.tenancy import get_project_scoped, get_canvas_scoped

from app.founder_os.strategy.models import (
    Project,
    EvidenceItem,
    StrategyCanvas,
    StrategyRevision,
    StrategyFoundation,
    CoreValue,
    ContextPack,
    StrategyAnalysis,
    PestelItem,
    SwotItem,
    TowsOption,
    AnalysisImport,
)
from app.platform.vault.models import Brain

logger = logging.getLogger(__name__)


class AssistedAnalyzerService:
    def __init__(self, db: Session, workspace_id: int, user_id: int):
        self.db = db
        self.workspace_id = workspace_id
        self.user_id = user_id

    def export_analysis_prompt(
        self,
        project_id: Optional[int] = None,
        canvas_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Build structured export package and prompt for ChatGPT Terra (spec §41, §42)."""
        project = None
        if project_id:
            project = get_project_scoped(self.db, project_id, self.workspace_id)

        # Get existing evidence items
        evidence_items = (
            self.db.query(EvidenceItem)
            .filter(EvidenceItem.workspace_id == self.workspace_id)
            .order_by(EvidenceItem.captured_at.desc())
            .limit(20)
            .all()
        )

        evidence_summary_list = []
        for ev in evidence_items:
            evidence_summary_list.append(
                f"- [{ev.source_type.upper()}] {ev.title} (Độ tin cậy: {ev.reliability}): {ev.summary}"
            )
        evidence_text = "\n".join(evidence_summary_list) if evidence_summary_list else "Chưa có bằng chứng cụ thể."

        # Get strategy foundation if canvas is provided
        foundation_text = "Chưa thiết lập"
        if canvas_id:
            canvas = get_canvas_scoped(self.db, canvas_id, self.workspace_id)
            latest_revision = (
                self.db.query(StrategyRevision)
                .filter(StrategyRevision.canvas_id == canvas.id)
                .order_by(StrategyRevision.revision_no.desc())
                .first()
            )
            if latest_revision:
                foundation = (
                    self.db.query(StrategyFoundation)
                    .filter(StrategyFoundation.strategy_revision_id == latest_revision.id)
                    .first()
                )
                if foundation:
                    values = (
                        self.db.query(CoreValue)
                        .filter(CoreValue.foundation_id == foundation.id)
                        .order_by(CoreValue.slot_no.asc())
                        .all()
                    )
                    v_str = ", ".join([f"{v.slot_no}. {v.title} ({v.decision_rule})" for v in values])
                    foundation_text = (
                        f"Tầm nhìn: {foundation.vision or 'N/A'}\n"
                        f"Sứ mệnh: {foundation.mission or 'N/A'}\n"
                        f"Giá trị cốt lõi (1-1-3): {v_str or 'N/A'}"
                    )

        proj_title = project.title if project else "Toàn bộ Doanh nghiệp (Company-level Strategy)"
        proj_type = (project.project_type if project else "STRATEGIC") or "STRATEGIC"
        proj_phase = project.phase if project else "Khởi động"

        prompt_text = f"""# YÊU CẦU PHÂN TÍCH CHIẾN LƯỢC CHO CHATGPT TERRA (COSA OS)

Bạn là **ChatGPT Terra** — Chuyên gia Phân tích Chiến lược Cấp cao trong COSA OS.
Nhiệm vụ của bạn là thực hiện phân tích ma trận chiến lược toàn diện theo mô hình **Strategic Canvas 1-1-3**:
- PESTEL: 6 yếu tố vĩ mô × 3 tín hiệu nổi bật nhất.
- SWOT: 4 góc nhìn × 3 yếu tố cốt lõi.
- TOWS: 4 nhóm kết hợp (SO, ST, WO, WT) × các phương án hành động.
- 3 Lựa chọn Chiến lược (Strategic Options).
- 3 Mục tiêu Đề xuất (Recommended Goals) cho chu kỳ 12 tuần.

## THÔNG TIN ĐẦU VÀO
- **Dự án**: {proj_title}
- **Loại dự án**: {proj_type}
- **Giai đoạn**: {proj_phase}
- **Nền tảng Chiến lược Doanh nghiệp**:
{foundation_text}

- **Bằng chứng & Dữ liệu Thị trường hiện có**:
{evidence_text}

---

## ĐỊNH DẠNG ĐẦU RA BẮT BUỘC
Vui lòng phân tích và trả về DUY NHẤT một khối mã JSON hợp lệ theo cấu trúc sau (không kèm lời chào hay văn bản thừa bên ngoài khối JSON):

```json
{{
  "schema_version": "1.0",
  "assumptions": [
    "Giả thuyết 1 về nhu cầu thị trường",
    "Giả thuyết 2 về rào cản gia nhập"
  ],
  "unknowns": [
    "Điểm chưa chắc chắn 1 cần xác thực thêm"
  ],
  "pestel": [
    {{
      "factor": "Political",
      "statement": "Mô tả tín hiệu chính sách/chính trị",
      "impact": "high",
      "horizon": "medium",
      "confidence": "high",
      "evidence_status": "verified"
    }},
    {{
      "factor": "Economic",
      "statement": "Mô tả tín hiệu kinh tế",
      "impact": "high",
      "horizon": "short",
      "confidence": "high",
      "evidence_status": "inferred"
    }}
  ],
  "swot": [
    {{
      "category": "strength",
      "statement": "Điểm mạnh cốt lõi",
      "impact": "high",
      "likelihood": "high",
      "confidence": "high",
      "evidence_status": "verified"
    }},
    {{
      "category": "opportunity",
      "statement": "Cơ hội thị trường",
      "impact": "high",
      "likelihood": "high",
      "confidence": "high",
      "evidence_status": "inferred"
    }}
  ],
  "tows": [
    {{
      "quadrant": "SO",
      "title": "Tên chiến lược Tận dụng Cơ hội",
      "tradeoffs": "Đánh đổi về nguồn lực",
      "expected_impact": "high",
      "confidence": "high"
    }}
  ],
  "strategic_options": [
    {{
      "option_no": 1,
      "title": "Tập trung thâm nhập ngách",
      "rationale": "Lý do lựa chọn",
      "risk": "Rủi ro chính"
    }},
    {{
      "option_no": 2,
      "title": "Mở rộng hệ sinh thái sản phẩm",
      "rationale": "Lý do lựa chọn",
      "risk": "Rủi ro chính"
    }},
    {{
      "option_no": 3,
      "title": "Tối ưu hóa biên lợi nhuận & tự động hóa",
      "rationale": "Lý do lựa chọn",
      "risk": "Rủi ro chính"
    }}
  ],
  "recommended_goals": [
    {{
      "title": "Đạt Product-Market Fit cho phân khúc cốt lõi",
      "target": "10 khách hàng trả phí đầu tiên",
      "krs": ["15 cuộc phỏng vấn chuyên sâu", "Tỷ lệ kích hoạt > 70%"]
    }}
  ],
  "risks": [
    "Rủi ro thiếu tập trung nguồn lực founder"
  ],
  "confidence_score": 0.9,
  "questions_for_founder": [
    "Câu hỏi 1 cần Founder làm rõ trước khi chốt kế hoạch 12 tuần?"
  ]
}}
```
"""
        return {
            "export_format": "markdown",
            "prompt_text": prompt_text,
            "project_id": str(project_id) if project_id else None,
            "canvas_id": str(canvas_id) if canvas_id else None,
            "evidence_count": len(evidence_items),
            "schema_version": "1.0",
        }

    def import_analysis_result(
        self,
        raw_input: str,
        project_id: Optional[int] = None,
        canvas_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Validate, persist and convert ChatGPT Terra JSON output into strategy entities."""
        if not raw_input or not raw_input.strip():
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Nội dung import không được để trống")

        cleaned = raw_input.strip()
        # Extract JSON from markdown code block if present
        if "```json" in cleaned:
            match = re.search(r"```json\s*(.*?)\s*```", cleaned, re.DOTALL)
            if match:
                cleaned = match.group(1).strip()
        elif "```" in cleaned:
            match = re.search(r"```\s*(.*?)\s*```", cleaned, re.DOTALL)
            if match:
                cleaned = match.group(1).strip()

        try:
            parsed = json.loads(cleaned)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Dữ liệu không phải JSON hợp lệ: {exc}",
            )

        if not isinstance(parsed, dict):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Cấu trúc JSON không hợp lệ (phải là Object JSON)",
            )

        # Basic schema validation
        pestel_list = parsed.get("pestel", [])
        swot_list = parsed.get("swot", [])
        tows_list = parsed.get("tows", [])
        options_list = parsed.get("strategic_options", [])
        goals_list = parsed.get("recommended_goals", [])

        if not any([pestel_list, swot_list, tows_list, options_list, goals_list]):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="JSON không chứa các phần tử chiến lược bắt buộc (pestel/swot/tows/options)",
            )

        # 1. Resolve or create Strategy Canvas & Revision
        brain = self.db.query(Brain).filter(Brain.workspace_id == self.workspace_id).first()
        brain_id = brain.id if brain else generate_snowflake_id()

        canvas = None
        if canvas_id:
            canvas = get_canvas_scoped(self.db, canvas_id, self.workspace_id)
        else:
            canvas = (
                self.db.query(StrategyCanvas)
                .filter(StrategyCanvas.workspace_id == self.workspace_id)
                .first()
            )
            if not canvas:
                canvas = StrategyCanvas(
                    id=generate_snowflake_id(),
                    workspace_id=self.workspace_id,
                    brain_id=brain_id,
                    name="Strategic Canvas",
                    description="Auto-generated canvas from Terra Import",
                    status="draft",
                    created_by=self.user_id,
                )
                self.db.add(canvas)
                self.db.flush()

        # Find latest revision or create new
        latest_rev = (
            self.db.query(StrategyRevision)
            .filter(StrategyRevision.canvas_id == canvas.id)
            .order_by(StrategyRevision.revision_no.desc())
            .first()
        )
        rev_no = (latest_rev.revision_no + 1) if latest_rev else 1

        revision = StrategyRevision(
            id=generate_snowflake_id(),
            canvas_id=canvas.id,
            revision_no=rev_no,
            status="draft",
            parent_revision_id=latest_rev.id if latest_rev else None,
            created_by=self.user_id,
        )
        self.db.add(revision)
        self.db.flush()

        # 2. Create Context Pack
        context_pack = ContextPack(
            id=generate_snowflake_id(),
            workspace_id=self.workspace_id,
            strategy_revision_id=revision.id,
            business_context={"assumptions": parsed.get("assumptions", []), "unknowns": parsed.get("unknowns", [])},
            status="ready_for_review",
        )
        self.db.add(context_pack)
        self.db.flush()

        # 3. Create StrategyAnalysis containers
        analysis_pestel = StrategyAnalysis(
            id=generate_snowflake_id(),
            workspace_id=self.workspace_id,
            context_pack_id=context_pack.id,
            kind="PESTEL",
            status="draft",
            created_by=self.user_id,
        )
        analysis_swot = StrategyAnalysis(
            id=generate_snowflake_id(),
            workspace_id=self.workspace_id,
            context_pack_id=context_pack.id,
            kind="SWOT",
            status="draft",
            created_by=self.user_id,
        )
        analysis_tows = StrategyAnalysis(
            id=generate_snowflake_id(),
            workspace_id=self.workspace_id,
            context_pack_id=context_pack.id,
            kind="TOWS",
            status="draft",
            created_by=self.user_id,
        )
        self.db.add_all([analysis_pestel, analysis_swot, analysis_tows])
        self.db.flush()

        # 4. Insert Pestel items
        created_pestel = 0
        for p in pestel_list:
            factor = p.get("factor", "Political")
            stmt = p.get("statement", "")
            if stmt:
                p_item = PestelItem(
                    id=generate_snowflake_id(),
                    workspace_id=self.workspace_id,
                    analysis_id=analysis_pestel.id,
                    factor=factor,
                    statement=stmt,
                    impact=p.get("impact", "high"),
                    horizon=p.get("horizon", "medium"),
                    confidence=p.get("confidence", "high"),
                    evidence_status=p.get("evidence_status", "inferred"),
                )
                self.db.add(p_item)
                created_pestel += 1

        # 5. Insert SWOT items
        created_swot = 0
        for s in swot_list:
            cat = s.get("category", "strength")
            stmt = s.get("statement", "")
            if stmt:
                s_item = SwotItem(
                    id=generate_snowflake_id(),
                    workspace_id=self.workspace_id,
                    analysis_id=analysis_swot.id,
                    category=cat,
                    statement=stmt,
                    impact=s.get("impact", "high"),
                    likelihood=s.get("likelihood", "high"),
                    confidence=s.get("confidence", "high"),
                    evidence_status=s.get("evidence_status", "inferred"),
                )
                self.db.add(s_item)
                created_swot += 1

        # 6. Insert TOWS options
        created_tows = 0
        for t in tows_list:
            quad = t.get("quadrant", "SO")
            title = t.get("title", "")
            if title:
                t_item = TowsOption(
                    id=generate_snowflake_id(),
                    workspace_id=self.workspace_id,
                    analysis_id=analysis_tows.id,
                    quadrant=quad,
                    title=title,
                    tradeoffs=t.get("tradeoffs", "Cân nhắc phân bổ nguồn lực"),
                    expected_impact=t.get("expected_impact", "high"),
                    confidence=t.get("confidence", "high"),
                    status="draft",
                )
                self.db.add(t_item)
                created_tows += 1

        # 7. Record AnalysisImport audit log
        import_record = AnalysisImport(
            id=generate_snowflake_id(),
            workspace_id=self.workspace_id,
            project_id=project_id,
            strategy_revision_id=revision.id,
            raw_input=raw_input,
            parsed_json=parsed,
            schema_version=parsed.get("schema_version", "1.0"),
            imported_by=self.user_id,
            created_at=datetime.utcnow(),
        )
        self.db.add(import_record)

        self.db.commit()

        return {
            "status": "success",
            "import_id": str(import_record.id),
            "canvas_id": str(canvas.id),
            "revision_id": str(revision.id),
            "revision_no": revision.revision_no,
            "pestel_count": created_pestel,
            "swot_count": created_swot,
            "tows_count": created_tows,
            "options_count": len(options_list),
            "goals_count": len(goals_list),
            "strategic_options": options_list,
            "recommended_goals": goals_list,
            "questions_for_founder": parsed.get("questions_for_founder", []),
        }
