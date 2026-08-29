import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:frontend/modules/hologram_hub/controllers/hologram_hub_controller.dart';

class HubChatHeader extends StatelessWidget {
  final HologramHubController controller;

  const HubChatHeader({super.key, required this.controller});

  Color _getBadgeColor(HologramRuntimeState state, bool isListening) {
    if (isListening) return const Color(0xFF14B8A6);
    switch (state) {
      case HologramRuntimeState.thinking:
        return const Color(0xFF818CF8);
      case HologramRuntimeState.speaking:
        return const Color(0xFF00FFB2);
      case HologramRuntimeState.error:
        return const Color(0xFFEF4444);
      case HologramRuntimeState.listening:
        return const Color(0xFF14B8A6);
      default:
        return const Color(0xFF10B981);
    }
  }

  String _getBadgeText(HologramRuntimeState state, bool isListening) {
    if (isListening) return '● ĐANG LẮNG NGHE';
    switch (state) {
      case HologramRuntimeState.thinking:
        return '● ĐANG XỬ LÝ';
      case HologramRuntimeState.speaking:
        return '● ĐANG TRẢ LỜI';
      case HologramRuntimeState.error:
        return '● SỰ CỐ';
      case HologramRuntimeState.listening:
        return '● ĐANG LẮNG NGHE';
      default:
        return '● SẴN SÀNG';
    }
  }

  @override
  Widget build(BuildContext context) {
    return Obx(() {
      final state = controller.runtimeState.value;
      final isListening = controller.isVoiceListening.value;
      final badgeColor = _getBadgeColor(state, isListening);
      final badgeText = _getBadgeText(state, isListening);

      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          border: Border(
            bottom: BorderSide(
              color: const Color(0xFF64748B).withValues(alpha: 0.20),
              width: 1,
            ),
          ),
        ),
        child: Row(
          children: [
            Container(
              width: 7,
              height: 7,
              decoration: BoxDecoration(
                color: const Color(0xFF14B8A6),
                shape: BoxShape.circle,
                boxShadow: [
                  BoxShadow(
                    color: const Color(0xFF14B8A6).withValues(alpha: 0.6),
                    blurRadius: 4,
                  ),
                ],
              ),
            ),
            const SizedBox(width: 8),
            const Text(
              'JAVIS AGENT',
              style: TextStyle(
                color: Colors.white,
                fontSize: 14,
                fontWeight: FontWeight.w800,
                letterSpacing: 1.0,
              ),
            ),
            const Spacer(),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
              decoration: BoxDecoration(
                color: badgeColor.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(6),
                border: Border.all(
                  color: badgeColor.withValues(alpha: 0.4),
                  width: 0.8,
                ),
              ),
              child: Text(
                badgeText,
                style: TextStyle(
                  color: badgeColor,
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 0.4,
                ),
              ),
            ),
            const SizedBox(width: 8),
            IconButton(
              tooltip: 'Xoá lịch sử hội thoại',
              icon: const Icon(Icons.delete_outline_rounded, size: 18, color: Color(0xFF94A3B8)),
              padding: EdgeInsets.zero,
              constraints: const BoxConstraints(minWidth: 28, minHeight: 28),
              onPressed: () {
                if (controller.mobileMessages.isNotEmpty) {
                  controller.clearMobileHistory();
                }
              },
            ),
            IconButton(
              tooltip: 'Mở rộng màn hình Chat',
              icon: const Icon(Icons.open_in_new_rounded, size: 17, color: Color(0xFF94A3B8)),
              padding: EdgeInsets.zero,
              constraints: const BoxConstraints(minWidth: 28, minHeight: 28),
              onPressed: () => controller.openDashboard(0, 0),
            ),
            const SizedBox(width: 4),
            IconButton(
              tooltip: 'Ẩn khung chat',
              icon: const Icon(Icons.close_rounded, size: 18, color: Color(0xFF94A3B8)),
              padding: EdgeInsets.zero,
              constraints: const BoxConstraints(minWidth: 28, minHeight: 28),
              onPressed: () => controller.closeChatInput(),
            ),
          ],
        ),
      );
    });
  }
}
