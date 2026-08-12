import os
from datetime import timedelta

from livekit import api as lk_api


def generate_livekit_token(
    *,
    room_name: str,
    identity: str,
    display_name: str,
    ttl_seconds: int = 4 * 3600,
) -> str:
    """Issue a short-lived LiveKit room-join token (mCOSA V12.1 §41).

    Signed with LIVEKIT_API_SECRET, not app.core.security's JWT_SECRET -
    LiveKit validates this token itself against its own key pair, so the
    claim shape (video grants, sub/iss) must match LiveKit's spec exactly,
    which is why we delegate to the official SDK instead of hand-rolling it.
    """
    grants = lk_api.VideoGrants(
        room_join=True,
        room=room_name,
        can_publish=True,
        can_subscribe=True,
        can_publish_data=True,
    )
    token = (
        lk_api.AccessToken(os.environ["LIVEKIT_API_KEY"], os.environ["LIVEKIT_API_SECRET"])
        .with_identity(identity)
        .with_name(display_name)
        .with_ttl(timedelta(seconds=ttl_seconds))
        .with_grants(grants)
    )
    return token.to_jwt()
