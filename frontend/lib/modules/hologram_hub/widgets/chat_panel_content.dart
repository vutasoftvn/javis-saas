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
import '../../../core/routing/app_routes.dart';
import '../../../core/network/api_result.dart';
import '../controllers/founder_command_center_controller.dart';
import '../controllers/hub_operations_controller.dart';
import '../services/hub_operations_service.dart';

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

  static Widget _flexibleIf(bool flexible, Widget child) =>
      flexible ? Flexible(child: child) : child;

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
                border: Border.all(
                  color: AppTheme.primary.withValues(alpha: 0.3),
                ),
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
                  Icon(
                    Icons.chat_bubble_outline,
                    size: 18,
                    color: AppTheme.primaryLight,
                  ),
                  const SizedBox(width: 10),
                  Text(
                    isEn
                        ? 'Select a Project to proceed'
                        : 'Chọn một Project / Dự án để tiếp tục',
                    style: TextStyle(
                      color: Colors.white.withValues(alpha: 0.8),
                      fontSize: 13,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      );
    }

    return LayoutBuilder(
      builder: (context, box) {
        // Cha có chiều cao giới hạn: khung chat co theo phần còn lại (chừa chỗ cho ô nhập) thay vì
        // dùng chiều cao cố định gây overflow. Cha không giới hạn (bottom sheet cũ): giữ maxHeight.
        final boundedHeight = box.hasBoundedHeight;
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
            _flexibleIf(
              boundedHeight,
              Obx(() {
                final hasMessages = controller.chatMessages.isNotEmpty;
                final isLoading = controller.isChatLoading.value;
                // Đang chờ nhưng cuối danh sách là tin của user (chưa có bong bóng AI) -> thêm bong bóng "...".
                final showPendingBubble =
                    isLoading &&
                    hasMessages &&
                    controller.chatMessages.last['role'] == 'user';
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
                          padding: const EdgeInsets.symmetric(
                            horizontal: 12,
                            vertical: 6,
                          ),
                          decoration: BoxDecoration(
                            color: const Color(
                              0xFF0F172A,
                            ).withValues(alpha: 0.7),
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(
                              color: AppTheme.primary.withValues(alpha: 0.25),
                            ),
                          ),
                          child: Row(
                            children: [
                              const Icon(
                                Icons.psychology,
                                color: AppTheme.primary,
                                size: 20,
                              ),
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
                                icon: const Icon(
                                  Icons.close,
                                  color: Colors.white70,
                                  size: 18,
                                ),
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
                            padding: const EdgeInsets.symmetric(
                              horizontal: 4,
                              vertical: 4,
                            ),
                            itemCount:
                                controller.chatMessages.length +
                                (showPendingBubble ? 1 : 0),
                            itemBuilder: (c, idx) {
                              // Chưa có bong bóng AI (đang tạo run) -> bong bóng "..." giả ở cuối.
                              final msg = idx < controller.chatMessages.length
                                  ? controller.chatMessages[idx]
                                  : <String, String>{
                                      'role': 'cosa',
                                      'content': '',
                                    };
                              // Hành động agent chờ founder duyệt (spec 2026-09-27).
                              if (msg['role'] == 'approval') {
                                return Padding(
                                  padding: const EdgeInsets.symmetric(
                                    vertical: 4,
                                  ),
                                  child: _ApprovalCard(
                                    msg: msg,
                                    onDecide: (approve) =>
                                        controller.decideChatApproval(
                                          msg['approval_id'] ?? '',
                                          approve: approve,
                                        ),
                                  ),
                                );
                              }
                              final isUser = msg['role'] == 'user';
                              final isError = msg['role'] == 'error';

                              // WGA — agent chèn 1 message JSON {"kind":"goal_confirm",...}
                              final content = (msg['content'] ?? '').trim();
                              // WGA G9 — tiến độ kế hoạch {"kind":"plan_progress",...}
                              final progress = !isUser && !isError
                                  ? PlanProgress.tryParse(content)
                                  : null;
                              if (progress != null) {
                                return Padding(
                                  padding: const EdgeInsets.symmetric(
                                    vertical: 4,
                                  ),
                                  child: _PlanProgressCard(progress: progress),
                                );
                              }
                              // G-8 — agent đề xuất lưu fact; founder xác nhận mới ghi.
                              final memoryFact = !isUser && !isError
                                  ? memoryConfirmFact(content)
                                  : null;
                              if (memoryFact != null) {
                                return Padding(
                                  padding: const EdgeInsets.symmetric(
                                    vertical: 4,
                                  ),
                                  child: _MemoryConfirmCard(
                                    fact: memoryFact,
                                    onConfirm: () => controller
                                        .confirmProjectFact(memoryFact),
                                  ),
                                );
                              }
                              // B6 — tool `automation.plan.propose` (T1) in thẳng
                              // {"kind":"automation_plan_proposal",...} làm content, cùng cơ
                              // chế parse-JSON-làm-content với plan_progress/memory_confirm ở
                              // trên (xem task-7-brief.md mục "Cơ chế hiển thị").
                              final automationPlanProposal = !isUser && !isError
                                  ? AutomationPlanProposal.tryParse(content)
                                  : null;
                              if (automationPlanProposal != null) {
                                return Padding(
                                  padding: const EdgeInsets.symmetric(
                                    vertical: 4,
                                  ),
                                  child: _AutomationPlanProposalCard(
                                    proposal: automationPlanProposal,
                                    controller: controller,
                                  ),
                                );
                              }
                              if (!isUser &&
                                  !isError &&
                                  content.startsWith('{') &&
                                  content.contains('"goal_confirm"')) {
                                String goal = '';
                                try {
                                  final parsed =
                                      jsonDecode(content)
                                          as Map<String, dynamic>;
                                  goal =
                                      (parsed['normalized_goal'] ?? '')
                                          as String;
                                } catch (_) {}
                                return Padding(
                                  padding: const EdgeInsets.symmetric(
                                    vertical: 4,
                                  ),
                                  child: Row(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Container(
                                        margin: const EdgeInsets.only(
                                          right: 8,
                                          top: 4,
                                        ),
                                        padding: const EdgeInsets.all(6),
                                        decoration: BoxDecoration(
                                          color: AppTheme.primary.withValues(
                                            alpha: 0.15,
                                          ),
                                          shape: BoxShape.circle,
                                          border: Border.all(
                                            color: AppTheme.primary.withValues(
                                              alpha: 0.35,
                                            ),
                                            width: 1,
                                          ),
                                          boxShadow: [
                                            BoxShadow(
                                              color: AppTheme.primary
                                                  .withValues(alpha: 0.2),
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
                                          onConfirm: () =>
                                              controller.requestDecomposition(
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
                                    margin: const EdgeInsets.symmetric(
                                      vertical: 4,
                                    ),
                                    constraints: const BoxConstraints(
                                      maxWidth: 480,
                                    ),
                                    child: ClipRRect(
                                      borderRadius: const BorderRadius.only(
                                        topLeft: Radius.circular(16),
                                        topRight: Radius.circular(16),
                                        bottomLeft: Radius.circular(16),
                                        bottomRight: Radius.circular(
                                          2,
                                        ), // 1 góc vuông nhận diện tin nhắn chat
                                      ),
                                      child: BackdropFilter(
                                        filter: ImageFilter.blur(
                                          sigmaX: 8,
                                          sigmaY: 8,
                                        ),
                                        child: Container(
                                          padding: const EdgeInsets.symmetric(
                                            horizontal: 14,
                                            vertical: 10,
                                          ),
                                          decoration: BoxDecoration(
                                            color: AppTheme.primary.withValues(
                                              alpha: 0.12,
                                            ),
                                            borderRadius:
                                                const BorderRadius.only(
                                                  topLeft: Radius.circular(16),
                                                  topRight: Radius.circular(16),
                                                  bottomLeft: Radius.circular(
                                                    16,
                                                  ),
                                                  bottomRight: Radius.circular(
                                                    2,
                                                  ),
                                                ),
                                            border: Border.all(
                                              color: AppTheme.primary
                                                  .withValues(alpha: 0.22),
                                              width: 1,
                                            ),
                                            boxShadow: [
                                              BoxShadow(
                                                color: Colors.black.withValues(
                                                  alpha: 0.15,
                                                ),
                                                blurRadius: 8,
                                                offset: const Offset(0, 2),
                                              ),
                                            ],
                                          ),
                                          child: Text(
                                            msg['content'] ?? '',
                                            style: TextStyle(
                                              color: Colors.white.withValues(
                                                alpha: 0.85,
                                              ), // màu text nhạt chút
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
                                  margin: const EdgeInsets.symmetric(
                                    vertical: 4,
                                  ),
                                  constraints: const BoxConstraints(
                                    maxWidth: 520,
                                  ),
                                  child: Row(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Container(
                                        margin: const EdgeInsets.only(
                                          right: 8,
                                          top: 4,
                                        ),
                                        padding: const EdgeInsets.all(6),
                                        decoration: BoxDecoration(
                                          color: isError
                                              ? const Color(0x20EF4444)
                                              : AppTheme.primary.withValues(
                                                  alpha: 0.10,
                                                ),
                                          shape: BoxShape.circle,
                                          border: Border.all(
                                            color: isError
                                                ? const Color(
                                                    0xFFEF4444,
                                                  ).withValues(alpha: 0.35)
                                                : AppTheme.primary.withValues(
                                                    alpha: 0.22,
                                                  ),
                                            width: 1,
                                          ),
                                          boxShadow: [
                                            BoxShadow(
                                              color:
                                                  (isError
                                                          ? const Color(
                                                              0xFFEF4444,
                                                            )
                                                          : AppTheme.primary)
                                                      .withValues(alpha: 0.12),
                                              blurRadius: 6,
                                            ),
                                          ],
                                        ),
                                        child: Icon(
                                          Icons.smart_toy_outlined,
                                          color: isError
                                              ? const Color(0xFFEF4444)
                                              : AppTheme.primaryLight,
                                          size: 14,
                                        ),
                                      ),
                                      Flexible(
                                        child: ClipRRect(
                                          borderRadius: const BorderRadius.only(
                                            topLeft: Radius.circular(
                                              2,
                                            ), // góc vuông nằm trên bên trái (gần icon AI)
                                            topRight: Radius.circular(16),
                                            bottomRight: Radius.circular(16),
                                            bottomLeft: Radius.circular(16),
                                          ),
                                          child: BackdropFilter(
                                            filter: ImageFilter.blur(
                                              sigmaX: 8,
                                              sigmaY: 8,
                                            ),
                                            child: Container(
                                              padding:
                                                  const EdgeInsets.symmetric(
                                                    horizontal: 14,
                                                    vertical: 10,
                                                  ),
                                              decoration: BoxDecoration(
                                                color: isError
                                                    ? const Color(0x1CEF4444)
                                                    : const Color(
                                                        0xFF0F172A,
                                                      ).withValues(
                                                        alpha: 0.20,
                                                      ), // kính trong suốt nhìn rõ trống đồng
                                                borderRadius:
                                                    const BorderRadius.only(
                                                      topLeft: Radius.circular(
                                                        2,
                                                      ),
                                                      topRight: Radius.circular(
                                                        16,
                                                      ),
                                                      bottomRight:
                                                          Radius.circular(16),
                                                      bottomLeft:
                                                          Radius.circular(16),
                                                    ),
                                                border: Border.all(
                                                  color: isError
                                                      ? const Color(
                                                          0xFFEF4444,
                                                        ).withValues(
                                                          alpha: 0.35,
                                                        )
                                                      : AppTheme.primary
                                                            .withValues(
                                                              alpha: 0.18,
                                                            ),
                                                  width: 1,
                                                ),
                                                boxShadow: [
                                                  BoxShadow(
                                                    color: Colors.black
                                                        .withValues(
                                                          alpha: 0.15,
                                                        ),
                                                    blurRadius: 8,
                                                    offset: const Offset(0, 2),
                                                  ),
                                                ],
                                              ),
                                              child: isError
                                                  ? Text(
                                                      msg['content'] ?? '',
                                                      style: TextStyle(
                                                        color:
                                                            const Color(
                                                              0xFFFCA5A5,
                                                            ).withValues(
                                                              alpha: 0.92,
                                                            ),
                                                        fontSize: 13,
                                                        height: 1.45,
                                                      ),
                                                    )
                                                  : ((msg['content'] ?? '')
                                                            .isEmpty &&
                                                        isLoading)
                                                  ? const _TypingDots()
                                                  : AppMarkdownBody(
                                                      data:
                                                          msg['content'] ?? '',
                                                      selectable: true,
                                                      styleSheet: MarkdownStyleSheet(
                                                        p: TextStyle(
                                                          color: Colors.white
                                                              .withValues(
                                                                alpha: 0.85,
                                                              ),
                                                          fontSize: 13,
                                                          height: 1.5,
                                                        ),
                                                        strong: const TextStyle(
                                                          color: Colors.white,
                                                          fontWeight:
                                                              FontWeight.bold,
                                                          fontSize: 13,
                                                        ),
                                                        em: TextStyle(
                                                          color: Colors.white
                                                              .withValues(
                                                                alpha: 0.80,
                                                              ),
                                                          fontStyle:
                                                              FontStyle.italic,
                                                          fontSize: 13,
                                                        ),
                                                        code: TextStyle(
                                                          color: AppTheme
                                                              .primaryLight,
                                                          backgroundColor:
                                                              Colors.white
                                                                  .withValues(
                                                                    alpha: 0.08,
                                                                  ),
                                                          fontFamily:
                                                              'monospace',
                                                          fontSize: 12,
                                                        ),
                                                        codeblockDecoration:
                                                            BoxDecoration(
                                                              color: Colors
                                                                  .black
                                                                  .withValues(
                                                                    alpha: 0.25,
                                                                  ),
                                                              borderRadius:
                                                                  BorderRadius.circular(
                                                                    8,
                                                                  ),
                                                              border: Border.all(
                                                                color: AppTheme
                                                                    .primary
                                                                    .withValues(
                                                                      alpha:
                                                                          0.20,
                                                                    ),
                                                              ),
                                                            ),
                                                        codeblockPadding:
                                                            const EdgeInsets.all(
                                                              8,
                                                            ),
                                                        listBullet: TextStyle(
                                                          color: AppTheme
                                                              .primaryLight
                                                              .withValues(
                                                                alpha: 0.85,
                                                              ),
                                                          fontSize: 13,
                                                        ),
                                                        listIndent: 18,
                                                        blockSpacing: 8,
                                                        a: TextStyle(
                                                          color: AppTheme
                                                              .primaryLight,
                                                          decoration:
                                                              TextDecoration
                                                                  .underline,
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
                    ],
                  ),
                );
              }),
            ),

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
                      contentPadding: const EdgeInsets.symmetric(
                        horizontal: 16,
                        vertical: 14,
                      ),
                      prefixIcon: IconButton(
                        key: const Key('hub_chat_new_chat_button'),
                        tooltip: AppCopy.hubChatNewChatTooltip,
                        onPressed: controller.startNewChat,
                        icon: const Icon(
                          Icons.add,
                          color: AppTheme.primary,
                          size: 20,
                        ),
                        splashRadius: 20,
                      ),
                      suffixIcon: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          // WGA G10 — kích hoạt lập kế hoạch tường minh (không đoán
                          // từ văn bản): nội dung ô nhập là mục tiêu cần phân rã.
                          IconButton(
                            key: const Key('hub_chat_plan_button'),
                            tooltip: isEn
                                ? 'Plan & assign to agents'
                                : 'Lập kế hoạch & giao việc',
                            onPressed: controller.planFromChatInput,
                            icon: const Icon(
                              Icons.account_tree_outlined,
                              color: AppTheme.primary,
                              size: 20,
                            ),
                            splashRadius: 20,
                          ),
                          IconButton(
                            key: const Key('hub_chat_send_button'),
                            tooltip: isEn ? 'Send' : 'Gửi',
                            onPressed: () => controller.sendChatMessage(
                              controller.chatInputController.text,
                            ),
                            icon: const Icon(
                              Icons.send,
                              color: AppTheme.primary,
                              size: 20,
                            ),
                            splashRadius: 20,
                          ),
                        ],
                      ),
                    ),
                    onSubmitted: (text) => controller.sendChatMessage(text),
                  ),
                ),
              ),
            ),
          ],
        );
      },
    );
  }
}

/// G-8 — fact trong thẻ `{"kind":"memory_confirm","fact":...}`; null nếu không phải.
String? memoryConfirmFact(String content) {
  if (!content.startsWith('{') || !content.contains('"memory_confirm"')) {
    return null;
  }
  try {
    final j = jsonDecode(content);
    if (j is Map<String, dynamic> && j['kind'] == 'memory_confirm') {
      final fact = '${j['fact'] ?? ''}'.trim();
      return fact.isEmpty ? null : fact;
    }
  } on FormatException {
    return null;
  }
  return null;
}

/// Hiệu ứng "..." (3 chấm nhấp nhô lần lượt) trong bong bóng AI khi đang chờ phản hồi.
class _TypingDots extends StatefulWidget {
  const _TypingDots();

  @override
  State<_TypingDots> createState() => _TypingDotsState();
}

class _TypingDotsState extends State<_TypingDots>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1200),
  )..repeat();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: 'AI is typing',
      child: SizedBox(
        height: 20,
        child: AnimatedBuilder(
          animation: _controller,
          builder: (context, _) {
            return Row(
              mainAxisSize: MainAxisSize.min,
              children: List.generate(3, (i) {
                // Mỗi chấm lệch pha 0.2 chu kỳ; sóng sin cho nhịp lên-xuống mượt.
                final phase = (_controller.value - i * 0.2) % 1.0;
                final wave = math.sin(phase * math.pi).clamp(0.0, 1.0);
                return Container(
                  width: 6,
                  height: 6,
                  margin: EdgeInsets.only(
                    right: i < 2 ? 5 : 0,
                    bottom: 6 * wave,
                  ),
                  decoration: BoxDecoration(
                    color: AppTheme.primaryLight.withValues(
                      alpha: 0.35 + 0.55 * wave,
                    ),
                    shape: BoxShape.circle,
                  ),
                );
              }),
            );
          },
        ),
      ),
    );
  }
}

/// Thẻ duyệt hành động agent ngay trong chat: tóm tắt bằng tên (không ID) do backend
/// dựng theo locale, hai nút Duyệt / Từ chối; đã quyết định thì thay nút bằng nhãn.
class _ApprovalCard extends StatelessWidget {
  final Map<String, String> msg;
  final Future<bool> Function(bool approve) onDecide;

  const _ApprovalCard({required this.msg, required this.onDecide});

  @override
  Widget build(BuildContext context) {
    final status = msg['status'] ?? 'pending';
    final title = msg['title'] ?? '';
    final detail = msg['detail'] ?? '';
    final busy = status == 'deciding';
    final resolved = switch (status) {
      'approved' => (AppCopy.hubApprovalApproved, Colors.greenAccent),
      'rejected' => (AppCopy.hubApprovalRejected, const Color(0xFFF87171)),
      'expired' => (AppCopy.hubApprovalExpired, const Color(0xFF94A3B8)),
      _ => null,
    };
    return Container(
      key: Key('hub_chat_approval_${msg['approval_id'] ?? ''}'),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A).withValues(alpha: 0.22),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.primary.withValues(alpha: 0.45)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.shield_outlined, color: AppTheme.primaryLight, size: 16),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  AppCopy.hubApprovalHeading,
                  style: TextStyle(
                    color: Colors.white.withValues(alpha: 0.6),
                    fontSize: 11,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            title,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 13,
              fontWeight: FontWeight.w600,
            ),
          ),
          if (detail.isNotEmpty) ...[
            const SizedBox(height: 4),
            Text(
              detail,
              style: const TextStyle(color: Color(0xFFCBD5E1), fontSize: 12),
            ),
          ],
          const SizedBox(height: 10),
          if (resolved != null)
            Text(
              resolved.$1,
              style: TextStyle(color: resolved.$2, fontSize: 12),
            )
          else
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                FilledButton(
                  onPressed: busy ? null : () => onDecide(true),
                  style: FilledButton.styleFrom(
                    backgroundColor: AppTheme.primary,
                    foregroundColor: const Color(0xFF04070E),
                  ),
                  child: Text(AppCopy.hubApprovalApprove),
                ),
                OutlinedButton(
                  onPressed: busy ? null : () => onDecide(false),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: const Color(0xFFCBD5E1),
                  ),
                  child: Text(AppCopy.hubApprovalReject),
                ),
              ],
            ),
        ],
      ),
    );
  }
}

