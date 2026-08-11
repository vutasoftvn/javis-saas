import uuid
from app.core.snowflake import generate_snowflake_id
from unittest.mock import MagicMock
import pytest

from app.modules.strategy.models import (
    PestelSignal,
    ModelRunAudit,
    ProjectPestelImpact,
    NextActionCandidate,
)
from app.modules.strategy.living_pestel_service import LivingPestelService


def test_ingest_pestel_signal_material_change():
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    proj_id = generate_snowflake_id()
    db = MagicMock()

    pestel_imp = ProjectPestelImpact(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        project_id=proj_id,
        pestel_item_id=generate_snowflake_id(),
        impact_type="NEGATIVE",
        impact_magnitude="HIGH",
    )

    def query_mock(model):
        m = MagicMock()
        m.join.return_value = m
        m.filter.return_value = m
        if model == ProjectPestelImpact:
            m.all.return_value = [pestel_imp]
        return m

    db.query.side_effect = query_mock

    service = LivingPestelService(db, ws_id, user_id)

    # Ingest HIGH magnitude signal -> material change -> CEO Exception Task
    res = service.ingest_signal(
        signal_title="Lãi suất điều hành tăng mạnh",
        pestel_category="ECONOMIC",
        magnitude="HIGH",
        signal_summary="Ngân hàng trung ương tăng lãi suất thêm 100 điểm cơ bản",
    )

    assert res["is_material_change"] is True
    assert res["ceo_exception_created"] is True
    assert res["signal"]["signal_title"] == "Lãi suất điều hành tăng mạnh"


def test_ingest_pestel_signal_filters_by_category():
    """Chỉ tạo CEO Exception cho impact có cùng PESTEL factor với tín hiệu (Spec §48)."""
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    db = MagicMock()

    def query_mock(model):
        m = MagicMock()
        m.join.return_value = m
        m.filter.return_value = m
        if model == ProjectPestelImpact:
            # Không có impact nào khớp factor "SOCIAL" -> danh sách rỗng
            m.all.return_value = []
        return m

    db.query.side_effect = query_mock

    service = LivingPestelService(db, ws_id, user_id)

    res = service.ingest_signal(
        signal_title="Xu hướng tiêu dùng thay đổi",
        pestel_category="SOCIAL",
        magnitude="HIGH",
    )

    assert res["is_material_change"] is True
    assert res["ceo_exception_created"] is False


def test_record_model_run_audit():
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    db = MagicMock()

    service = LivingPestelService(db, ws_id, user_id)

    res = service.record_model_run(
        model_profile="TERRA_V12",
        prompt_tokens=1200,
        completion_tokens=450,
        latency_ms=850,
        status_val="success",
    )

    assert res["model_profile"] == "TERRA_V12"
    assert res["prompt_tokens"] == 1200
    assert res["latency_ms"] == 850


