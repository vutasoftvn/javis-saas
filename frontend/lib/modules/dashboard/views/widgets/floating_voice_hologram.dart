import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../../core/shell/chat_panel_controller.dart';

/// Icon robot nổi, kéo được — thay cho orb voice cũ. Tap mở/đóng khung chat
/// nổi (`DraggableChatPanel`) qua `ChatPanelController`. Voice/STT chưa nối
/// lại vào đây — triển khai ở 1 tính năng riêng sau này (xem spec
/// `docs/superpowers/specs/2026-09-03-robot-icon-draggable-chat-design.md`).
class FloatingVoiceHologram extends StatefulWidget {
  const FloatingVoiceHologram({super.key});

  @override
  State<FloatingVoiceHologram> createState() => _FloatingVoiceHologramState();
}

class _FloatingVoiceHologramState extends State<FloatingVoiceHologram> {
  static const _diameter = 56.0;
  static const _rightPadding = 48.0;
  static const _bottomPadding = 120.0;
  Offset? _position;

  ChatPanelController get _panelController => Get.find<ChatPanelController>();

  @override
  Widget build(BuildContext context) {
    return Positioned.fill(
      child: LayoutBuilder(
        builder: (context, constraints) {
          final double maxX = (constraints.maxWidth - _diameter).clamp(
            0.0,
            double.infinity,
          );
          final double maxY = (constraints.maxHeight - _diameter).clamp(
            0.0,
            double.infinity,
          );
          final defaultPosition = Offset(
            (constraints.maxWidth - _diameter - _rightPadding).clamp(0.0, maxX),
            (constraints.maxHeight - _diameter - _bottomPadding).clamp(
              0.0,
              maxY,
            ),
          );
          final Offset currentPos = _position ?? defaultPosition;
          final Offset boundedPosition = Offset(
            currentPos.dx.clamp(0.0, maxX),
            currentPos.dy.clamp(0.0, maxY),
          );

          final robotButton = GestureDetector(
            onPanStart: (_) => setState(() => _position = boundedPosition),
            onPanUpdate: (details) => setState(() {
              _position = Offset(
                (boundedPosition.dx + details.delta.dx).clamp(0.0, maxX),
                (boundedPosition.dy + details.delta.dy).clamp(0.0, maxY),
              );
            }),
            onTap: () => _panelController.toggle(),
            child: Tooltip(
              message: 'Mở/đóng chat với COSA',
              child: Obx(() {
                final isOpen = _panelController.isOpen.value;
                return Container(
                  key: const Key('floating_voice_hologram'),
                  width: _diameter,
                  height: _diameter,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: const LinearGradient(
                      colors: [Color(0xFF6366F1), Color(0xFF8B5CF6)],
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: const Color(
                          0xFF6366F1,
                        ).withValues(alpha: isOpen ? 0.6 : 0.35),
                        blurRadius: 16,
                        spreadRadius: isOpen ? 2 : 0,
                      ),
                    ],
                  ),
                  child: const Icon(
                    Icons.smart_toy_rounded,
                    color: Colors.white,
                    size: 28,
                  ),
                );
              }),
            ),
          );

          return Stack(
            children: [
              Positioned(
                left: boundedPosition.dx,
                top: boundedPosition.dy,
                child: robotButton,
              ),
            ],
          );
        },
      ),
    );
  }
}
