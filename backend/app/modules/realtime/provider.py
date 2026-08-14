from abc import ABC, abstractmethod
from typing import Any, Optional

from app.modules.realtime.token_service import generate_livekit_token
from app.modules.realtime.transport_resolver import (
    DeviceType,
    RealtimeTransportResolver,
    TransportDecision,
    TransportSetting,
)


class RealtimeProvider(ABC):
    """Abstract interface for voice/realtime transport providers (LiveKit, Cloud, Mock)."""

    @abstractmethod
    def generate_token(
        self,
        workspace_id: int,
        user_id: int,
        user_name: str,
        room_name: Optional[str] = None,
    ) -> str:
        """Generate access token for connecting to the realtime voice/audio room."""
        ...

    @abstractmethod
    def resolve_transport(
        self,
        *,
        device_type: DeviceType,
        setting: TransportSetting = "auto",
        local_available: bool = False,
    ) -> TransportDecision:
        """Resolve optimal transport mechanism (local vs cloud LiveKit)."""
        ...


class LiveKitRealtimeProvider(RealtimeProvider):
    """Production Realtime Provider using LiveKit + Gemini voice agents."""

    def __init__(self) -> None:
        self._resolver = RealtimeTransportResolver()

    def generate_token(
        self,
        workspace_id: int,
        user_id: int,
        user_name: str,
        room_name: Optional[str] = None,
    ) -> str:
        return generate_livekit_token(
            workspace_id=workspace_id,
            user_id=user_id,
            user_name=user_name,
            room_name=room_name,
        )

    def resolve_transport(
        self,
        *,
        device_type: DeviceType,
        setting: TransportSetting = "auto",
        local_available: bool = False,
    ) -> TransportDecision:
        return self._resolver.resolve(
            device_type=device_type,
            setting=setting,
            local_available=local_available,
        )