def test_living_pestel_endpoints():
    from app.modules.strategy.living_pestel_router import (
        ingest_pestel_signal,
        get_pestel_signals,
        record_model_run_audit,
        get_model_runs_audit,
        PestelSignalIngest,
        ModelRunAuditCreate,
    )
    from app.tests.test_strategy_endpoints import mock_member

    ws_id = generate_snowflake_id()
    member = mock_member()
    db = MagicMock()

    signal = PestelSignal(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        signal_title="Quy định mới về AI compliance",
        pestel_category="LEGAL",
        magnitude="HIGH",
        is_material_change=True,
    )
    audit = ModelRunAudit(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        model_profile="DEEPSEEK_V3",
        prompt_tokens=500,
        completion_tokens=200,
        latency_ms=600,
    )

    from app.modules.platform.models import FeatureFlag

    def query_mock(model):
        m = MagicMock()
        m.join.return_value = m
        m.filter.return_value = m
        if model == PestelSignal:
            m.order_by.return_value.all.return_value = [signal]
        elif model == ModelRunAudit:
            m.order_by.return_value.limit.return_value.all.return_value = [audit]
        elif model == ProjectPestelImpact:
            m.all.return_value = []
        elif model == FeatureFlag:
            m.first.return_value = FeatureFlag(key="living_pestel_v12", enabled=True)
        return m

    db.query.side_effect = query_mock

    # 1. Ingest signal endpoint
    ingest_req = PestelSignalIngest(
        signal_title="Quy định mới về AI compliance",
        pestel_category="LEGAL",
        magnitude="HIGH",
    )
    ing_res = ingest_pestel_signal(ws_id, ingest_req, member, db)
    assert ing_res["is_material_change"] is True

    # 2. Get signals
    sig_res = get_pestel_signals(ws_id, member, db)
    assert len(sig_res["signals"]) == 1

    # 3. Record & Get model runs audit
    aud_req = ModelRunAuditCreate(model_profile="DEEPSEEK_V3", prompt_tokens=500, completion_tokens=200, latency_ms=600)
    aud_rec = record_model_run_audit(ws_id, aud_req, member, db)
    assert aud_rec["model_profile"] == "DEEPSEEK_V3"

    aud_list = get_model_runs_audit(ws_id, limit=20, member=member, db=db)
    assert len(aud_list["audits"]) == 1


def test_get_model_profiles_endpoint_does_not_import_missing_module():
    """Regression: GET /model-profiles từng import app.modules.strategy.model_profile_service
    (module không tồn tại) -> ModuleNotFoundError/500 trên mọi request. Test này gọi thẳng
    hàm router để đảm bảo endpoint thực thi được và không còn phụ thuộc module đó."""
    from app.modules.strategy.living_pestel_router import get_model_profiles
    from app.tests.test_strategy_endpoints import mock_member
    from app.modules.platform.models import FeatureFlag
    from app.modules.strategy.models import ModelProfileOverride

    ws_id = generate_snowflake_id()
    member = mock_member()
    db = MagicMock()

    def query_mock(model):
        m = MagicMock()
        m.filter.return_value = m
        if model == FeatureFlag:
            m.first.return_value = FeatureFlag(key="living_pestel_v12", enabled=True)
        elif model == ModelProfileOverride:
            m.all.return_value = []
        return m

    db.query.side_effect = query_mock

    res = get_model_profiles(ws_id, member, db)
    profiles = res["profiles"]
    assert len(profiles) == 3
    assert {p["profile"] for p in profiles} == {
        "STRATEGIC_ANALYZER", "CONVERSATION_ROUTER", "DEVELOPER_WORKER",
    }
    assert all("provider" in p and "model" in p for p in profiles)


def test_update_model_profile_endpoint_persists():
    """Regression: PUT /model-profiles/{id} từng là no-op không ghi DB."""
    from app.modules.strategy.living_pestel_router import update_model_profile, ModelProfileUpdate
    from app.tests.test_strategy_endpoints import mock_member
    from app.modules.platform.models import FeatureFlag
    from app.modules.strategy.models import ModelProfileOverride

    ws_id = generate_snowflake_id()
    member = mock_member()
    db = MagicMock()

    def query_mock(model):
        m = MagicMock()
        m.filter.return_value = m
        if model == FeatureFlag:
            m.first.return_value = FeatureFlag(key="living_pestel_v12", enabled=True)
        elif model == ModelProfileOverride:
            m.first.return_value = None  # chưa có override -> tạo mới
        return m

    db.query.side_effect = query_mock

    res = update_model_profile(
        "strategic_analyzer",
        ws_id,
        ModelProfileUpdate(display_name="Terra Chiến lược gia", temperature=0.4, is_active=False),
        member,
        db,
    )

    assert res["profile"] == "STRATEGIC_ANALYZER"
    assert res["display_name"] == "Terra Chiến lược gia"
    assert res["temperature"] == 0.4
    assert res["is_active"] is False
    assert db.add.called
    assert db.commit.called
