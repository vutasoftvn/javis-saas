from app.modules.realtime.transport_resolver import RealtimeTransportResolver


def test_mobile_always_resolves_to_cloud_regardless_of_setting():
    resolver = RealtimeTransportResolver()

    for setting in ("auto", "local", "cloud"):
        for local_available in (True, False):
            decision = resolver.resolve(device_type="mobile", setting=setting, local_available=local_available)
            assert decision.transport == "livekit_cloud"
            assert decision.fallback is False


def test_web_always_resolves_to_cloud():
    resolver = RealtimeTransportResolver()

    decision = resolver.resolve(device_type="web", setting="local", local_available=True)

    assert decision.transport == "livekit_cloud"


def test_desktop_auto_selects_local_when_available():
    resolver = RealtimeTransportResolver()

    decision = resolver.resolve(device_type="desktop", setting="auto", local_available=True)

    assert decision.transport == "livekit_local"
    assert decision.fallback is False


def test_desktop_auto_falls_back_to_cloud_when_local_unavailable():
    """Spec §127 hybrid failure mode - AUTO must degrade to cloud, not fail
    the session, when local LiveKit is down."""
    resolver = RealtimeTransportResolver()

    decision = resolver.resolve(device_type="desktop", setting="auto", local_available=False)

    assert decision.transport == "livekit_cloud"
    assert decision.fallback is True


def test_desktop_explicit_local_setting_falls_back_when_unavailable():
    resolver = RealtimeTransportResolver()

    decision = resolver.resolve(device_type="desktop", setting="local", local_available=False)

    assert decision.transport == "livekit_cloud"
    assert decision.fallback is True


def test_desktop_explicit_local_setting_used_when_available():
    resolver = RealtimeTransportResolver()

    decision = resolver.resolve(device_type="desktop", setting="local", local_available=True)

    assert decision.transport == "livekit_local"
    assert decision.fallback is False


def test_desktop_explicit_cloud_setting_ignores_local_availability():
    resolver = RealtimeTransportResolver()

    decision = resolver.resolve(device_type="desktop", setting="cloud", local_available=True)

    assert decision.transport == "livekit_cloud"
    assert decision.fallback is False


def test_default_setting_is_auto():
    resolver = RealtimeTransportResolver()

    decision = resolver.resolve(device_type="desktop", local_available=True)

    assert decision.transport == "livekit_local"
