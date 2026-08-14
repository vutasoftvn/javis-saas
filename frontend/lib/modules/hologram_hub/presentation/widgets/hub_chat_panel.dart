import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:get/get.dart';
import '../../controllers/hologram_hub_controller.dart';
import 'audio_waveform_painter.dart';
import 'miva_hologram_core.dart';

class HubChatPanel extends StatefulWidget {
  final HologramHubController controller;

  const HubChatPanel({
    super.key,
    required this.controller,
  });

  @override
  State<HubChatPanel> createState() => _HubChatPanelState();
}

class _HubChatPanelState extends State<HubChatPanel>
    with SingleTickerProviderStateMixin {
  final TextEditingController _textController = TextEditingController();
  final FocusNode _focusNode = FocusNode();
  final ScrollController _scrollController = ScrollController();
  late AnimationController _waveController;
  bool _isComposing = false;

  @override
  void initState() {
    super.initState();
    _waveController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1600),
    )..repeat();

    _textController.addListener(_handleTextChange);
  }

  void _handleTextChange() {
    final composing = _textController.text.trim().isNotEmpty;
    if (composing != _isComposing) {
      setState(() {
        _isComposing = composing;
      });
    }
  }

  @override
  void dispose() {
    _waveController.dispose();
    _textController.removeListener(_handleTextChange);
    _textController.dispose();
    _focusNode.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _handleSubmitted(String text) {
    final trimmed = text.trim();
    if (trimmed.isEmpty) return;

    _textController.clear();
    widget.controller.executePrompt(trimmed);
    _scrollToBottom();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  Color _getBadgeColor(HologramRuntimeState state, bool isListening) {
    if (isListening) return const Color(0xFF00F0FF);
    switch (state) {
      case HologramRuntimeState.thinking:
        return const Color(0xFF818CF8);
      case HologramRuntimeState.speaking:
        return const Color(0xFF00FFB2);
      case HologramRuntimeState.error:
        return const Color(0xFFEF4444);
      case HologramRuntimeState.listening:
        return const Color(0xFF00F0FF);
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
    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF070C18).withValues(alpha: 0.95),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: const Color(0xFF1E293B).withValues(alpha: 0.9),
          width: 1,
        ),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF00F0FF).withValues(alpha: 0.05),
            blurRadius: 16,
            spreadRadius: 1,
          ),
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.5),
            blurRadius: 20,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // 1. HEADER
            _buildHeader(),

            const Divider(
              height: 1,
              thickness: 1,
              color: Color(0xFF1E293B),
            ),

            // 2. CHAT MESSAGES / EMPTY STATE
            Expanded(
              child: Obx(() {
                final msgs = widget.controller.mobileMessages;
                if (msgs.isEmpty) {
                  return _buildEmptyState();
                }
                return _buildMessageList(msgs);
              }),
            ),

            // 3. VOICE RECORDING ACTIVE BANNER (IF LISTENING)
            Obx(() {
              final isListening = widget.controller.isVoiceListening.value ||
                  widget.controller.runtimeState.value ==
                      HologramRuntimeState.listening;
              if (!isListening) return const SizedBox.shrink();
              return _buildVoiceListeningBanner();
            }),

            const Divider(
              height: 1,
              thickness: 1,
              color: Color(0xFF1E293B),
            ),

            // 4. BOTTOM INPUT BAR
            _buildInputBar(),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Obx(() {
      final isListening = widget.controller.isVoiceListening.value ||
          widget.controller.runtimeState.value == HologramRuntimeState.listening;
      final state = widget.controller.runtimeState.value;
      final badgeColor = _getBadgeColor(state, isListening);
      final badgeText = _getBadgeText(state, isListening);

      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        decoration: BoxDecoration(
          color: const Color(0xFF0B1934).withValues(alpha: 0.85),
          border: const Border(
            bottom: BorderSide(
              color: Color(0xFF1E293B),
              width: 0.5,
            ),
          ),
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(6),
              decoration: BoxDecoration(
                color: const Color(0xFF00F0FF).withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(
                  color: const Color(0xFF00F0FF).withValues(alpha: 0.4),
                  width: 1,
                ),
              ),
              child: const Icon(
                Icons.smart_toy_outlined,
                size: 16,
                color: Color(0xFF00F0FF),
              ),
            ),
            const SizedBox(width: 10),
            const Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'TRỢ LÝ COSA AI',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 15,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 1.1,
                    ),
                  ),
                  SizedBox(height: 2),
                  Text(
                    'Chat & Điều hành thông minh',
                    style: TextStyle(
                      color: Color(0xFF94A3B8),
                      fontSize: 14,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
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
                  fontSize: 14,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 0.6,
                ),
              ),
            ),
            const SizedBox(width: 8),
            // Clear history button
            IconButton(
              tooltip: 'Xoá lịch sử hội thoại',
              icon: const Icon(
                Icons.delete_outline_rounded,
                size: 18,
                color: Color(0xFF94A3B8),
              ),
              padding: EdgeInsets.zero,
              constraints: const BoxConstraints(minWidth: 28, minHeight: 28),
              onPressed: () {
                if (widget.controller.mobileMessages.isNotEmpty) {
                  widget.controller.clearMobileHistory();
                }
              },
            ),
            // Open full dashboard chat
            IconButton(
              tooltip: 'Mở rộng màn hình Chat',
              icon: const Icon(
                Icons.open_in_new_rounded,
                size: 17,
                color: Color(0xFF94A3B8),
              ),
              padding: EdgeInsets.zero,
              constraints: const BoxConstraints(minWidth: 28, minHeight: 28),
              onPressed: () => widget.controller.openDashboard(0, 0),
            ),
          ],
        ),
      );
    });
  }

  Widget _buildEmptyState() {
    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 4),
          const Text(
            'GỢI Ý LỆNH NHANH',
            style: TextStyle(
              color: Color(0xFF64748B),
              fontSize: 14,
              fontWeight: FontWeight.w800,
              letterSpacing: 1.2,
            ),
          ),
          const SizedBox(height: 10),
          _buildPromptChip(
            icon: Icons.dashboard_outlined,
            label: 'Tổng quan vận hành hôm nay',
            prompt: 'Tóm tắt tổng quan công việc, OKRs và tình hình vận hành hôm nay.',
          ),
          const SizedBox(height: 8),
          _buildPromptChip(
            icon: Icons.track_changes_outlined,
            label: 'Kiểm tra tiến độ OKRs',
            prompt: 'Báo cáo tình hình thực thi các mục tiêu OKRs quan trọng quý này.',
          ),
          const SizedBox(height: 8),
          _buildPromptChip(
            icon: Icons.checklist_rtl_rounded,
            label: 'Nhiệm vụ cần ưu tiên giải quyết',
            prompt: 'Liệt kê danh sách các công việc và quyết định quan trọng cần Founder xử lý.',
          ),
          const SizedBox(height: 8),
          _buildPromptChip(
            icon: Icons.analytics_outlined,
            label: 'Báo cáo tóm tắt tài chính',
            prompt: 'Tạo báo cáo tóm tắt tài chính và các chỉ số vận hành gần nhất.',
          ),
        ],
      ),
    );
  }

  Widget _buildPromptChip({
    required IconData icon,
    required String label,
    required String prompt,
  }) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(10),
        onTap: () => _handleSubmitted(prompt),
        hoverColor: const Color(0xFF00F0FF).withValues(alpha: 0.08),
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
          decoration: BoxDecoration(
            color: const Color(0xFF0D172A).withValues(alpha: 0.8),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(
              color: const Color(0xFF1E293B),
              width: 1,
            ),
          ),
          child: Row(
            children: [
              Icon(
                icon,
                size: 15,
                color: const Color(0xFF38BDF8),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  label,
                  style: const TextStyle(
                    color: Color(0xFFCBD5E1),
                    fontSize: 14,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ),
              const Icon(
                Icons.arrow_forward_ios_rounded,
                size: 11,
                color: Color(0xFF64748B),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildMessageList(List<Map<String, String>> messages) {
    WidgetsBinding.instance.addPostFrameCallback((_) => _scrollToBottom());

    return ListView.builder(
      controller: _scrollController,
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      itemCount: messages.length,
      itemBuilder: (context, index) {
        final msg = messages[index];
        final isUser = msg['role'] == 'user';
        final text = msg['text'] ?? '';
        final status = msg['status'];

        return Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: Row(
            mainAxisAlignment:
                isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (!isUser) ...[
                Container(
                  width: 28,
                  height: 28,
                  margin: const EdgeInsets.only(right: 8, top: 2),
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: const LinearGradient(
                      colors: [Color(0xFF00D2FF), Color(0xFF0072FF)],
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: const Color(0xFF00D2FF).withValues(alpha: 0.3),
                        blurRadius: 6,
                      ),
                    ],
                  ),
                  child: const Icon(
                    Icons.psychology,
                    size: 16,
                    color: Colors.white,
                  ),
                ),
              ],
              Flexible(
                child: Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 14,
                    vertical: 10,
                  ),
                  decoration: BoxDecoration(
                    gradient: isUser
                        ? const LinearGradient(
                            colors: [Color(0xFF0072FF), Color(0xFF00D2FF)],
                            begin: Alignment.topLeft,
                            end: Alignment.bottomRight,
                          )
                        : null,
                    color: isUser
                        ? null
                        : const Color(0xFF0D172A).withValues(alpha: 0.95),
                    borderRadius: BorderRadius.only(
                      topLeft: const Radius.circular(14),
                      topRight: const Radius.circular(14),
                      bottomLeft: Radius.circular(isUser ? 14 : 4),
                      bottomRight: Radius.circular(isUser ? 4 : 14),
                    ),
                    border: isUser
                        ? null
                        : Border.all(
                            color: const Color(0xFF1E293B),
                            width: 1,
                          ),
                    boxShadow: [
                      BoxShadow(
                        color: isUser
                            ? const Color(0xFF00D2FF).withValues(alpha: 0.25)
                            : Colors.black.withValues(alpha: 0.35),
                        blurRadius: 10,
                        offset: const Offset(0, 2),
                      ),
                    ],
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      if (text.trim().isNotEmpty && text.trim() != '...')
                        SelectableText(
                          text.trim(),
                          style: TextStyle(
                            color: isUser ? const Color(0xFF04070E) : Colors.white,
                            fontSize: 14.5,
                            height: 1.45,
                            fontWeight: isUser ? FontWeight.w600 : FontWeight.w400,
                          ),
                        ),
                      if (status == 'streaming') ...[
                        if (text.trim().isNotEmpty && text.trim() != '...') const SizedBox(height: 6),
                        Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            SizedBox(
                              width: 14,
                              height: 14,
                              child: CircularProgressIndicator(
                                strokeWidth: 1.8,
                                valueColor: AlwaysStoppedAnimation<Color>(
                                  isUser ? Colors.black54 : const Color(0xFF00F0FF),
                                ),
                              ),
                            ),
                            const SizedBox(width: 8),
                            Text(
                              'Đang xử lý...',
                              style: TextStyle(
                                color: isUser
                                    ? Colors.black54
                                    : const Color(0xFF38BDF8),
                                fontSize: 14,
                                fontStyle: FontStyle.italic,
                              ),
                            ),
                          ],
                        ),
                      ],
                      if (status == 'error') ...[
                        const SizedBox(height: 6),
                        const Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(
                              Icons.error_outline,
                              size: 15,
                              color: Color(0xFFEF4444),
                            ),
                            SizedBox(width: 4),
                            Text(
                              'Lỗi phản hồi',
                              style: TextStyle(
                                color: Color(0xFFEF4444),
                                fontSize: 14,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ],
                        ),
                      ],
                    ],
                  ),
                ),
              ),
              if (isUser) ...[
                const SizedBox(width: 8),
                Container(
                  width: 28,
                  height: 28,
                  margin: const EdgeInsets.only(top: 2),
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: const Color(0xFF1E293B),
                    border: Border.all(
                      color: const Color(0xFF334155),
                      width: 1,
                    ),
                  ),
                  child: const Icon(
                    Icons.person,
                    size: 16,
                    color: Color(0xFF38BDF8),
                  ),
                ),
              ],
            ],
          ),
        );
      },
    );
  }

  Widget _buildVoiceListeningBanner() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
      color: const Color(0xFF00F0FF).withValues(alpha: 0.1),
      child: Row(
        children: [
          Container(
            width: 8,
            height: 8,
            decoration: BoxDecoration(
              color: const Color(0xFF00F0FF),
              shape: BoxShape.circle,
              boxShadow: [
                BoxShadow(
                  color: const Color(0xFF00F0FF).withValues(alpha: 0.8),
                  blurRadius: 6,
                ),
              ],
            ),
          ),
          const SizedBox(width: 10),
          const Expanded(
            child: Text(
              'Đang lắng nghe giọng nói... Bấm lại nút Mic để kết thúc.',
              style: TextStyle(
                color: Color(0xFF00F0FF),
                fontSize: 14,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          AnimatedBuilder(
            animation: _waveController,
            builder: (context, child) {
              return SizedBox(
                width: 60,
                height: 16,
                child: CustomPaint(
                  painter: AudioWaveformPainter(
                    animationValue: _waveController.value,
                    barCount: 10,
                    primaryColor: const Color(0xFF00F0FF),
                    secondaryColor: const Color(0xFF3B82F6),
                  ),
                ),
              );
            },
          ),
        ],
      ),
    );
  }

  Widget _buildInputBar() {
    return Container(
      padding: const EdgeInsets.fromLTRB(12, 10, 12, 12),
      decoration: const BoxDecoration(
        color: Color(0xFF070C18),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          // Speech to text / Mic button
          Obx(() {
            final isListening = widget.controller.isVoiceListening.value ||
                widget.controller.runtimeState.value ==
                    HologramRuntimeState.listening;

            return Tooltip(
              message: isListening
                  ? 'Dừng ghi âm & xử lý'
                  : 'Nói để chuyển thành văn bản (Speech to Text)',
              child: Material(
                color: Colors.transparent,
                child: InkWell(
                  borderRadius: BorderRadius.circular(10),
                  onTap: widget.controller.onTalkPressed,
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 200),
                    width: 40,
                    height: 40,
                    decoration: BoxDecoration(
                      color: isListening
                          ? const Color(0xFFEF4444).withValues(alpha: 0.2)
                          : const Color(0xFF0D172A),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(
                        color: isListening
                            ? const Color(0xFFEF4444)
                            : const Color(0xFF1E293B),
                        width: isListening ? 1.5 : 1,
                      ),
                      boxShadow: isListening
                          ? [
                              BoxShadow(
                                color: const Color(0xFFEF4444)
                                    .withValues(alpha: 0.4),
                                blurRadius: 10,
                              ),
                            ]
                          : null,
                    ),
                    child: Icon(
                      isListening
                          ? Icons.mic
                          : Icons.mic_none_rounded,
                      size: 20,
                      color: isListening
                          ? const Color(0xFFEF4444)
                          : const Color(0xFF00F0FF),
                    ),
                  ),
                ),
              ),
            );
          }),

          const SizedBox(width: 8),

          // Text Field (Exact height 40 matching the 2 buttons)
          Expanded(
            child: Container(
              height: 40,
              decoration: BoxDecoration(
                color: const Color(0xFF0D172A),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(
                  color: _focusNode.hasFocus
                      ? const Color(0xFF00F0FF).withValues(alpha: 0.6)
                      : const Color(0xFF1E293B),
                  width: 1,
                ),
              ),
              child: CallbackShortcuts(
                bindings: {
                  const SingleActivator(LogicalKeyboardKey.enter): () {
                    _handleSubmitted(_textController.text);
                  },
                },
                child: TextField(
                  controller: _textController,
                  focusNode: _focusNode,
                  maxLines: 1,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 14.5,
                  ),
                  decoration: const InputDecoration(
                    hintText: 'Nhập tin nhắn hoặc lệnh...',
                    hintStyle: TextStyle(
                      color: Color(0xFF64748B),
                      fontSize: 14,
                    ),
                    filled: false,
                    border: InputBorder.none,
                    enabledBorder: InputBorder.none,
                    focusedBorder: InputBorder.none,
                    disabledBorder: InputBorder.none,
                    errorBorder: InputBorder.none,
                    isDense: true,
                    contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 11),
                  ),
                ),
              ),
            ),
          ),

          const SizedBox(width: 8),

          // Send Button
          Material(
            color: Colors.transparent,
            child: InkWell(
              borderRadius: BorderRadius.circular(10),
              onTap: _isComposing
                  ? () => _handleSubmitted(_textController.text)
                  : null,
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 200),
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  gradient: _isComposing
                      ? const LinearGradient(
                          colors: [Color(0xFF00F0FF), Color(0xFF0072FF)],
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                        )
                      : null,
                  color: _isComposing ? null : const Color(0xFF0D172A),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(
                    color: _isComposing
                        ? const Color(0xFF00F0FF).withValues(alpha: 0.5)
                        : const Color(0xFF1E293B),
                    width: 1,
                  ),
                  boxShadow: _isComposing
                      ? [
                          BoxShadow(
                            color: const Color(0xFF00F0FF)
                                .withValues(alpha: 0.3),
                            blurRadius: 10,
                          ),
                        ]
                      : null,
                ),
                child: Icon(
                  Icons.send_rounded,
                  size: 18,
                  color: _isComposing ? const Color(0xFF04070E) : const Color(0xFF64748B),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
