import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/shell/chat_panel_controller.dart';
import '../controllers/founder_command_center_controller.dart';
import 'chat_panel_content.dart';

class DraggableChatPanel extends StatelessWidget {
  const DraggableChatPanel({super.key});

  static const _width = 340.0;
  static const _height = 480.0;

  ChatPanelController get _panelController => Get.find<ChatPanelController>();
  FounderCommandCenterController get _hubController =>
      Get.find<FounderCommandCenterController>();

  @override
  Widget build(BuildContext context) {
    return Obx(() {
      if (!_panelController.isOpen.value) return const SizedBox.shrink();

      return LayoutBuilder(
        builder: (context, constraints) {
          final maxX = (constraints.maxWidth - _width).clamp(0.0, double.infinity);
          final maxY = (constraints.maxHeight - _height).clamp(0.0, double.infinity);
          final defaultPosition = Offset(
            (constraints.maxWidth - _width - 48).clamp(0.0, maxX),
            (constraints.maxHeight - _height - 48).clamp(0.0, maxY),
          );
          final current = _panelController.position.value ?? defaultPosition;
          final bounded = Offset(
            current.dx.clamp(0.0, maxX),
            current.dy.clamp(0.0, maxY),
          );

          // Bọc trong 1 Stack riêng: Positioned cần RenderObject Stack làm cha
          // trực tiếp — đặt Positioned ngay dưới LayoutBuilder (không có Stack
          // trung gian) khiến Flutter báo lỗi ParentData không tương thích vì
          // LayoutBuilder tự chèn RenderObject của chính nó vào giữa.
          return Stack(
            children: [
              Positioned(
                left: bounded.dx,
                top: bounded.dy,
                child: GestureDetector(
                  onPanUpdate: (details) => _panelController.updatePosition(
                    Offset(
                      (bounded.dx + details.delta.dx).clamp(0.0, maxX),
                      (bounded.dy + details.delta.dy).clamp(0.0, maxY),
                    ),
                  ),
                  child: Container(
                    width: _width,
                    height: _height,
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: const Color(0xFF0F172A),
                      borderRadius: BorderRadius.circular(16),
                      boxShadow: [
                        BoxShadow(color: Colors.black.withValues(alpha: 0.4), blurRadius: 20),
                      ],
                    ),
                    child: ChatPanelContent(
                      controller: _hubController,
                      onClose: _panelController.close,
                    ),
                  ),
                ),
              ),
            ],
          );
        },
      );
    });
  }
}
