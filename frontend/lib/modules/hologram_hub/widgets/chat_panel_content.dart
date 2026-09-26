import 'dart:ui';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/localization/locale_controller.dart';
import '../../../core/localization/supported_locale.dart';
import '../../../core/ui/app_copy.dart';
import '../../../core/theme/app_theme.dart';
import '../controllers/founder_command_center_controller.dart';

/// Nội dung chat thuần (không side effect ngoài [controller] được truyền
/// vào) — tách ra từ nội dung chat có sẵn trong `HologramHubView` để dùng
/// chung cho cả bottom sheet cũ lẫn khung chat nổi kéo-thả mới
/// (`DraggableChatPanel`).
class ChatPanelContent extends StatelessWidget {
  const ChatPanelContent({
    super.key,
    required this.controller,
    this.onClose,
    this.showCloseButton = false,
    this.enabled = true,
  });

  final FounderCommandCenterController controller;
  final VoidCallback? onClose;
  final bool showCloseButton;

  /// Task 7 — `false` khi chưa chọn Project: composer không được render,
  /// chỉ hiện thông báo yêu cầu chọn Project. Widget vẫn mount (không bị
  /// swap ra ngoài) để layout Hub luôn có đúng 1 khung chat cố định.
  final bool enabled;

  bool _isEnglish() {
    if (Get.isRegistered<LocaleController>()) {
      return Get.find<LocaleController>().current.value == SupportedLocale.enUS;
    }
    return Get.locale?.languageCode == 'en';
  }