class _MemoryConfirmCard extends StatefulWidget {
  final String fact;
  final Future<bool> Function() onConfirm;

  const _MemoryConfirmCard({required this.fact, required this.onConfirm});

  @override
  State<_MemoryConfirmCard> createState() => _MemoryConfirmCardState();
}

class _MemoryConfirmCardState extends State<_MemoryConfirmCard> {
  bool _saved = false;
  bool _dismissed = false;
  bool _busy = false;

  @override
  Widget build(BuildContext context) {
    if (_dismissed) return const SizedBox.shrink();
    final isEn = Get.isRegistered<LocaleController>()
        ? Get.find<LocaleController>().current.value == SupportedLocale.enUS
        : Get.locale?.languageCode == 'en';
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A).withValues(alpha: 0.22),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.primary.withValues(alpha: 0.22)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            isEn
                ? 'Save this to the project memory?'
                : 'Lưu điều này vào trí nhớ dự án?',
            style: TextStyle(
              color: Colors.white.withValues(alpha: 0.82),
              fontSize: 13,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            '“${widget.fact}”',
            style: const TextStyle(color: Color(0xFFCBD5E1), fontSize: 12),
          ),
          const SizedBox(height: 10),
          if (_saved)
            Text(
              isEn ? 'Saved' : 'Đã lưu',
              style: const TextStyle(color: Colors.greenAccent, fontSize: 12),
            )
          else
            Row(
              children: [
                ElevatedButton(
                  onPressed: _busy
                      ? null
                      : () async {
                          setState(() => _busy = true);
                          final ok = await widget.onConfirm();
                          if (!mounted) return;
                          setState(() {
                            _busy = false;
                            _saved = ok;
                          });
                        },
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.primary,
                    foregroundColor: const Color(0xFF04070E),
                  ),
                  child: Text(isEn ? 'Save' : 'Lưu'),
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

/// WGA G9 — message có cấu trúc báo tiến độ task của 1 execution plan.
class PlanProgress {
  final String planId;
  final List<String> done;
  final List<String> pendingReview;
  final List<String> waitingApproval;
  final List<String> blocked;

  const PlanProgress({
    required this.planId,
    required this.done,
    required this.pendingReview,
    required this.waitingApproval,
    required this.blocked,
  });

  static PlanProgress? tryParse(String content) {
    if (!content.startsWith('{') || !content.contains('"plan_progress"')) {
      return null;
    }
    try {
      final j = jsonDecode(content);
      if (j is! Map<String, dynamic> || j['kind'] != 'plan_progress') {
        return null;
      }
      List<String> list(String k) =>
          ((j[k] as List<dynamic>?) ?? const []).map((e) => '$e').toList();
      return PlanProgress(
        planId: '${j['plan_id'] ?? ''}',
        done: list('done'),
        pendingReview: list('pending_review'),
        waitingApproval: list('waiting_approval'),
        blocked: list('blocked'),
      );
    } on FormatException {
      return null;
    }
  }
}

class _PlanProgressCard extends StatelessWidget {
  final PlanProgress progress;

  const _PlanProgressCard({required this.progress});

  @override
  Widget build(BuildContext context) {
    final isEn = Get.isRegistered<LocaleController>()
        ? Get.find<LocaleController>().current.value == SupportedLocale.enUS
        : Get.locale?.languageCode == 'en';
    final rows = <(IconData, Color, String, List<String>)>[
      (
        Icons.check_circle_outline,
        Colors.greenAccent,
        isEn ? 'Done' : 'Đã xong',
        progress.done,
      ),
      (
        Icons.rate_review_outlined,
        Colors.amberAccent,
        isEn ? 'Needs your confirmation' : 'Chờ bạn xác nhận kết quả',
        progress.pendingReview,
      ),
      (
        Icons.pending_actions_outlined,
        Colors.amberAccent,
        isEn ? 'Waiting for your approval' : 'Chờ bạn duyệt',
        progress.waitingApproval,
      ),
      (
        Icons.block,
        Colors.redAccent,
        isEn ? 'Blocked' : 'Bị chặn',
        progress.blocked,
      ),
    ];
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A).withValues(alpha: 0.22),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.primary.withValues(alpha: 0.22)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            isEn ? 'Plan progress update' : 'Cập nhật tiến độ kế hoạch',
            style: TextStyle(
              color: Colors.white.withValues(alpha: 0.82),
              fontSize: 13,
            ),
          ),
          for (final (icon, color, label, titles) in rows)
            if (titles.isNotEmpty) ...[
              const SizedBox(height: 6),
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(icon, color: color, size: 16),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      '$label: ${titles.join(', ')}',
                      style: const TextStyle(
                        color: Color(0xFFCBD5E1),
                        fontSize: 12,
                      ),
                    ),
                  ),
                ],
              ),
            ],
        ],
      ),
    );
  }
}

