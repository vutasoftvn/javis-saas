import 'package:flutter/material.dart';
import 'command_bar/chat_input_pill_bar.dart';
import 'command_bar/hologram_palette_helper.dart';
import 'command_bar/two_action_icons_bar.dart';
import 'miva_hologram_core.dart';

class MobileCommandBar extends StatefulWidget {
  final HologramRuntimeState runtimeState;
  final bool isChatInputActive;
  final bool isVoiceListening;
  final bool isConversationModeActive;
  final VoidCallback onOpenChat;
  final VoidCallback onCloseChat;
  final VoidCallback onVoiceTap;
  final VoidCallback? onVoiceLongPress;
  final Function(String query) onSubmit;

  const MobileCommandBar({
    super.key,
    this.runtimeState = HologramRuntimeState.idle,
    required this.isChatInputActive,
    this.isVoiceListening = false,
    this.isConversationModeActive = false,
    required this.onOpenChat,
    required this.onCloseChat,
    required this.onVoiceTap,
    this.onVoiceLongPress,
    required this.onSubmit,
  });

  @override
  State<MobileCommandBar> createState() => _MobileCommandBarState();
}

class _MobileCommandBarState extends State<MobileCommandBar>
    with TickerProviderStateMixin {
  final TextEditingController _controller = TextEditingController();
  final FocusNode _focusNode = FocusNode();
  late AnimationController _pulseAnimController;
  late AnimationController _hueController;
  late AnimationController _waveAnimController;

  @override
  void initState() {
    super.initState();
    _pulseAnimController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2200),
    )..repeat(reverse: true);

    _hueController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 16),
    )..repeat();

    _waveAnimController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    )..repeat();
  }

  @override
  void didUpdateWidget(MobileCommandBar oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.isChatInputActive && !oldWidget.isChatInputActive) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        _focusNode.requestFocus();
      });
    } else if (!widget.isChatInputActive && oldWidget.isChatInputActive) {
      _focusNode.unfocus();
      _controller.clear();
    }
  }

  @override
  void dispose() {
    _pulseAnimController.dispose();
    _hueController.dispose();
    _waveAnimController.dispose();
    _controller.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  void _handleSubmitted(String value) {
    final text = value.trim();
    if (text.isEmpty) return;
    _controller.clear();
    widget.onSubmit(text);
  }

  HologramPalette _resolvePalette() {
    return resolveHologramPalette(
      runtimeState: widget.runtimeState,
      hueProgress: _hueController.value,
    );
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedSwitcher(
      duration: const Duration(milliseconds: 300),
      switchInCurve: Curves.easeOutCubic,
      switchOutCurve: Curves.easeInCubic,
      transitionBuilder: (child, animation) {
        return FadeTransition(
          opacity: animation,
          child: SlideTransition(
            position: Tween<Offset>(
              begin: const Offset(0, 0.15),
              end: Offset.zero,
            ).animate(animation),
            child: child,
          ),
        );
      },
      child: AnimatedBuilder(
        key: ValueKey(widget.isChatInputActive ? 'chat_input_mode' : 'two_icons_mode'),
        animation: Listenable.merge([
          _pulseAnimController,
          _hueController,
          _waveAnimController,
        ]),
        builder: (context, child) {
          final palette = _resolvePalette();
          final pulse = _pulseAnimController.value;

          if (widget.isChatInputActive) {
            return ChatInputPillBar(
              controller: _controller,
              focusNode: _focusNode,
              runtimeState: widget.runtimeState,
              isVoiceListening: widget.isVoiceListening,
              isConversationModeActive: widget.isConversationModeActive,
              onCloseChat: widget.onCloseChat,
              onVoiceTap: widget.onVoiceTap,
              onSubmit: _handleSubmitted,
              palette: palette,
              pulse: pulse,
            );
          } else {
            return TwoActionIconsBar(
              runtimeState: widget.runtimeState,
              isVoiceListening: widget.isVoiceListening,
              isConversationModeActive: widget.isConversationModeActive,
              onOpenChat: widget.onOpenChat,
              onVoiceTap: widget.onVoiceTap,
              onVoiceLongPress: widget.onVoiceLongPress,
              palette: palette,
              pulse: pulse,
              waveAnimController: _waveAnimController,
            );
          }
        },
      ),
    );
  }
}
