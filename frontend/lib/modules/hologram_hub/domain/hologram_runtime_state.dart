/// Domain layer — exported so mixins and widgets can import without depending
/// on the presentation layer (miva_hologram_core.dart).
///
/// miva_hologram_core.dart re-exports this enum to preserve backward compat.
enum HologramRuntimeState {
  genesis,
  idle,
  listening,
  thinking,
  retrieving,
  acting,
  speaking,
  waitingApproval,
  success,
  warning,
  error,
  offline,
}