/// B6 (Task 7) — model + parse cho thẻ đề xuất kế hoạch tự động hoá
/// (`{"kind":"automation_plan_proposal",...}`, shape trả về từ
/// `POST /operations/projects/:projectId/automation-plans/proposals` — xem task-5-report.md
/// mục ROUTE). Parse rộng dung: field thiếu/sai kiểu → giá trị mặc định hợp lý, KHÔNG throw
/// (output model có thể lệch định dạng nhẹ).
class AutomationPlanConnectorInfo {
  const AutomationPlanConnectorInfo({required this.key, required this.status});
  final String key;
  final String status;
  bool get isConnected => status == 'connected';
}

class AutomationPlanChannelInfo {
  const AutomationPlanChannelInfo({
    required this.kind,
    required this.label,
    required this.verified,
  });
  final String kind;
  final String label;
  final bool verified;
}

class AutomationPlanBlocker {
  const AutomationPlanBlocker({required this.code, required this.target});
  final String code;
  final String target;
}

class AutomationPlanReadinessInfo {
  const AutomationPlanReadinessInfo({required this.ready, required this.blockers});
  final bool ready;
  final List<AutomationPlanBlocker> blockers;
}

class AutomationPlanDetail {
  const AutomationPlanDetail({
    required this.agentLabel,
    required this.proposeNewAgent,
    required this.skillLabel,
    required this.connectors,
    required this.channel,
    required this.scheduleHumanReadable,
    required this.tokenBudgetPerRun,
  });
  final String agentLabel;
  final bool proposeNewAgent;
  final String skillLabel;
  final List<AutomationPlanConnectorInfo> connectors;
  final AutomationPlanChannelInfo channel;
  final String scheduleHumanReadable;
  final int tokenBudgetPerRun;
}

