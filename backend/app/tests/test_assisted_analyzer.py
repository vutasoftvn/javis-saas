import json
import uuid
from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException

from app.modules.strategy.models import Project, EvidenceItem, StrategyCanvas, StrategyRevision
from app.modules.strategy.assisted_analyzer import AssistedAnalyzerService


def test_export_analysis_prompt():
    ws_id = uuid.uuid4()
    user_id = uuid.uuid4()
    proj_id = uuid.uuid4()

    db = MagicMock()
    proj = Project(
        id=proj_id,
        workspace_id=ws_id,
        brain_id=uuid.uuid4(),
        title="Dự án mCOSA V12",
        project_type="STRATEGIC",
        phase="Phase 1",
    )
    ev = EvidenceItem(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        title="Báo cáo thị trường SaaS 2026",
        summary="Thị trường tăng trưởng 25% năm",
        source_type="market_report",
        reliability="high",
        created_by=user_id,
    )
    db.query.return_value.filter.return_value.first.return_value = proj
    db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [ev]

    service = AssistedAnalyzerService(db=db, workspace_id=ws_id, user_id=user_id)
    res = service.export_analysis_prompt(project_id=proj_id)

    assert "ChatGPT Terra" in res["prompt_text"]
    assert "Dự án mCOSA V12" in res["prompt_text"]
    assert "Báo cáo thị trường SaaS 2026" in res["prompt_text"]
    assert res["evidence_count"] == 1


def test_import_analysis_result_valid_json():
    ws_id = uuid.uuid4()
    user_id = uuid.uuid4()
    proj_id = uuid.uuid4()

    sample_json = {
        "schema_version": "1.0",
        "assumptions": ["Nhu cầu cao"],
        "unknowns": ["Giá tối ưu"],
        "pestel": [
            {"factor": "Political", "statement": "Chính sách ưu đãi AI", "impact": "high", "horizon": "medium", "confidence": "high", "evidence_status": "verified"}
        ],
        "swot": [
            {"category": "strength", "statement": "Công nghệ vượt trội", "impact": "high", "likelihood": "high", "confidence": "high", "evidence_status": "verified"}
        ],
        "tows": [
            {"quadrant": "SO", "title": "Chiếm lĩnh thị trường", "tradeoffs": "Chi phí đầu tư", "expected_impact": "high", "confidence": "high"}
        ],
        "strategic_options": [
            {"option_no": 1, "title": "Tập trung B2B", "rationale": "Lợi nhuận cao", "risk": "Chu kỳ bán hàng dài"}
        ],
        "recommended_goals": [
            {"title": "Đạt 100 khách hàng", "target": "100", "krs": ["KR1", "KR2"]}
        ],
        "risks": ["Thiếu nhân sự"],
        "confidence_score": 0.95,
        "questions_for_founder": ["Ngân sách marketing là bao nhiêu?"]
    }

    raw_input = f"```json\n{json.dumps(sample_json)}\n```"

    db = MagicMock()
    # Mock brain query, canvas query, latest revision query
    db.query.return_value.filter.return_value.first.return_value = None

    service = AssistedAnalyzerService(db=db, workspace_id=ws_id, user_id=user_id)
    res = service.import_analysis_result(raw_input=raw_input, project_id=proj_id)

    assert res["status"] == "success"
    assert res["pestel_count"] == 1
    assert res["swot_count"] == 1
    assert res["tows_count"] == 1
    assert res["options_count"] == 1
    assert res["goals_count"] == 1
    assert len(res["questions_for_founder"]) == 1
    assert db.commit.called


def test_import_analysis_result_invalid_json():
    ws_id = uuid.uuid4()
    user_id = uuid.uuid4()
    service = AssistedAnalyzerService(db=MagicMock(), workspace_id=ws_id, user_id=user_id)

    with pytest.raises(HTTPException) as exc:
        service.import_analysis_result(raw_input="Đây không phải là JSON")
    assert exc.value.status_code == 422
