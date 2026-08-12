/// Realtime-voice-local mirror of the Hologram Hub's runtime states
/// (mCOSA V12.1 §11-12), owned by this module so [VoiceSessionController]
/// doesn't have to import `hologram_hub`'s widget file just to report state.
///
/// `HologramHubController` is the one responsible for translating this into
/// its own `HologramRuntimeState` at the point it consumes the controller -
/// this inverts what used to be a direct dependency from realtime_voice into
/// hologram_hub internals.
enum RealtimeHologramState {
  idle,
  listening,
  thinking,
  retrieving,
  acting,
  speaking,
  error,
}