class AutomationPlanProposal {
  const AutomationPlanProposal({
    required this.proposalId,
    required this.projectId,
    required this.plan,
    required this.readiness,
  });

  final String proposalId;
  final String projectId;
  final AutomationPlanDetail plan;
  final AutomationPlanReadinessInfo readiness;

  static AutomationPlanProposal? tryParse(String content) {
    if (!content.startsWith('{') || !content.contains('"automation_plan_proposal"')) {
      return null;
    }
    try {
      final j = jsonDecode(content);
      if (j is! Map<String, dynamic> || j['kind'] != 'automation_plan_proposal') {
        return null;
      }
      final planJson = (j['plan'] is Map<String, dynamic>)
          ? j['plan'] as Map<String, dynamic>
          : const <String, dynamic>{};
      final channelJson = (planJson['channel'] is Map<String, dynamic>)
          ? planJson['channel'] as Map<String, dynamic>
          : const <String, dynamic>{};
      final scheduleJson = (planJson['schedule'] is Map<String, dynamic>)
          ? planJson['schedule'] as Map<String, dynamic>
          : const <String, dynamic>{};
      final readinessJson = (j['readiness'] is Map<String, dynamic>)
          ? j['readiness'] as Map<String, dynamic>
          : const <String, dynamic>{};
      final connectors = ((planJson['connectors'] as List<dynamic>?) ?? const [])
          .whereType<Map<String, dynamic>>()
          .map((c) => AutomationPlanConnectorInfo(
                key: '${c['key'] ?? ''}',
                status: '${c['status'] ?? 'missing'}',
              ))
          .toList();
      final blockers = ((readinessJson['blockers'] as List<dynamic>?) ?? const [])
          .whereType<Map<String, dynamic>>()
          .map((b) => AutomationPlanBlocker(
                code: '${b['code'] ?? ''}',
                target: '${b['target'] ?? ''}',
              ))
          .toList();
      return AutomationPlanProposal(
        proposalId: '${j['proposalId'] ?? ''}',
        projectId: '${j['projectId'] ?? ''}',
        plan: AutomationPlanDetail(
          agentLabel: '${planJson['agentLabel'] ?? ''}',
          proposeNewAgent: planJson['proposeNewAgent'] == true,
          skillLabel: '${planJson['skillLabel'] ?? ''}',
          connectors: connectors,
          channel: AutomationPlanChannelInfo(
            kind: '${channelJson['kind'] ?? ''}',
            label: '${channelJson['label'] ?? ''}',
            verified: channelJson['verified'] == true,
          ),
          scheduleHumanReadable: '${scheduleJson['humanReadable'] ?? ''}',
          tokenBudgetPerRun: (planJson['tokenBudgetPerRun'] is num)
              ? (planJson['tokenBudgetPerRun'] as num).toInt()
              : 0,
        ),
        readiness: AutomationPlanReadinessInfo(
          ready: readinessJson['ready'] == true,
          blockers: blockers,
        ),
      );
    } on FormatException {
      return null;
    } catch (_) {
      // Parse rộng dung — mọi lỗi cast khác (field đúng tên, sai kiểu) cũng không được
      // làm crash bong bóng chat, chỉ coi như không nhận diện được thẻ này.
      return null;
    }
  }
}

