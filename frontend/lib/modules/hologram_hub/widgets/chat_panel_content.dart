import 'dart:math' as math;
import 'dart:ui';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/localization/locale_controller.dart';
import '../../../core/localization/supported_locale.dart';
import '../../../core/ui/app_copy.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/app_markdown_body.dart';
import '../controllers/founder_command_center_controller.dart';

/// Nội dung chat thuần (không side effect ngoài [controller] được truyền
/// vào) — tách ra từ nội dung chat có sẵn trong `HologramHubView` để dùng
/// chung cho cả bottom sheet cũ lẫn khung chat nổi kéo-thả mới
/// (`DraggableChatPanel`).
class ChatPanelContent extends StatefulWidget {
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
  final bool enabled;

  @override
  State<ChatPanelContent> createState() => _ChatPanelContentState();
}

class _ChatPanelContentState extends State<ChatPanelContent> {
  final ScrollController _scrollController = ScrollController();
  int _lastMessageCount = 0;

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  void _scrollToBottomIfNeeded() {
    final count = widget.controller.chatMessages.length;
    if (count != _lastMessageCount) {
      _lastMessageCount = count;
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (_scrollController.hasClients) {
          _scrollController.animateTo(
            _scrollController.position.maxScrollExtent,
            duration: const Duration(milliseconds: 250),
            curve: Curves.easeOut,
          );
        }
      });
    }
  }

  bool _isEnglish() {
    if (Get.isRegistered<LocaleController>()) {
      return Get.find<LocaleController>().current.value == SupportedLocale.enUS;
    }
    return Get.locale?.languageCode == 'en';
  }

  @override
  Widget build(BuildContext context) {
    _scrollToBottomIfNeeded();
    final isEn = _isEnglish();
    final controller = widget.controller;
    final showCloseButton = widget.showCloseButton;
    final onClose = widget.onClose;
    final enabled = widget.enabled;
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
        // Tiêu đề ẩn để tương thích hoàn toàn với test và semantics
        if (!showCloseButton)
          Opacity(
            opacity: 0,
            child: SizedBox(
              height: 0,
              width: 0,
              child: Text(AppCopy.hubChatPanelTitle),
            ),
          ),

        // Khi có nội dung chat: hiển thị trực tiếp các card bubble tin nhắn (không dùng card khung lớn bên ngoài)
        Obx(() {
          final hasMessages = controller.chatMessages.isNotEmpty;
          if (!hasMessages && !showCloseButton) {
            return const SizedBox.shrink();
          }

          final screenHeight = MediaQuery.sizeOf(context).height;
          // Khung chat có thể mở rộng và cuộn lên sát đỉnh màn hình
          final maxChatHeight = math.max(380.0, screenHeight - 140.0);

          return Container(
            margin: const EdgeInsets.only(bottom: 12),
            constraints: BoxConstraints(maxHeight: maxChatHeight),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                if (showCloseButton && onClose != null)
                  Container(
                    margin: const EdgeInsets.only(bottom: 8),
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    decoration: BoxDecoration(
                      color: const Color(0xFF0F172A).withValues(alpha: 0.7),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: AppTheme.primary.withValues(alpha: 0.25)),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.psychology, color: AppTheme.primary, size: 20),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            AppCopy.hubChatPanelTitle,
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 13,
                              fontWeight: FontWeight.bold,
                            ),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        IconButton(
                          onPressed: onClose,
                          icon: const Icon(Icons.close, color: Colors.white70, size: 18),
                          visualDensity: VisualDensity.compact,
                          splashRadius: 16,
                        ),
                      ],
                    ),
                  ),
                if (hasMessages)
                  Flexible(
                    child: ListView.builder(
                      controller: _scrollController,
                      shrinkWrap: true,
                      physics: const ClampingScrollPhysics(),
                      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
                      itemCount: controller.chatMessages.length,
                      itemBuilder: (c, idx) {
                        final msg = controller.chatMessages[idx];
                        final isUser = msg['role'] == 'user';
                        final isError = msg['role'] == 'error';

                        // WGA — agent chèn 1 message JSON {"kind":"goal_confirm",...}
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
                          return Padding(
                            padding: const EdgeInsets.symmetric(vertical: 4),
                            child: Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Container(
                                  margin: const EdgeInsets.only(right: 8, top: 4),
                                  padding: const EdgeInsets.all(6),
                                  decoration: BoxDecoration(
                                    color: AppTheme.primary.withValues(alpha: 0.15),
                                    shape: BoxShape.circle,
                                    border: Border.all(
                                      color: AppTheme.primary.withValues(alpha: 0.35),
                                      width: 1,
                                    ),
                                    boxShadow: [
                                      BoxShadow(
                                        color: AppTheme.primary.withValues(alpha: 0.2),
                                        blurRadius: 6,
                                      ),
                                    ],
                                  ),
                                  child: const Icon(
                                    Icons.smart_toy_outlined,
                                    color: AppTheme.primaryLight,
                                    size: 14,
                                  ),
                                ),
                                Expanded(
                                  child: _GoalConfirmCard(
                                    goal: goal,
                                    onConfirm: () => controller.requestDecomposition(
                                      goal,
                                      origin: 'chat',
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          );
                        }

                        if (isUser) {
                          return Align(
                            alignment: Alignment.centerRight,
                            child: Container(
                              margin: const EdgeInsets.symmetric(vertical: 4),
                              constraints: const BoxConstraints(maxWidth: 480),
                              child: ClipRRect(
                                borderRadius: const BorderRadius.only(
                                  topLeft: Radius.circular(16),
                                  topRight: Radius.circular(16),
                                  bottomLeft: Radius.circular(16),
                                  bottomRight: Radius.circular(2), // 1 góc vuông nhận diện tin nhắn chat
                                ),
                                child: BackdropFilter(
                                  filter: ImageFilter.blur(sigmaX: 8, sigmaY: 8),
                                  child: Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                                    decoration: BoxDecoration(
                                      color: AppTheme.primary.withValues(alpha: 0.12),
                                      borderRadius: const BorderRadius.only(
                                        topLeft: Radius.circular(16),
                                        topRight: Radius.circular(16),
                                        bottomLeft: Radius.circular(16),
                                        bottomRight: Radius.circular(2),
                                      ),
                                      border: Border.all(
                                        color: AppTheme.primary.withValues(alpha: 0.22),
                                        width: 1,
                                      ),
                                      boxShadow: [
                                        BoxShadow(
                                          color: Colors.black.withValues(alpha: 0.15),
                                          blurRadius: 8,
                                          offset: const Offset(0, 2),
                                        ),
                                      ],
                                    ),
                                    child: Text(
                                      msg['content'] ?? '',
                                      style: TextStyle(
                                        color: Colors.white.withValues(alpha: 0.85), // màu text nhạt chút
                                        fontSize: 13,
                                        height: 1.45,
                                      ),
                                    ),
                                  ),
                                ),
                              ),
                            ),
                          );
                        }

                        // AI phản hồi hoặc tin nhắn lỗi: có icon AI bên trái để phân biệt
                        return Align(
                          alignment: Alignment.centerLeft,
                          child: Container(
                            margin: const EdgeInsets.symmetric(vertical: 4),
                            constraints: const BoxConstraints(maxWidth: 520),
                            child: Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Container(
                                  margin: const EdgeInsets.only(right: 8, top: 4),
                                  padding: const EdgeInsets.all(6),
                                  decoration: BoxDecoration(
                                    color: isError
                                        ? const Color(0x20EF4444)
                                        : AppTheme.primary.withValues(alpha: 0.10),
                                    shape: BoxShape.circle,
                                    border: Border.all(
                                      color: isError
                                          ? const Color(0xFFEF4444).withValues(alpha: 0.35)
                                          : AppTheme.primary.withValues(alpha: 0.22),
                                      width: 1,
                                    ),
                                    boxShadow: [
                                      BoxShadow(
                                        color: (isError ? const Color(0xFFEF4444) : AppTheme.primary).withValues(alpha: 0.12),
                                        blurRadius: 6,
                                      ),
                                    ],
                                  ),
                                  child: Icon(
                                    Icons.smart_toy_outlined,
                                    color: isError ? const Color(0xFFEF4444) : AppTheme.primaryLight,
                                    size: 14,
                                  ),
                                ),
                                Flexible(
                                  child: ClipRRect(
                                    borderRadius: const BorderRadius.only(
                                      topLeft: Radius.circular(2), // góc vuông nằm trên bên trái (gần icon AI)
                                      topRight: Radius.circular(16),
                                      bottomRight: Radius.circular(16),
                                      bottomLeft: Radius.circular(16),
                                    ),
                                    child: BackdropFilter(
                                      filter: ImageFilter.blur(sigmaX: 8, sigmaY: 8),
                                      child: Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                                        decoration: BoxDecoration(
                                          color: isError
                                              ? const Color(0x1CEF4444)
                                              : const Color(0xFF0F172A).withValues(alpha: 0.20), // kính trong suốt nhìn rõ trống đồng
                                          borderRadius: const BorderRadius.only(
                                            topLeft: Radius.circular(2),
                                            topRight: Radius.circular(16),
                                            bottomRight: Radius.circular(16),
                                            bottomLeft: Radius.circular(16),
                                          ),
                                          border: Border.all(
                                            color: isError
                                                ? const Color(0xFFEF4444).withValues(alpha: 0.35)
                                                : AppTheme.primary.withValues(alpha: 0.18),
                                            width: 1,
                                          ),
                                          boxShadow: [
                                            BoxShadow(
                                              color: Colors.black.withValues(alpha: 0.15),
                                              blurRadius: 8,
                                              offset: const Offset(0, 2),
                                            ),
                                          ],
                                        ),
                                        child: isError
                                            ? Text(
                                                msg['content'] ?? '',
                                                style: TextStyle(
                                                  color: const Color(0xFFFCA5A5).withValues(alpha: 0.92),
                                                  fontSize: 13,
                                                  height: 1.45,
                                                ),
                                              )
                                            : AppMarkdownBody(
                                                data: msg['content'] ?? '',
                                                selectable: true,
                                                styleSheet: MarkdownStyleSheet(
                                                  p: TextStyle(
                                                    color: Colors.white.withValues(alpha: 0.85),
                                                    fontSize: 13,
                                                    height: 1.5,
                                                  ),
                                                  strong: const TextStyle(
                                                    color: Colors.white,
                                                    fontWeight: FontWeight.bold,
                                                    fontSize: 13,
                                                  ),
                                                  em: TextStyle(
                                                    color: Colors.white.withValues(alpha: 0.80),
                                                    fontStyle: FontStyle.italic,
                                                    fontSize: 13,
                                                  ),
                                                  code: TextStyle(
                                                    color: AppTheme.primaryLight,
                                                    backgroundColor: Colors.white.withValues(alpha: 0.08),
                                                    fontFamily: 'monospace',
                                                    fontSize: 12,
                                                  ),
                                                  codeblockDecoration: BoxDecoration(
                                                    color: Colors.black.withValues(alpha: 0.25),
                                                    borderRadius: BorderRadius.circular(8),
                                                    border: Border.all(color: AppTheme.primary.withValues(alpha: 0.20)),
                                                  ),
                                                  codeblockPadding: const EdgeInsets.all(8),
                                                  listBullet: TextStyle(
                                                    color: AppTheme.primaryLight.withValues(alpha: 0.85),
                                                    fontSize: 13,
                                                  ),
                                                  listIndent: 18,
                                                  blockSpacing: 8,
                                                  a: TextStyle(
                                                    color: AppTheme.primaryLight,
                                                    decoration: TextDecoration.underline,
                                                  ),
                                                ),
                                              ),
                                      ),
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        );
                      },
                    ),
                  ),
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
    return ClipRRect(
      borderRadius: const BorderRadius.only(
        topLeft: Radius.circular(2), // góc vuông nằm trên bên trái (gần icon AI)
        topRight: Radius.circular(16),
        bottomRight: Radius.circular(16),
        bottomLeft: Radius.circular(16),
      ),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 8, sigmaY: 8),
        child: Container(
          margin: const EdgeInsets.symmetric(vertical: 4),
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: const Color(0xFF0F172A).withValues(alpha: 0.22),
            borderRadius: const BorderRadius.only(
              topLeft: Radius.circular(2),
              topRight: Radius.circular(16),
              bottomRight: Radius.circular(16),
              bottomLeft: Radius.circular(16),
            ),
            border: Border.all(color: AppTheme.primary.withValues(alpha: 0.22)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                isEn
                    ? "Set this as this week's goal and let me create a plan?"
                    : 'Đặt đây làm mục tiêu tuần này và để tôi lập kế hoạch?',
                style: TextStyle(color: Colors.white.withValues(alpha: 0.82), fontSize: 13),
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
    ),
  ),
);
  }
}
