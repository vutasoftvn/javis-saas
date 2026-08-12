from dataclasses import dataclass
from typing import Literal

TransportSetting = Literal["auto", "local", "cloud"]
DeviceType = Literal["desktop", "mobile", "web"]


@dataclass(frozen=True)
class TransportDecision:
    transport: str  # "livekit_local" | "livekit_cloud"
    reason: str
    fallback: bool


class RealtimeTransportResolver:
    """Resolves LiveKit Local vs Cloud transport (mCOSA V12.2 §107-108).

    Pure/stateless: takes the device type, the voice-transport user
    preference, and whether a local LiveKit server is actually available,
    and returns a decision plus a human-readable reason. Mobile always
    resolves to cloud regardless of setting (spec §106) - only Desktop is
    ever eligible for local transport.
    """

    def resolve(
        self,
        *,
        device_type: DeviceType,
        setting: TransportSetting = "auto",
        local_available: bool = False,
    ) -> TransportDecision:
        if device_type != "desktop":
            return TransportDecision(
                transport="livekit_cloud",
                reason=f"device_type={device_type} always uses cloud transport (spec §106)",
                fallback=False,
            )

        if setting == "cloud":
            return TransportDecision(transport="livekit_cloud", reason="user setting is CLOUD", fallback=False)

        if setting == "local":
            if local_available:
                return TransportDecision(transport="livekit_local", reason="user setting is LOCAL", fallback=False)
            return TransportDecision(
                transport="livekit_cloud",
                reason="user setting is LOCAL but local LiveKit is unavailable",
                fallback=True,
            )

        # setting == "auto" (spec §108, §127 hybrid failure modes)
        if local_available:
            return TransportDecision(
                transport="livekit_local", reason="AUTO: local LiveKit healthy", fallback=False
            )
        return TransportDecision(
            transport="livekit_cloud",
            reason="AUTO: local LiveKit unavailable, falling back to cloud",
            fallback=True,
        )