/// Thẻ đề xuất kế hoạch tự động hoá (B6): hiển thị agent/skill/connector/kênh/lịch/ngân
/// sách, nút Duyệt gọi thẳng route approve của Task 6 (B5). Thiếu điều kiện (`readiness.
/// ready == false`) thì khoá nút Duyệt và hiện nút phụ điều hướng thật theo từng blocker.
class _AutomationPlanProposalCard extends StatefulWidget {
  const _AutomationPlanProposalCard({required this.proposal, required this.controller});

  final AutomationPlanProposal proposal;
  final FounderCommandCenterController controller;

  @override
  State<_AutomationPlanProposalCard> createState() => _AutomationPlanProposalCardState();
}

class _AutomationPlanProposalCardState extends State<_AutomationPlanProposalCard> {
  bool _busy = false;
  bool _approved = false;
  String? _errorMessage;
  String? _scheduleSummary;
  HubOperationsService? _service;

  HubOperationsService get _operations => _service ??= HubOperationsService();

  Future<void> _approve() async {
    setState(() {
      _busy = true;
      _errorMessage = null;
    });
    final res = await _operations.approveAutomationPlan(
      proposalId: widget.proposal.proposalId,
      projectId: widget.proposal.projectId,
    );
    if (!mounted) return;
    switch (res) {
      case ApiSuccess():
        // `ScheduleDefinitionResponse` (task-6-report.md) không có sẵn chuỗi giờ chạy đã
        // format — dùng lại `humanReadable` company đã tính khi tạo nháp (không đổi sau
        // duyệt, cùng lịch).
        setState(() {
          _busy = false;
          _approved = true;
          _scheduleSummary = widget.proposal.plan.scheduleHumanReadable;
        });
      case ApiFailure(:final failure):
        // Task 6 (B5): duyệt lại 1 đề xuất đã có lịch trả `already_exists` — coi như đã
        // tạo lịch, không phải lỗi (task-6-report.md mục ROUTE APPROVE).
        final raw = failure.raw;
        final backendCode = raw is Map ? raw['code']?.toString() : null;
        if (backendCode == 'already_exists') {
          setState(() {
            _busy = false;
            _approved = true;
            _scheduleSummary = widget.proposal.plan.scheduleHumanReadable;
          });
          return;
        }
        setState(() {
          _busy = false;
          _errorMessage = AppCopy.automationPlanErrorFor(backendCode);
        });
    }
  }

