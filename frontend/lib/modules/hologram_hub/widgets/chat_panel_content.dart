import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/ui/app_copy.dart';
import '../controllers/founder_command_center_controller.dart';

/// Nội dung chat thuần (không side effect ngoài [controller] được truyền
/// vào) — tách ra từ nội dung chat có sẵn trong `HologramHubView` để dùng
/// chung cho cả bottom sheet cũ lẫn khung chat nổi kéo-thả mới
/// (`DraggableChatPanel`).
class ChatPanelContent extends StatelessWidget {
  const ChatPanelContent({
    super.key,
    required this.controller,
    required this.onClose,
  });

  final FounderCommandCenterController controller;
  final VoidCallback onClose;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Row(
          children: [
            const Icon(Icons.psychology, color: Color(0xFF8B5CF6), size: 24),
            const SizedBox(width: 10),
            // Expanded + ellipsis: panel nổi (`DraggableChatPanel`) hẹp hơn
            // nhiều so với bottom sheet cũ, tránh RenderFlex overflow khi tiêu
            // đề dài hơn bề rộng khả dụng.
            const Expanded(
              child: Text(
                AppCopy.hubChatPanelTitle,
                style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
                overflow: TextOverflow.ellipsis,
              ),
            ),
            IconButton(
              onPressed: onClose,
              icon: const Icon(Icons.close, color: Colors.white70),
            ),
          ],
        ),
        const Divider(color: Color(0x336366F1)),
        Expanded(
          child: Obx(() {
            if (controller.chatMessages.isEmpty) {
              return Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.chat_bubble_outline, size: 48, color: Colors.white.withValues(alpha: 0.2)),
                    const SizedBox(height: 12),
                    Text(
                      AppCopy.hubChatEmptyState,
                      style: TextStyle(color: Colors.white.withValues(alpha: 0.5), fontSize: 13),
                      textAlign: TextAlign.center,
                    ),
                  ],
                ),
              );
            }
            return ListView.builder(
              itemCount: controller.chatMessages.length,
              itemBuilder: (c, idx) {
                final msg = controller.chatMessages[idx];
                final isUser = msg['role'] == 'user';
                final isError = msg['role'] == 'error';

                // WGA — agent chèn 1 message JSON {"kind":"goal_confirm",...}
                // khi nhận diện phát biểu mục tiêu tuần. Render 2 nút thay vì text.
                final content = (msg['content'] ?? '').trim();
                if (!isUser &&
                    !isError &&
                    content.startsWith('{') &&
                    content.contains('"goal_confirm"')) {
                  String goal = '';
                  try {
                    final parsed = jsonDecode(content) as Map<String, dynamic>;
                    goal = (parsed['normalized_goal'] ?? '') as String;
                  } catch (_) {}
                  return _GoalConfirmCard(
                    goal: goal,
                    onConfirm: () => controller.requestDecomposition(
                      goal,
                      origin: 'chat',
                    ),
                  );
                }

                return Align(
                  alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
                  child: Container(
                    margin: const EdgeInsets.symmetric(vertical: 6),
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: isUser
                          ? const Color(0xFF6366F1)
                          : (isError ? const Color(0x33EF4444) : const Color(0xFF1E293B)),
                      borderRadius: BorderRadius.circular(12),
                      border: isError ? Border.all(color: const Color(0xFFEF4444), width: 1) : null,
                    ),
                    child: Text(
                      msg['content'] ?? '',
                      style: const TextStyle(color: Colors.white, fontSize: 13),
                    ),
                  ),
                );
              },
            );
          }),
        ),
        Obx(() => controller.isChatLoading.value
            ? const Padding(
                padding: EdgeInsets.all(8.0),
                child: LinearProgressIndicator(color: Color(0xFF6366F1)),
              )
            : const SizedBox.shrink()),
        const SizedBox(height: 10),
        Row(
          children: [
            Expanded(
              child: TextField(
                controller: controller.chatInputController,
                style: const TextStyle(color: Colors.white, fontSize: 13),
                decoration: InputDecoration(
                  hintText: AppCopy.hubChatInputHint,
                  hintStyle: TextStyle(color: Colors.white.withValues(alpha: 0.4), fontSize: 12),
                  filled: true,
                  fillColor: const Color(0xFF1E293B),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
                  contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                ),
                onSubmitted: (text) => controller.sendChatMessage(text),
              ),
            ),
            const SizedBox(width: 8),
            IconButton(
              onPressed: () => controller.sendChatMessage(controller.chatInputController.text),
              icon: const Icon(Icons.send, color: Color(0xFF6366F1)),
            ),
          ],
        ),
      ],
    );
  }
}

/// WGA — thẻ xác nhận "đặt làm mục tiêu tuần" trong luồng chat.
class _GoalConfirmCard extends StatefulWidget {
  final String goal;
  final VoidCallback onConfirm;

  const _GoalConfirmCard({required this.goal, required this.onConfirm});

  @override
  State<_GoalConfirmCard> createState() => _GoalConfirmCardState();
}

class _GoalConfirmCardState extends State<_GoalConfirmCard> {
  bool _dismissed = false;

  @override
  Widget build(BuildContext context) {
    if (_dismissed) return const SizedBox.shrink();
    return Container(
      margin: const EdgeInsets.symmetric(vertical: 6),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFF6366F1)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Đặt đây làm mục tiêu tuần này và để tôi lập kế hoạch?',
            style: TextStyle(color: Colors.white, fontSize: 13),
          ),
          if (widget.goal.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(
              '“${widget.goal}”',
              style: const TextStyle(color: Color(0xFFCBD5E1), fontSize: 12),
            ),
          ],
          const SizedBox(height: 10),
          Row(
            children: [
              ElevatedButton(
                onPressed: () {
                  widget.onConfirm();
                  setState(() => _dismissed = true);
                },
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF6366F1),
                  foregroundColor: Colors.white,
                ),
                child: const Text('Đặt & lập kế hoạch'),
              ),
              const SizedBox(width: 8),
              TextButton(
                onPressed: () => setState(() => _dismissed = true),
                child: const Text(
                  'Không',
                  style: TextStyle(color: Color(0xFF94A3B8)),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
