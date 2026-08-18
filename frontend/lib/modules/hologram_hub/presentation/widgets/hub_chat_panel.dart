import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:get/get.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../controllers/hologram_hub_controller.dart';
import 'audio_waveform_painter.dart';
import 'miva_hologram_core.dart';

import 'glass_card.dart';

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
    return GlassCard(
      padding: EdgeInsets.zero,
      borderRadius: 16,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // 1. HEADER
          _buildHeader(),

          Divider(
            height: 1,
            thickness: 1,
            color: const Color(0xFF14B8A6).withValues(alpha: 0.12),
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

          Divider(
            height: 1,
            thickness: 1,
            color: const Color(0xFF14B8A6).withValues(alpha: 0.12),
          ),

          // 4. BOTTOM INPUT BAR
          _buildInputBar(),
        ],
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
          color: const Color(0xFF14B8A6).withValues(alpha: 0.05),
          borderRadius: const BorderRadius.vertical(top: Radius.circular(15)),
          border: Border(
            bottom: BorderSide(
              color: const Color(0xFF14B8A6).withValues(alpha: 0.12),
              width: 0.5,
            ),
          ),
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(6),
              decoration: BoxDecoration(
                color: const Color(0xFF14B8A6).withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(
                  color: const Color(0xFF14B8A6).withValues(alpha: 0.4),
                  width: 1,
                ),
              ),
              child: const Icon(
                Icons.smart_toy_outlined,
                size: 16,
                color: Color(0xFF14B8A6),
              ),
            ),
            const Spacer(),
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
            const SizedBox(width: 4),
            // Close / Hide chat panel
            IconButton(
              tooltip: 'Ẩn khung chat',
              icon: const Icon(
                Icons.close_rounded,
                size: 18,
                color: Color(0xFF94A3B8),
              ),
              padding: EdgeInsets.zero,
              constraints: const BoxConstraints(minWidth: 28, minHeight: 28),
              onPressed: () => widget.controller.closeChatInput(),
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
          const SizedBox(height: 8),
          _buildPromptChip(
            icon: Icons.auto_graph_rounded,
            label: 'Lập chu kỳ chiến lược N tuần',
            prompt: 'Lập chu kỳ 6 tuần kiểm chứng PMF cho Dự án',
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
        hoverColor: const Color(0xFF14B8A6).withValues(alpha: 0.08),
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
          decoration: BoxDecoration(
            color: Colors.transparent,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(
              color: const Color(0xFF334155).withValues(alpha: 0.6),
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

  Widget _buildMessageList(List<Map<String, dynamic>> messages) {
    WidgetsBinding.instance.addPostFrameCallback((_) => _scrollToBottom());

    return Align(
      alignment: Alignment.bottomCenter,
      child: ListView.builder(
        shrinkWrap: true,
        controller: _scrollController,
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        itemCount: messages.length,
        itemBuilder: (context, index) {
        final msg = messages[index];
        final isUser = msg['role'] == 'user';
        final text = (msg['text'] as String?) ?? '';
        final status = msg['status'] as String?;

        final rawProposals = msg['proposals'];
        List<Map<String, dynamic>> proposalsList = [];
        if (rawProposals is List) {
          proposalsList = rawProposals.map((p) => Map<String, dynamic>.from(p as Map)).toList();
        } else if (!isUser && widget.controller.needsYouItems.isNotEmpty &&
            (text.contains('Cần bạn xử lý') || text.contains('đề xuất') || text.contains('Duyệt') || text.contains('duyệt'))) {
          final openItems = widget.controller.needsYouItems
              .where((item) => item['status'] != 'RESOLVED')
              .toList();
          if (openItems.isNotEmpty && index == messages.length - 1) {
            proposalsList = [Map<String, dynamic>.from(openItems.first as Map)];
          }
        }

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
                    color: Colors.transparent,
                    border: Border.all(
                      color: const Color(0xFF64748B).withValues(alpha: 0.40),
                      width: 1,
                    ),
                  ),
                  child: const Icon(
                    Icons.psychology,
                    size: 16,
                    color: Color(0xFF94A3B8),
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
                    color: Colors.transparent,
                    borderRadius: BorderRadius.only(
                      topLeft: Radius.circular(isUser ? 14 : 3),
                      topRight: Radius.circular(isUser ? 3 : 14),
                      bottomLeft: const Radius.circular(14),
                      bottomRight: const Radius.circular(14),
                    ),
                    border: Border.all(
                      color: isUser
                          ? const Color(0xFF14B8A6).withValues(alpha: 0.35)
                          : const Color(0xFF64748B).withValues(alpha: 0.40),
                      width: 1,
                    ),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      if (text.trim().isNotEmpty && text.trim() != '...')
                        isUser
                            ? SelectableText(
                                text.trim(),
                                style: const TextStyle(
                                  color: Color(0xFF94A3B8),
                                  fontSize: 14.5,
                                  height: 1.45,
                                  fontWeight: FontWeight.w500,
                                ),
                              )
                            : MarkdownBody(
                                data: text.trim(),
                                selectable: true,

                                onTapLink: (text, href, title) {
                                  if (href != null) {
                                    final uri = Uri.tryParse(href);
                                    if (uri != null) {
                                      launchUrl(uri,
                                          mode: LaunchMode.externalApplication);
                                    }
                                  }
                                },
                                styleSheet: MarkdownStyleSheet(
                                  p: const TextStyle(
                                    color: Color(0xFF94A3B8),
                                    fontSize: 14.5,
                                    height: 1.5,
                                  ),
                                  strong: const TextStyle(
                                    color: Color(0xFFCBD5E1),
                                    fontWeight: FontWeight.bold,
                                    fontSize: 14.5,
                                  ),
                                  em: const TextStyle(
                                    color: Color(0xFF64748B),
                                    fontStyle: FontStyle.italic,
                                    fontSize: 14.5,
                                  ),
                                  code: const TextStyle(
                                    color: Color(0xFF94A3B8),
                                    backgroundColor: Color(0xFF1E293B),
                                    fontFamily: 'monospace',
                                    fontSize: 13,
                                  ),
                                  codeblockDecoration: BoxDecoration(
                                    color: Colors.white.withValues(alpha: 0.04),
                                    borderRadius: BorderRadius.circular(8),
                                    border: Border.all(
                                        color: Colors.white.withValues(alpha: 0.08)),
                                  ),
                                  codeblockPadding: const EdgeInsets.all(10),
                                  listBullet: const TextStyle(
                                    color: Color(0xFF64748B),
                                    fontSize: 14.5,
                                  ),
                                  a: const TextStyle(
                                    color: Color(0xFF38BDF8),
                                    decoration: TextDecoration.underline,
                                  ),
                                ),
                              ),
                      if (status == 'streaming') ...[
                        if (text.trim().isNotEmpty && text.trim() != '...') const SizedBox(height: 6),
                        const Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            SizedBox(
                              width: 14,
                              height: 14,
                              child: CircularProgressIndicator(
                                strokeWidth: 1.8,
                                valueColor: AlwaysStoppedAnimation<Color>(
                                  Color(0xFF94A3B8),
                                ),
                              ),
                            ),
                            SizedBox(width: 8),
                            Text(
                              'Đang xử lý...',
                              style: TextStyle(
                                color: Color(0xFF94A3B8),
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
                      if (!isUser && proposalsList.isNotEmpty) ...[
                        for (final prop in proposalsList)
                          _buildNeedsYouActionCard(prop),
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
                    color: Colors.transparent,
                    border: Border.all(
                      color: const Color(0xFF14B8A6).withValues(alpha: 0.35),
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
    ),
    );
  }

  Widget _buildNeedsYouActionCard(Map<String, dynamic> proposal) {
    final proposalId = (proposal['id'] ?? proposal['proposal_id'] ?? '').toString();
    final action = (proposal['requested_action'] as String?) ?? 'Yêu cầu xử lý / phê duyệt';
    final reason = (proposal['reason'] as String?) ?? '';
    final priority = (proposal['priority'] as String?) ?? 'P1';
    final rawStatus = (proposal['status'] as String?) ?? 'OPEN';

    return Obx(() {
      final isResolved = rawStatus == 'RESOLVED' || widget.controller.resolvedProposalIds.contains(proposalId);
      final isSnoozed = rawStatus == 'SNOOZED' || widget.controller.snoozedProposalIds.contains(proposalId);
      final isP0 = priority == 'P0';

      final accentColor = isResolved
          ? const Color(0xFF10B981)
          : (isSnoozed
              ? const Color(0xFFF59E0B)
              : (isP0 ? const Color(0xFFEF4444) : const Color(0xFF14B8A6)));

      return Container(
        margin: const EdgeInsets.only(top: 10),
        decoration: BoxDecoration(
          color: const Color(0xFF0F172A).withValues(alpha: 0.85),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: accentColor.withValues(alpha: 0.45),
            width: 1.2,
          ),
          boxShadow: [
            BoxShadow(
              color: accentColor.withValues(alpha: 0.12),
              blurRadius: 10,
              spreadRadius: 1,
            ),
          ],
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Top Accent Header
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                decoration: BoxDecoration(
                  color: accentColor.withValues(alpha: 0.12),
                  border: Border(
                    bottom: BorderSide(
                      color: accentColor.withValues(alpha: 0.25),
                      width: 0.8,
                    ),
                  ),
                ),
                child: Row(
                  children: [
                    Icon(
                      isResolved
                          ? Icons.check_circle_rounded
                          : (isSnoozed
                              ? Icons.snooze_rounded
                              : Icons.notification_important_rounded),
                      size: 15,
                      color: accentColor,
                    ),
                    const SizedBox(width: 6),
                    Text(
                      'CẦN BẠN XỬ LÝ',
                      style: TextStyle(
                        color: accentColor,
                        fontSize: 11.5,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 0.8,
                      ),
                    ),
                    const Spacer(),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: (isP0 ? const Color(0xFFEF4444) : const Color(0xFF38BDF8))
                            .withValues(alpha: 0.2),
                        borderRadius: BorderRadius.circular(4),
                        border: Border.all(
                          color: (isP0 ? const Color(0xFFEF4444) : const Color(0xFF38BDF8))
                              .withValues(alpha: 0.5),
                          width: 0.6,
                        ),
                      ),
                      child: Text(
                        priority,
                        style: TextStyle(
                          color: isP0 ? const Color(0xFFEF4444) : const Color(0xFF38BDF8),
                          fontSize: 10,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                    const SizedBox(width: 6),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: (isResolved
                                ? const Color(0xFF10B981)
                                : (isSnoozed ? const Color(0xFFF59E0B) : const Color(0xFF14B8A6)))
                            .withValues(alpha: 0.2),
                        borderRadius: BorderRadius.circular(4),
                        border: Border.all(
                          color: (isResolved
                                  ? const Color(0xFF10B981)
                                  : (isSnoozed ? const Color(0xFFF59E0B) : const Color(0xFF14B8A6)))
                              .withValues(alpha: 0.5),
                          width: 0.6,
                        ),
                      ),
                      child: Text(
                        isResolved
                            ? 'ĐÃ DUYỆT'
                            : (isSnoozed ? 'ĐÃ HOÃN' : 'CHỜ XÁC NHẬN'),
                        style: TextStyle(
                          color: isResolved
                              ? const Color(0xFF10B981)
                              : (isSnoozed ? const Color(0xFFF59E0B) : const Color(0xFF14B8A6)),
                          fontSize: 10,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                  ],
                ),
              ),

              // Body content
              Padding(
                padding: const EdgeInsets.all(12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      action,
                      style: const TextStyle(
                        color: Color(0xFFF8FAFC),
                        fontSize: 13.5,
                        fontWeight: FontWeight.w700,
                        height: 1.35,
                      ),
                    ),
                    if (reason.isNotEmpty) ...[
                      const SizedBox(height: 5),
                      Text(
                        reason,
                        style: const TextStyle(
                          color: Color(0xFF94A3B8),
                          fontSize: 12,
                          height: 1.35,
                        ),
                        maxLines: 3,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                    const SizedBox(height: 10),

                    // Actions
                    if (isResolved)
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.symmetric(vertical: 7, horizontal: 10),
                        decoration: BoxDecoration(
                          color: const Color(0xFF10B981).withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(
                            color: const Color(0xFF10B981).withValues(alpha: 0.4),
                          ),
                        ),
                        child: const Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.check_circle_outline_rounded,
                                size: 14, color: Color(0xFF10B981)),
                            SizedBox(width: 6),
                            Expanded(
                              child: Text(
                                'Đã xác nhận & khởi tạo thành công vào hệ thống',
                                textAlign: TextAlign.center,
                                style: TextStyle(
                                  color: Color(0xFF10B981),
                                  fontSize: 12,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ),
                          ],
                        ),
                      )
                    else if (isSnoozed)
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.symmetric(vertical: 7, horizontal: 10),
                        decoration: BoxDecoration(
                          color: const Color(0xFFF59E0B).withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(
                            color: const Color(0xFFF59E0B).withValues(alpha: 0.4),
                          ),
                        ),
                        child: const Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.snooze_rounded,
                                size: 14, color: Color(0xFFF59E0B)),
                            SizedBox(width: 6),
                            Expanded(
                              child: Text(
                                'Đã tạm hoãn đề xuất này',
                                textAlign: TextAlign.center,
                                style: TextStyle(
                                  color: Color(0xFFF59E0B),
                                  fontSize: 12,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ),
                          ],
                        ),
                      )
                    else
                      Row(
                        children: [
                          Expanded(
                            child: InkWell(
                              borderRadius: BorderRadius.circular(6),
                              onTap: proposalId.isNotEmpty
                                  ? () => widget.controller.resolveNeedsYouItem(proposalId, actionName: action)
                                  : null,
                              child: Container(
                                padding: const EdgeInsets.symmetric(vertical: 8),
                                decoration: BoxDecoration(
                                  gradient: const LinearGradient(
                                    colors: [Color(0xFF14B8A6), Color(0xFF0284C7)],
                                  ),
                                  borderRadius: BorderRadius.circular(6),
                                  boxShadow: [
                                    BoxShadow(
                                      color: const Color(0xFF14B8A6).withValues(alpha: 0.3),
                                      blurRadius: 6,
                                    ),
                                  ],
                                ),
                                child: const Row(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: [
                                    Icon(
                                      Icons.check_rounded,
                                      size: 15,
                                      color: Color(0xFF0F172A),
                                    ),
                                    SizedBox(width: 5),
                                    Text(
                                      'Xác nhận & Khởi tạo',
                                      style: TextStyle(
                                        color: Color(0xFF0F172A),
                                        fontSize: 12.5,
                                        fontWeight: FontWeight.w700,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          ),
                          if (proposalId.isNotEmpty) ...[
                            const SizedBox(width: 8),
                            InkWell(
                              borderRadius: BorderRadius.circular(6),
                              onTap: () => widget.controller.snoozeNeedsYouItem(proposalId, actionName: action),
                              child: Container(
                                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                                decoration: BoxDecoration(
                                  color: Colors.white.withValues(alpha: 0.05),
                                  borderRadius: BorderRadius.circular(6),
                                  border: Border.all(
                                    color: Colors.white.withValues(alpha: 0.15),
                                  ),
                                ),
                                child: const Row(
                                  children: [
                                    Icon(
                                      Icons.snooze_rounded,
                                      size: 13,
                                      color: Color(0xFF94A3B8),
                                    ),
                                    SizedBox(width: 4),
                                    Text(
                                      'Hoãn',
                                      style: TextStyle(
                                        color: Color(0xFF94A3B8),
                                        fontSize: 11.5,
                                        fontWeight: FontWeight.w500,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          ],
                        ],
                      ),
                  ],
                ),
              ),
            ],
          ),
        ),
      );
    });
  }

  Widget _buildVoiceListeningBanner() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
      color: const Color(0xFF14B8A6).withValues(alpha: 0.1),
      child: Row(
        children: [
          Container(
            width: 8,
            height: 8,
            decoration: BoxDecoration(
              color: const Color(0xFF14B8A6),
              shape: BoxShape.circle,
              boxShadow: [
                BoxShadow(
                  color: const Color(0xFF14B8A6).withValues(alpha: 0.8),
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
                color: Color(0xFF14B8A6),
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
                    primaryColor: const Color(0xFF14B8A6),
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
      decoration: BoxDecoration(
        color: const Color(0xFF070C18).withValues(alpha: 0.40),
        borderRadius: const BorderRadius.vertical(bottom: Radius.circular(15)),
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
                  borderRadius: BorderRadius.circular(100),
                  onTap: widget.controller.onTalkPressed,
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 200),
                    width: 40,
                    height: 40,
                    decoration: BoxDecoration(
                      color: isListening
                          ? const Color(0xFFEF4444).withValues(alpha: 0.15)
                          : Colors.transparent,
                      borderRadius: BorderRadius.circular(100),
                      border: Border.all(
                        color: isListening
                            ? const Color(0xFFEF4444)
                            : const Color(0xFF334155).withValues(alpha: 0.8),
                        width: 1,
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
                          : const Color(0xFF94A3B8),
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
                color: Colors.transparent,
                borderRadius: BorderRadius.circular(100),
                border: Border.all(
                  color: _focusNode.hasFocus
                      ? const Color(0xFF14B8A6).withValues(alpha: 0.5)
                      : const Color(0xFF334155).withValues(alpha: 0.8),
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
                    color: Color(0xFF94A3B8),
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
                    contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 11),
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
              borderRadius: BorderRadius.circular(100),
              onTap: _isComposing
                  ? () => _handleSubmitted(_textController.text)
                  : null,
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 200),
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: Colors.transparent,
                  borderRadius: BorderRadius.circular(100),
                  border: Border.all(
                    color: _isComposing
                        ? const Color(0xFF14B8A6).withValues(alpha: 0.7)
                        : const Color(0xFF334155).withValues(alpha: 0.8),
                    width: 1,
                  ),
                  boxShadow: _isComposing
                      ? [
                          BoxShadow(
                            color: const Color(0xFF14B8A6)
                                .withValues(alpha: 0.25),
                            blurRadius: 8,
                          ),
                        ]
                      : null,
                ),
                child: Icon(
                  Icons.send_rounded,
                  size: 18,
                  color: _isComposing ? const Color(0xFF14B8A6) : const Color(0xFF64748B),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