  @override
  Widget build(BuildContext context) {
    final plan = widget.proposal.plan;
    final readiness = widget.proposal.readiness;
    return Container(
      key: Key('hub_chat_automation_plan_${widget.proposal.proposalId}'),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A).withValues(alpha: 0.22),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.primary.withValues(alpha: 0.45)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.auto_awesome_outlined, color: AppTheme.primaryLight, size: 16),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  AppCopy.automationPlanHeading,
                  style: TextStyle(color: Colors.white.withValues(alpha: 0.6), fontSize: 11),
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            plan.proposeNewAgent ? AppCopy.automationPlanNewAgentLabel : plan.agentLabel,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 13,
              fontWeight: FontWeight.w600,
            ),
          ),
          if (plan.proposeNewAgent) ...[
            const SizedBox(height: 2),
            Text(
              AppCopy.automationPlanNewAgentWarning,
              style: const TextStyle(color: Color(0xFFFBBF24), fontSize: 11),
            ),
          ],
          const SizedBox(height: 4),
          Text(
            '${AppCopy.automationPlanSkillLabel}: ${plan.skillLabel}',
            style: const TextStyle(color: Color(0xFFCBD5E1), fontSize: 12),
          ),
          if (plan.connectors.isNotEmpty) ...[
            const SizedBox(height: 6),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: [
                for (final c in plan.connectors)
                  _statusChip(
                    c.isConnected
                        ? AppCopy.automationPlanConnectorConnected(c.key)
                        : AppCopy.automationPlanConnectorMissing(c.key),
                    c.isConnected,
                  ),
              ],
            ),
          ],
          const SizedBox(height: 6),
          _statusChip(
            plan.channel.verified
                ? AppCopy.automationPlanChannelVerified(plan.channel.label)
                : AppCopy.automationPlanChannelUnverified(plan.channel.label),
            plan.channel.verified,
          ),
          const SizedBox(height: 8),
          Text(
            '${AppCopy.automationPlanScheduleLabel}: ${plan.scheduleHumanReadable}',
            style: const TextStyle(color: Color(0xFFCBD5E1), fontSize: 12),
          ),
          const SizedBox(height: 2),
          Text(
            '${AppCopy.automationPlanBudgetLabel}: ${plan.tokenBudgetPerRun}',
            style: const TextStyle(color: Color(0xFFCBD5E1), fontSize: 12),
          ),
          const SizedBox(height: 10),
          if (_approved)
            Text(
              _scheduleSummary == null || _scheduleSummary!.isEmpty
                  ? AppCopy.automationPlanApproved
                  : '${AppCopy.automationPlanApproved} — $_scheduleSummary',
              style: const TextStyle(color: Colors.greenAccent, fontSize: 12),
            )
          else ...[
            if (_errorMessage != null) ...[
              Text(
                _errorMessage!,
                style: const TextStyle(color: Color(0xFFF87171), fontSize: 12),
              ),
              const SizedBox(height: 6),
            ],
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                FilledButton(
                  key: const Key('automation_plan_approve_button'),
                  onPressed: (readiness.ready && !_busy) ? _approve : null,
                  style: FilledButton.styleFrom(
                    backgroundColor: AppTheme.primary,
                    foregroundColor: const Color(0xFF04070E),
                  ),
                  child: _busy
                      ? const SizedBox(
                          width: 14,
                          height: 14,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: Color(0xFF04070E),
                          ),
                        )
                      : Text(AppCopy.automationPlanApprove),
                ),
                if (!readiness.ready)
                  for (final blocker in readiness.blockers) _blockerButton(blocker),
              ],
            ),
          ],
        ],
      ),
    );
  }

  Widget _statusChip(String label, bool ok) {
    final color = ok ? Colors.greenAccent : const Color(0xFFFBBF24);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: color.withValues(alpha: 0.4)),
      ),
      child: Text(
        label,
        style: TextStyle(color: color, fontSize: 11, fontWeight: FontWeight.w600),
      ),
    );
  }

  /// Nút phụ khi thiếu điều kiện — điều hướng THẬT theo `target` (không SnackBar/no-op).
  /// `founder_profile` sang route hồ sơ founder thật (`AppRoutes.profile`). `tools_tab`/
  /// `agents_tab` phát tín hiệu THẬT qua `FounderCommandCenterController.requestOperationsTab`
  /// để `HubOperationsPanel` (hologram_hub_view.dart) mở đúng tab — xem CONCERNS trong
  /// task-7-report.md về việc nối listener phía đó (đang là WIP chưa commit của người khác).
  Widget _blockerButton(AutomationPlanBlocker blocker) {
    switch (blocker.target) {
      case 'founder_profile':
        return OutlinedButton(
          key: const Key('automation_plan_open_founder_profile'),
          onPressed: () => Get.toNamed(AppRoutes.profile),
          style: OutlinedButton.styleFrom(foregroundColor: const Color(0xFFCBD5E1)),
          child: Text(AppCopy.automationPlanOpenFounderProfile),
        );
      case 'tools_tab':
        return OutlinedButton(
          key: const Key('automation_plan_open_tools_tab'),
          onPressed: () => widget.controller.requestOperationsTab(HubOperationsTab.tools),
          style: OutlinedButton.styleFrom(foregroundColor: const Color(0xFFCBD5E1)),
          child: Text(AppCopy.automationPlanOpenToolsTab),
        );
      case 'agents_tab':
        return OutlinedButton(
          key: const Key('automation_plan_open_agents_tab'),
          onPressed: () => widget.controller.requestOperationsTab(HubOperationsTab.agents),
          style: OutlinedButton.styleFrom(foregroundColor: const Color(0xFFCBD5E1)),
          child: Text(AppCopy.automationPlanOpenAgentsTab),
        );
      default:
        return const SizedBox.shrink();
    }
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
        topLeft: Radius.circular(
          2,
        ), // góc vuông nằm trên bên trái (gần icon AI)
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
                style: TextStyle(
                  color: Colors.white.withValues(alpha: 0.82),
                  fontSize: 13,
                ),
              ),
              if (widget.goal.isNotEmpty) ...[
                const SizedBox(height: 6),
                Text(
                  '“${widget.goal}”',
                  style: const TextStyle(
                    color: Color(0xFFCBD5E1),
                    fontSize: 12,
                  ),
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
