import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:get/get.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:frontend/modules/hologram_hub/controllers/hologram_hub_controller.dart';

class HubChatMessageBubble extends StatelessWidget {
  final Map<String, dynamic> message;
  final HologramHubController controller;

  const HubChatMessageBubble({
    super.key,
    required this.message,
    required this.controller,
  });

  @override
  Widget build(BuildContext context) {
    final isUser = message['role'] == 'user';
    final text = (message['text'] as String?) ?? '';
    final status = message['status'] as String?;

    final rawProposals = message['proposals'];
    List<Map<String, dynamic>> proposalsList = [];
    if (rawProposals is List) {
      proposalsList = rawProposals.map((p) => Map<String, dynamic>.from(p as Map)).toList();
    } else if (!isUser &&
        controller.needsYouItems.isNotEmpty &&
        (text.contains('Cần bạn xử lý') ||
            text.contains('đề xuất') ||
            text.contains('Duyệt') ||
            text.contains('duyệt'))) {
      final openItems = controller.needsYouItems.where((item) => item['status'] != 'RESOLVED').toList();
      if (openItems.isNotEmpty) {
        proposalsList = [Map<String, dynamic>.from(openItems.first as Map)];
      }
    }

    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        mainAxisAlignment: isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
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
              child: const Icon(Icons.psychology, size: 16, color: Color(0xFF94A3B8)),
            ),
          ],
          Flexible(
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
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
                                if (uri != null) launchUrl(uri, mode: LaunchMode.externalApplication);
                              }
                            },
                            styleSheet: MarkdownStyleSheet(
                              p: const TextStyle(color: Color(0xFF94A3B8), fontSize: 14.5, height: 1.5),
                              strong: const TextStyle(color: Color(0xFFCBD5E1), fontWeight: FontWeight.bold, fontSize: 14.5),
                              em: const TextStyle(color: Color(0xFF64748B), fontStyle: FontStyle.italic, fontSize: 14.5),
                              code: const TextStyle(color: Color(0xFF94A3B8), backgroundColor: Color(0xFF1E293B), fontFamily: 'monospace', fontSize: 13),
                              codeblockDecoration: BoxDecoration(
                                color: Colors.white.withValues(alpha: 0.04),
                                borderRadius: BorderRadius.circular(8),
                                border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
                              ),
                              codeblockPadding: const EdgeInsets.all(10),
                              listBullet: const TextStyle(color: Color(0xFF64748B), fontSize: 14.5),
                              a: const TextStyle(color: Color(0xFF38BDF8), decoration: TextDecoration.underline),
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
                            valueColor: AlwaysStoppedAnimation<Color>(Color(0xFF94A3B8)),
                          ),
                        ),
                        SizedBox(width: 8),
                        Text(
                          'Đang xử lý...',
                          style: TextStyle(color: Color(0xFF94A3B8), fontSize: 14, fontStyle: FontStyle.italic),
                        ),
                      ],
                    ),
                  ],
                  if (status == 'error') ...[
                    const SizedBox(height: 6),
                    const Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.error_outline, size: 15, color: Color(0xFFEF4444)),
                        SizedBox(width: 4),
                        Text(
                          'Lỗi phản hồi',
                          style: TextStyle(color: Color(0xFFEF4444), fontSize: 14, fontWeight: FontWeight.w600),
                        ),
                      ],
                    ),
                  ],
                  if (!isUser && proposalsList.isNotEmpty) ...[
                    for (final prop in proposalsList) _buildNeedsYouActionCard(prop),
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
              child: const Icon(Icons.person, size: 16, color: Color(0xFF38BDF8)),
            ),
          ],
        ],
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
      final isResolved = rawStatus == 'RESOLVED' || controller.resolvedProposalIds.contains(proposalId);
      final isSnoozed = rawStatus == 'SNOOZED' || controller.snoozedProposalIds.contains(proposalId);
      final isP0 = priority == 'P0';

      final accentColor = isResolved
          ? const Color(0xFF10B981)
          : (isSnoozed ? const Color(0xFFF59E0B) : (isP0 ? const Color(0xFFEF4444) : const Color(0xFF14B8A6)));

      return Container(
        margin: const EdgeInsets.only(top: 10),
        decoration: BoxDecoration(
          color: const Color(0xFF0F172A).withValues(alpha: 0.85),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: accentColor.withValues(alpha: 0.45), width: 1.2),
          boxShadow: [
            BoxShadow(color: accentColor.withValues(alpha: 0.12), blurRadius: 10, spreadRadius: 1),
          ],
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                decoration: BoxDecoration(
                  color: accentColor.withValues(alpha: 0.12),
                  border: Border(bottom: BorderSide(color: accentColor.withValues(alpha: 0.25), width: 0.8)),
                ),
                child: Row(
                  children: [
                    Icon(
                      isResolved ? Icons.check_circle_rounded : (isSnoozed ? Icons.snooze_rounded : Icons.notification_important_rounded),
                      size: 15,
                      color: accentColor,
                    ),
                    const SizedBox(width: 6),
                    Text(
                      'CẦN BẠN XỬ LÝ',
                      style: TextStyle(color: accentColor, fontSize: 11.5, fontWeight: FontWeight.w800, letterSpacing: 0.8),
                    ),
                    const Spacer(),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: (isP0 ? const Color(0xFFEF4444) : const Color(0xFF38BDF8)).withValues(alpha: 0.2),
                        borderRadius: BorderRadius.circular(4),
                        border: Border.all(
                          color: (isP0 ? const Color(0xFFEF4444) : const Color(0xFF38BDF8)).withValues(alpha: 0.5),
                          width: 0.6,
                        ),
                      ),
                      child: Text(priority, style: TextStyle(color: isP0 ? const Color(0xFFEF4444) : const Color(0xFF38BDF8), fontSize: 10, fontWeight: FontWeight.w700)),
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
              Padding(
                padding: const EdgeInsets.all(12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(action, style: const TextStyle(color: Color(0xFFF8FAFC), fontSize: 13.5, fontWeight: FontWeight.w700, height: 1.35)),
                    if (reason.isNotEmpty) ...[
                      const SizedBox(height: 5),
                      Text(reason, style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 12, height: 1.35), maxLines: 3, overflow: TextOverflow.ellipsis),
                    ],
                    const SizedBox(height: 10),
                    if (isResolved)
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.symmetric(vertical: 7, horizontal: 10),
                        decoration: BoxDecoration(
                          color: const Color(0xFF10B981).withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(color: const Color(0xFF10B981).withValues(alpha: 0.4)),
                        ),
                        child: const Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.check_circle_outline_rounded, size: 14, color: Color(0xFF10B981)),
                            SizedBox(width: 6),
                            Expanded(
                              child: Text(
                                'Đã xác nhận & khởi tạo thành công vào hệ thống',
                                textAlign: TextAlign.center,
                                style: TextStyle(color: Color(0xFF10B981), fontSize: 12, fontWeight: FontWeight.w600),
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
                                  ? () => controller.resolveNeedsYouItem(proposalId, actionName: action)
                                  : null,
                              child: Container(
                                padding: const EdgeInsets.symmetric(vertical: 8),
                                decoration: BoxDecoration(
                                  gradient: const LinearGradient(colors: [Color(0xFF14B8A6), Color(0xFF0284C7)]),
                                  borderRadius: BorderRadius.circular(6),
                                  boxShadow: [
                                    BoxShadow(color: const Color(0xFF14B8A6).withValues(alpha: 0.3), blurRadius: 6),
                                  ],
                                ),
                                child: const Row(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: [
                                    Icon(Icons.check_rounded, size: 15, color: Color(0xFF0F172A)),
                                    SizedBox(width: 5),
                                    Text('Xác nhận & Khởi tạo', style: TextStyle(color: Color(0xFF0F172A), fontSize: 12.5, fontWeight: FontWeight.w700)),
                                  ],
                                ),
                              ),
                            ),
                          ),
                          if (proposalId.isNotEmpty) ...[
                            const SizedBox(width: 8),
                            InkWell(
                              borderRadius: BorderRadius.circular(6),
                              onTap: () => controller.snoozeNeedsYouItem(proposalId, actionName: action),
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
}
