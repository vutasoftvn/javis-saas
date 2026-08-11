import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/chat_controller.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/theme/glassmorphism.dart';

class ChatView extends GetView<ChatController> {
  const ChatView({super.key});

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<ChatController>()) {
      Get.put(ChatController());
    }

    // Dùng LayoutBuilder thay vì MediaQuery: ChatView được nhúng trong body của
    // DashboardView nên bề rộng thực tế nhỏ hơn màn hình. Nếu quyết định layout
    // theo bề rộng màn hình, sidebar 280px + header desktop vẫn được vẽ trong
    // vùng hẹp và làm tràn RenderFlex.
    return LayoutBuilder(
      builder: (context, constraints) {
        final isDesktop = constraints.maxWidth >= 800;
        final chatWidth = isDesktop
            ? constraints.maxWidth - _sidebarWidth - 1 // 1 = VerticalDivider
            : constraints.maxWidth;

        return Row(
          children: [
            _buildSidebar(isDesktop),
            if (isDesktop)
              const VerticalDivider(
                width: 1,
                thickness: 1,
                color: Color(0xFF1E293B),
              ),
            Expanded(child: _buildChatArea(isDesktop, chatWidth)),
          ],
        );
      },
    );
  }

  static const double _sidebarWidth = 280;

  Widget _buildSidebar(bool isDesktop) {
    if (!isDesktop) return const SizedBox.shrink();

    return Container(
      width: _sidebarWidth,
      color: AppTheme.backgroundDark,
      child: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: ElevatedButton.icon(
              onPressed: controller.createNewSession,
              icon: const Icon(Icons.add),
              label: const Text('Đoạn chat mới'),
              style: ElevatedButton.styleFrom(
                minimumSize: const Size(double.infinity, 48),
              ),
            ),
          ),
          Expanded(
            child: Obx(() {
              if (controller.isLoadingSessions.value) {
                return const Center(child: CircularProgressIndicator());
              }
              final currentId = controller.currentSessionId.value?.toString();

              return ListView.builder(
                padding: const EdgeInsets.symmetric(
                  horizontal: 16,
                  vertical: 8,
                ),
                itemCount: controller.sessions.length,
                itemBuilder: (context, index) {
                  final session = controller.sessions[index];
                  final isSelected = session['id'].toString() == currentId;

                  void showDeleteMenu(Offset position) {
                    showMenu(
                      context: context,
                      position: RelativeRect.fromLTRB(
                        position.dx,
                        position.dy,
                        position.dx + 1,
                        position.dy + 1,
                      ),
                      color: AppTheme.surfaceDark,
                      items: [
                        PopupMenuItem(
                          value: 'delete',
                          child: Row(
                            children: const [
                              Icon(Icons.delete_outline, color: Colors.redAccent, size: 18),
                              SizedBox(width: 8),
                              Text('Xoá đoạn chat', style: TextStyle(color: Colors.redAccent)),
                            ],
                          ),
                        ),
                      ],
                    ).then((value) {
                      if (value == 'delete') {
                        controller.deleteSession(session['id'].toString());
                      }
                    });
                  }

                  return Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: GestureDetector(
                      onSecondaryTapDown: (details) => showDeleteMenu(details.globalPosition),
                      onLongPressStart: (details) => showDeleteMenu(details.globalPosition),
                      child: InkWell(
                        onTap: () => controller.selectSession(session['id'].toString()),
                        borderRadius: BorderRadius.circular(12),
                        child: Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 16,
                            vertical: 12,
                          ),
                          decoration: BoxDecoration(
                            color: isSelected
                                ? AppTheme.primary.withValues(alpha: 0.15)
                                : Colors.transparent,
                            borderRadius: BorderRadius.circular(12),
                            border: isSelected
                                ? Border.all(
                                    color: AppTheme.primary.withValues(alpha: 0.3),
                                  )
                                : Border.all(color: Colors.transparent),
                          ),
                          child: Row(
                            children: [
                              Icon(
                                isSelected
                                    ? Icons.chat_bubble
                                    : Icons.chat_bubble_outline,
                                size: 20,
                                color: isSelected
                                    ? AppTheme.primaryLight
                                    : AppTheme.textMutedDark,
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: Text(
                                  session['title'] ?? 'Đoạn chat mới',
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: TextStyle(
                                    color: isSelected
                                        ? AppTheme.primaryLight
                                        : AppTheme.textMutedDark,
                                    fontWeight: isSelected
                                        ? FontWeight.w600
                                        : FontWeight.normal,
                                    fontSize: 14,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                  );
                },
              );
            }),
          ),
        ],
      ),
    );
  }

  /// Thư AI đã soạn, đang chờ người dùng bấm duyệt.
  ///
  /// Đặt ngay trên ô nhập chứ không lẫn vào danh sách tin nhắn: đây là việc cần người
  /// QUYẾT ĐỊNH, không phải một dòng hội thoại trôi đi khi cuộn.
  Widget _buildEmailApprovals(bool isDesktop) {
    return Obx(() {
      final pending = controller.emailApprovals
          .where((item) => item['status'] == 'pending')
          .toList();
      if (pending.isEmpty) return const SizedBox.shrink();

      return Container(
        margin: EdgeInsets.symmetric(horizontal: isDesktop ? 24 : 16),
        child: Column(
          children: pending.map((approval) {
            final id = approval['id'] as String;
            final deciding = controller.decidingApprovalId.value == id;
            return Container(
              margin: const EdgeInsets.only(bottom: 8),
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: Colors.amber.withValues(alpha: 0.08),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.amber.withValues(alpha: 0.35)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      const Icon(Icons.drafts_outlined,
                          color: Colors.amber, size: 18),
                      const SizedBox(width: 8),
                      const Expanded(
                        child: Text(
                          'Thư đã soạn — chưa gửi, chờ bạn duyệt',
                          style: TextStyle(
                            color: Colors.amber,
                            fontSize: 13,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Tới: ${approval['to'] ?? ''}',
                    style: const TextStyle(
                        color: AppTheme.textDark, fontSize: 13),
                  ),
                  Text(
                    'Tiêu đề: ${approval['subject'] ?? ''}',
                    style: const TextStyle(
                        color: AppTheme.textDark, fontSize: 13),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    (approval['body'] as String? ?? ''),
                    maxLines: 4,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                        color: AppTheme.textMutedDark, fontSize: 12, height: 1.5),
                  ),
                  const SizedBox(height: 10),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.end,
                    children: [
                      TextButton(
                        onPressed: deciding
                            ? null
                            : () => controller.decideEmailApproval(id,
                                approve: false),
                        child: const Text('Bỏ qua',
                            style: TextStyle(color: AppTheme.textMutedDark)),
                      ),
                      const SizedBox(width: 8),
                      ElevatedButton.icon(
                        onPressed: deciding
                            ? null
                            : () => controller.decideEmailApproval(id,
                                approve: true),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.amber.shade700,
                          foregroundColor: Colors.white,
                        ),
                        icon: deciding
                            ? const SizedBox(
                                width: 14,
                                height: 14,
                                child: CircularProgressIndicator(
                                    strokeWidth: 2, color: Colors.white),
                              )
                            : const Icon(Icons.send_rounded, size: 16),
                        label: const Text('Duyệt & gửi'),
                      ),
                    ],
                  ),
                ],
              ),
            );
          }).toList(),
        ),
      );
    });
  }

  /// Model picker widget — reusable in both desktop header and mobile AppBar
  Widget _buildModelPicker() {
    return Obx(() {
      final selected = controller.selectedModel.value;
      final options = controller.models;
      final label = selected != null
          ? (selected['label'] as String? ?? '${selected['provider']} · ${selected['model']}')
          : 'Chọn model...';

      if (options.isEmpty) {
        return Text(
          label,
          style: const TextStyle(fontSize: 12, color: AppTheme.textMutedDark),
        );
      }

      return PopupMenuButton<Map<String, dynamic>>(
        tooltip: 'Đổi model',
        padding: EdgeInsets.zero,
        color: AppTheme.surfaceDark,
        onSelected: controller.selectModel,
        itemBuilder: (context) => options
            .cast<Map<String, dynamic>>()
            .map(
              (m) {
                final configured = m['configured'] == true;
                return PopupMenuItem<Map<String, dynamic>>(
                  value: m,
                  child: Row(
                    children: [
                      Icon(
                        configured
                            ? Icons.check_circle
                            : Icons.remove_circle_outline,
                        size: 15,
                        color: configured
                            ? AppTheme.success
                            : AppTheme.textMutedDark,
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          m['label'] as String? ??
                              '${m['provider']} · ${m['model']}',
                          style: TextStyle(
                            color: configured
                                ? AppTheme.textDark
                                : AppTheme.textMutedDark,
                          ),
                        ),
                      ),
                      if (!configured) ...[
                        const SizedBox(width: 8),
                        const Text(
                          'chưa có key',
                          style: TextStyle(
                            fontSize: 11,
                            color: AppTheme.textMutedDark,
                          ),
                        ),
                      ],
                    ],
                  ),
                );
              },
            )
            .toList(),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Tên model do server trả về, độ dài không kiểm soát được -> phải co được.
            Flexible(
              child: Text(
                label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  fontSize: 12,
                  color: AppTheme.textMutedDark,
                ),
              ),
            ),
            const SizedBox(width: 2),
            const Icon(
              Icons.expand_more,
              size: 14,
              color: AppTheme.textMutedDark,
            ),
          ],
        ),
      );
    });
  }

  Widget _buildChatArea(bool isDesktop, double chatWidth) {
    final textController = TextEditingController();

    return Container(
      color: Colors.transparent,
      child: Column(
        children: [
          // Header — desktop only; mobile uses DashboardView's AppBar
          if (isDesktop)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
              decoration: const BoxDecoration(
                border: Border(bottom: BorderSide(color: Color(0xFF1E293B))),
              ),
              child: Row(
                children: [
                  // Expanded thay cho Spacer: khi cửa sổ hẹp, phần tiêu đề + model picker
                  // phải co lại nhường chỗ cho các nút bên phải. Để Column tự do theo kích
                  // thước nội dung thì tên model dài làm tràn header (RenderFlex overflow).
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Javis Brain',
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        _buildModelPicker(),
                      ],
                    ),
                  ),
                  Obx(
                    () => controller.isSending.value
                        ? TextButton.icon(
                            onPressed: controller.stopGenerating,
                            icon: const Icon(
                              Icons.stop_circle_outlined,
                              size: 18,
                              color: AppTheme.accentLight,
                            ),
                            label: const Text(
                              'Dừng',
                              style: TextStyle(color: AppTheme.accentLight),
                            ),
                          )
                        : const SizedBox.shrink(),
                  ),
                  IconButton(
                    icon: const Icon(
                      Icons.more_vert,
                      color: AppTheme.textMutedDark,
                    ),
                    onPressed: () {},
                  ),
                ],
              ),
            ),

          // Messages
          Expanded(
            child: Obx(() {
              if (controller.isLoadingMessages.value) {
                return const Center(child: CircularProgressIndicator());
              }

              if (controller.messages.isEmpty) {
                return const Center(
                  child: Text(
                    'Bắt đầu cuộc trò chuyện với Javis.',
                    style: TextStyle(color: AppTheme.textMutedDark),
                  ),
                );
              }

              return ListView.builder(
                padding: EdgeInsets.all(isDesktop ? 24 : 16),
                itemCount: controller.messages.length,
                itemBuilder: (context, index) {
                  final msg = controller.messages[index];
                  final isUser = msg['role'] == 'user';

                  return Padding(
                    padding: const EdgeInsets.only(bottom: 24),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisAlignment: isUser
                          ? MainAxisAlignment.end
                          : MainAxisAlignment.start,
                      children: [
                        if (!isUser) ...[
                          const CircleAvatar(
                            backgroundColor: AppTheme.primary,
                            child: Icon(
                              Icons.psychology,
                              color: Color(0xFF04070E),
                              size: 20,
                            ),
                          ),
                          const SizedBox(width: 16),
                        ],

                        Flexible(
                          child: Column(
                            crossAxisAlignment: isUser
                                ? CrossAxisAlignment.end
                                : CrossAxisAlignment.start,
                            children: [
                              isUser
                                  ? Container(
                                      constraints: BoxConstraints(
                                        maxWidth: chatWidth * 0.75,
                                      ),
                                      padding: const EdgeInsets.symmetric(
                                          horizontal: 16, vertical: 12),
                                      decoration: BoxDecoration(
                                        gradient: AppTheme.primaryGradient,
                                        borderRadius: const BorderRadius.only(
                                          topLeft: Radius.circular(16),
                                          topRight: Radius.circular(16),
                                          bottomLeft: Radius.circular(16),
                                          bottomRight: Radius.circular(4),
                                        ),
                                        boxShadow: [
                                          BoxShadow(
                                            color: AppTheme.primary
                                                .withValues(alpha: 0.3),
                                            blurRadius: 12,
                                            offset: const Offset(0, 4),
                                          ),
                                        ],
                                      ),
                                      child: Text(
                                        msg['content'] ?? '',
                                        style: const TextStyle(
                                          color: Colors.white,
                                          fontSize: 16,
                                          height: 1.5,
                                        ),
                                      ),
                                    )
                                  : Container(
                                      constraints: BoxConstraints(
                                        maxWidth: chatWidth * 0.75,
                                      ),
                                      decoration: BoxDecoration(
                                        color: AppTheme.surfaceDark,
                                        borderRadius: const BorderRadius.only(
                                          topLeft: Radius.circular(16),
                                          topRight: Radius.circular(16),
                                          bottomLeft: Radius.circular(4),
                                          bottomRight: Radius.circular(16),
                                        ),
                                      ),
                                      child: Padding(
                                        padding: const EdgeInsets.symmetric(
                                            horizontal: 16, vertical: 12),
                                        child: Column(
                                          crossAxisAlignment:
                                              CrossAxisAlignment.start,
                                          children: [
                                            (msg['content'] as String? ?? '')
                                                            .isEmpty &&
                                                        msg['status'] ==
                                                            'streaming'
                                                ? const _TypingDots()
                                                : Text(
                                                    msg['content'] ?? '',
                                                    style: const TextStyle(
                                                      color: AppTheme.textDark,
                                                      fontSize: 16,
                                                      height: 1.5,
                                                    ),
                                                  ),
                                            if (msg['citations'] != null &&
                                                (msg['citations'] as List)
                                                    .isNotEmpty) ...[
                                              const SizedBox(height: 12),
                                              const Divider(
                                                  color: Colors.white24),
                                              const SizedBox(height: 8),
                                              const Text('Tham khảo:',
                                                  style: TextStyle(
                                                      color: AppTheme
                                                          .textMutedDark,
                                                      fontSize: 12)),
                                              const SizedBox(height: 8),
                                              Wrap(
                                                spacing: 8,
                                                runSpacing: 8,
                                                children: (msg['citations']
                                                        as List)
                                                    .map(
                                                      (c) => Container(
                                                        padding: const EdgeInsets
                                                            .symmetric(
                                                            horizontal: 8,
                                                            vertical: 4),
                                                        decoration:
                                                            BoxDecoration(
                                                          color: AppTheme
                                                              .primary
                                                              .withValues(
                                                                  alpha: 0.2),
                                                          borderRadius:
                                                              BorderRadius
                                                                  .circular(4),
                                                        ),
                                                        child: Text(
                                                          c['path']
                                                                  ?.split('/')
                                                                  .last ??
                                                              'Tài liệu',
                                                          style: const TextStyle(
                                                              fontSize: 12,
                                                              color: AppTheme
                                                                  .primaryLight),
                                                        ),
                                                      ),
                                                    )
                                                    .toList(),
                                              ),
                                            ],
                                          ],
                                        ),
                                      ),
                                    ),
                            ],
                          ),
                        ),

                        if (isUser) ...[
                          const SizedBox(width: 16),
                          CircleAvatar(
                            backgroundColor: AppTheme.surfaceDark,
                            child: const Icon(
                              Icons.person,
                              color: AppTheme.textMutedDark,
                              size: 20,
                            ),
                          ),
                        ],
                      ],
                    ),
                  );
                },
              );
            }),
          ),

          _buildEmailApprovals(isDesktop),

          // Input — pill-shaped (border radius 100)
          Container(
            padding: EdgeInsets.symmetric(
              horizontal: isDesktop ? 24 : 16,
              vertical: isDesktop ? 24 : 16,
            ),
            child: Row(
              children: [
                Expanded(
                  child: Glassmorphism(
                    blur: 20,
                    opacity: 0.3,
                    color: AppTheme.surfaceDark,
                    borderRadius: BorderRadius.circular(100),
                    child: TextField(
                      controller: textController,
                      decoration: InputDecoration(
                        contentPadding: const EdgeInsets.symmetric(
                          horizontal: 24,
                          vertical: 14,
                        ),
                        hintText: 'Nhập tin nhắn của bạn...',
                        filled: false,
                        fillColor: Colors.transparent,
                        border: InputBorder.none,
                        enabledBorder: InputBorder.none,
                        focusedBorder: InputBorder.none,
                        suffixIcon: Padding(
                          padding: const EdgeInsets.only(right: 6),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Obx(() => IconButton(
                                icon: Icon(
                                  controller.isRecordingVoice.value ? Icons.mic : Icons.mic_none,
                                  color: controller.isRecordingVoice.value ? const Color(0xFFEF4444) : const Color(0xFF00F0FF),
                                ),
                                tooltip: controller.isRecordingVoice.value ? 'Dừng ghi âm' : 'Nói qua Micro',
                                onPressed: controller.toggleVoiceRecording,
                              )),
                              IconButton(
                                icon: const Icon(
                                  Icons.send_rounded,
                                  color: AppTheme.primaryLight,
                                ),
                                onPressed: () {
                                  controller.sendMessage(textController.text);
                                  textController.clear();
                                },
                              ),
                            ],
                          ),
                        ),
                      ),
                      onSubmitted: (val) {
                        controller.sendMessage(val);
                        textController.clear();
                      },
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _TypingDots extends StatefulWidget {
  const _TypingDots();

  @override
  State<_TypingDots> createState() => _TypingDotsState();
}

class _TypingDotsState extends State<_TypingDots>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    )..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 20,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: List.generate(3, (i) {
          return AnimatedBuilder(
            animation: _controller,
            builder: (context, child) {
              final t = (_controller.value - i * 0.2) % 1.0;
              final opacity = 0.3 + 0.7 * (t < 0.5 ? t * 2 : (1 - t) * 2);
              return Padding(
                padding: const EdgeInsets.symmetric(horizontal: 2),
                child: Opacity(
                  opacity: opacity.clamp(0.3, 1.0),
                  child: const CircleAvatar(
                    radius: 4,
                    backgroundColor: AppTheme.textMutedDark,
                  ),
                ),
              );
            },
          );
        }),
      ),
    );
  }
}
