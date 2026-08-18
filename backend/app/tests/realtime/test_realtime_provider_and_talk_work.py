from unittest.mock import patch
import pytest
from app.integrations.realtime.provider import LiveKitRealtimeProvider, RealtimeProvider
from app.platform.license.talk_work_router import TalkWorkRouter, TalkWorkMode


def test_livekit_realtime_provider_transport_and_token():
    provider = LiveKitRealtimeProvider()
    assert isinstance(provider, RealtimeProvider)

    # 1. Transport resolution test (mobile -> cloud)
    decision = provider.resolve_transport(device_type="mobile", setting="local")
    assert decision.transport == "livekit_cloud"

    # 2. Token generation test
    with patch("app.integrations.realtime.provider.generate_livekit_token", return_value="mock_jwt_token_123"):
        token = provider.generate_token(workspace_id=1, user_id=2, user_name="Founder")
        assert token == "mock_jwt_token_123"


def test_talk_work_router_classification():
    # 1. Conversational TALK
    res_talk = TalkWorkRouter.classify_talk_vs_work("Xin chào bạn nhé")
    assert res_talk["mode"] == TalkWorkMode.TALK
    assert res_talk["target_agent"] == "realtime_companion"

    # 2. Operational WORK (Company mission)
    res_work = TalkWorkRouter.classify_talk_vs_work("Hãy chuẩn bị kế hoạch launch beta quý này")
    assert res_work["mode"] == TalkWorkMode.WORK
    assert res_work["target_agent"] == "chief_of_staff"

    # 3. State normalization
    assert TalkWorkRouter.normalize_mission_state("AWAITING_APPROVAL") == "waiting_approval"
    assert TalkWorkRouter.normalize_mission_state("in_progress") == "running"
    assert TalkWorkRouter.normalize_mission_state("completed") == "completed"