  @override
  Widget build(BuildContext context) {
    final isEn = _isEnglish();
    if (!enabled) {
      return Center(
        child: ClipRRect(
          borderRadius: BorderRadius.circular(100),
          child: BackdropFilter(
            filter: ImageFilter.blur(sigmaX: 16, sigmaY: 16),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
              decoration: BoxDecoration(
                color: const Color(0xFF0F172A).withValues(alpha: 0.7),
                borderRadius: BorderRadius.circular(100),
                border: Border.all(color: AppTheme.primary.withValues(alpha: 0.3)),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: 0.3),
                    blurRadius: 16,
                    offset: const Offset(0, 4),
                  ),
                ],
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.chat_bubble_outline, size: 18, color: AppTheme.primaryLight),
                  const SizedBox(width: 10),
                  Text(
                    isEn ? 'Select a Project to proceed' : 'Chọn một Project / Dự án để tiếp tục',
                    style: TextStyle(color: Colors.white.withValues(alpha: 0.8), fontSize: 13),
                  ),
                ],
              ),
            ),
          ),
        ),
      );
    }

    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisAlignment: MainAxisAlignment.end,
      children: [
        // Khi có nội dung chat hoặc khi showCloseButton == true: hiển thị phần tin nhắn / header từ dưới lên dạng glass
        Obx(() {
          final hasMessages = controller.chatMessages.isNotEmpty;
          if (!hasMessages && !showCloseButton) {
            return const SizedBox.shrink();
          }

          return Container(
            margin: const EdgeInsets.only(bottom: 12),
            constraints: const BoxConstraints(maxHeight: 380),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(20),
              child: BackdropFilter(
                filter: ImageFilter.blur(sigmaX: 20, sigmaY: 20),
                child: Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: const Color(0xFF0F172A).withValues(alpha: 0.72),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: AppTheme.primary.withValues(alpha: 0.3)),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withValues(alpha: 0.4),
                        blurRadius: 24,
                        offset: const Offset(0, 8),
                      ),
                    ],
                  ),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Row(
                        children: [
                          const Icon(Icons.psychology, color: AppTheme.primary, size: 22),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              AppCopy.hubChatPanelTitle,
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 14,
                                fontWeight: FontWeight.bold,
                              ),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                          if (showCloseButton && onClose != null)
                            IconButton(
                              onPressed: onClose,
                              icon: const Icon(Icons.close, color: Colors.white70, size: 18),
                              visualDensity: VisualDensity.compact,
                              splashRadius: 16,
                            ),
                        ],
                      ),
                      if (hasMessages) ...[
                        const SizedBox(height: 8),
                        Divider(color: AppTheme.primary.withValues(alpha: 0.2), height: 1),
                        const SizedBox(height: 8),
                        Flexible(
                          child: ListView.builder(
                            shrinkWrap: true,
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
                                        ? AppTheme.primary.withValues(alpha: 0.2)
                                        : (isError ? const Color(0x33EF4444) : const Color(0xFF1E293B)),
                                    borderRadius: BorderRadius.circular(12),
                                    border: Border.all(
                                      color: isUser
                                          ? AppTheme.primary.withValues(alpha: 0.4)
                                          : (isError ? const Color(0xFFEF4444) : const Color(0xFF334155)),
                                      width: 1,
                                    ),
                                  ),
                                  child: Text(
                                    msg['content'] ?? '',
                                    style: const TextStyle(color: Colors.white, fontSize: 13),
                                  ),
                                ),
                              );
                            },
                          ),
                        ),
                      ],
                      if (controller.isChatLoading.value)
                        Padding(
                          padding: const EdgeInsets.only(top: 8.0),
                          child: LinearProgressIndicator(
                            color: AppTheme.primary,
                            backgroundColor: AppTheme.primary.withValues(alpha: 0.15),
                          ),
                        ),
                    ],
                  ),
                ),
              ),
            ),
          );
        }),

        // Text chat input: bo góc 100, dạng glass, icon add bên trái, icon send bên phải
        ClipRRect(
          borderRadius: BorderRadius.circular(100),
          child: BackdropFilter(
            filter: ImageFilter.blur(sigmaX: 16, sigmaY: 16),
            child: Container(
              decoration: BoxDecoration(
                color: const Color(0xFF0F172A).withValues(alpha: 0.65),
                borderRadius: BorderRadius.circular(100),
                border: Border.all(
                  color: AppTheme.primary.withValues(alpha: 0.35),
                  width: 1.2,
                ),
                boxShadow: [
                  BoxShadow(
                    color: AppTheme.primary.withValues(alpha: 0.08),
                    blurRadius: 16,
                    offset: const Offset(0, 4),
                  ),
                  BoxShadow(
                    color: Colors.black.withValues(alpha: 0.35),
                    blurRadius: 20,
                    offset: const Offset(0, 6),
                  ),
                ],
              ),
              child: TextField(
                controller: controller.chatInputController,
                style: const TextStyle(color: Colors.white, fontSize: 13),
                decoration: InputDecoration(
                  hintText: AppCopy.hubChatInputHint,
                  hintStyle: TextStyle(
                    color: Colors.white.withValues(alpha: 0.5),
                    fontSize: 12.5,
                  ),
                  filled: false,
                  border: InputBorder.none,
                  enabledBorder: InputBorder.none,
                  focusedBorder: InputBorder.none,
                  contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                  prefixIcon: IconButton(
                    key: const Key('hub_chat_new_chat_button'),
                    tooltip: AppCopy.hubChatNewChatTooltip,
                    onPressed: controller.startNewChat,
                    icon: const Icon(Icons.add, color: AppTheme.primary, size: 20),
                    splashRadius: 20,
                  ),
                  suffixIcon: IconButton(
                    key: const Key('hub_chat_send_button'),
                    tooltip: isEn ? 'Send' : 'Gửi',
                    onPressed: () => controller.sendChatMessage(controller.chatInputController.text),
                    icon: const Icon(Icons.send, color: AppTheme.primary, size: 20),
                    splashRadius: 20,
                  ),
                ),
                onSubmitted: (text) => controller.sendChatMessage(text),
              ),
            ),
          ),
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

  bool _isEnglish() {
    if (Get.isRegistered<LocaleController>()) {
      return Get.find<LocaleController>().current.value == SupportedLocale.enUS;
    }
    return Get.locale?.languageCode == 'en';
  }

  @override
  Widget build(BuildContext context) {
    if (_dismissed) return const SizedBox.shrink();
    final isEn = _isEnglish();
    return Container(
      margin: const EdgeInsets.symmetric(vertical: 6),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.primary.withValues(alpha: 0.5)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            isEn
                ? "Set this as this week's goal and let me create a plan?"
                : 'Đặt đây làm mục tiêu tuần này và để tôi lập kế hoạch?',
            style: const TextStyle(color: Colors.white, fontSize: 13),
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
                  backgroundColor: AppTheme.primary,
                  foregroundColor: const Color(0xFF04070E),
                ),
                child: Text(isEn ? 'Set & Plan' : 'Đặt & lập kế hoạch'),
              ),
              const SizedBox(width: 8),
              TextButton(
                onPressed: () => setState(() => _dismissed = true),
                child: Text(
                  isEn ? 'No' : 'Không',
                  style: const TextStyle(color: Color(0xFF94A3B8)),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
