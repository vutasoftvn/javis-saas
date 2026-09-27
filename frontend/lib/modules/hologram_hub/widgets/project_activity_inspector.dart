import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:frontend/modules/hologram_hub/models/project_activity_models.dart';
import '../../../core/localization/locale_controller.dart';
import '../../../core/localization/supported_locale.dart';

class ProjectActivityInspector extends StatelessWidget {
  final String eventId;
  final String projectId;
  final ProjectActivityEvent? event;
  final VoidCallback? onClose;

  const ProjectActivityInspector({
    super.key,
    required this.eventId,
    required this.projectId,
    this.event,
    this.onClose,
  });

  bool _isEnglish() {
    if (Get.isRegistered<LocaleController>()) {
      return Get.find<LocaleController>().current.value == SupportedLocale.enUS;
    }
    return Get.locale?.languageCode == 'en';
  }

  @override
  Widget build(BuildContext context) {
    final isEn = _isEnglish();
    if (event == null) {
      return Center(
        child: Text(
          isEn ? 'Event not found' : 'Không tìm thấy sự kiện',
          style: TextStyle(
            color: Colors.white.withValues(alpha: 0.7),
          ),
        ),
      );
    }

    final e = event!;
    final agentName = e.agentProfile != null
        ? ProjectActivityEvent.formatAgentProfile(e.agentProfile, isEn: isEn)
        : null;

    return SingleChildScrollView(
      child: Container(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header with close button
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(6),
                      decoration: BoxDecoration(
                        color: const Color(0xFF6366F1).withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: const Icon(
                        Icons.receipt_long_rounded,
                        color: Color(0xFF818CF8),
                        size: 16,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      isEn ? 'Activity Details' : 'Chi tiết Hoạt động',
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 15,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
                if (onClose != null)
                  IconButton(
                    onPressed: onClose,
                    icon: const Icon(Icons.close, color: Colors.white70),
                  ),
              ],
            ),
            const Divider(color: Color(0x226366F1)),
            const SizedBox(height: 12),

            // Main summary banner
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: const Color(0xFF1E293B).withValues(alpha: 0.7),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(
                  color: const Color(0xFF334155),
                  width: 1,
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    isEn ? 'Title / Action' : 'Tiêu đề / Hành động',
                    style: TextStyle(
                      color: Colors.white.withValues(alpha: 0.5),
                      fontSize: 10.5,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    e.getFormattedTitle(isEn: isEn),
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 13.5,
                      fontWeight: FontWeight.w600,
                      height: 1.4,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 14),

            // Key metadata
            if (agentName != null)
              _buildField(
                label: isEn ? 'Agent Role' : 'Vai trò Trợ lý',
                value: agentName,
              ),

            // Event ID
            _buildField(
              label: isEn ? 'Event ID' : 'Mã sự kiện',
              value: e.eventId,
            ),

            // Correlation ID
            if (e.correlationId != null)
              _buildField(
                label: isEn ? 'Correlation ID' : 'Mã tương quan',
                value: e.correlationId!,
              ),

            // Source Reference
            if (e.sourceType != null)
              _buildField(
                label: isEn ? 'Source Type' : 'Loại nguồn',
                value: e.sourceType!.toUpperCase(),
              ),
            if (e.sourceId != null)
              _buildField(
                label: isEn ? 'Source ID' : 'Mã nguồn',
                value: e.sourceId!,
              ),

            // Status
            if (e.status != null)
              _buildField(
                label: isEn ? 'Status' : 'Trạng thái',
                value: e.formatStatus(isEn: isEn) ?? e.status!.toUpperCase(),
              ),

            // Kind
            _buildField(
              label: isEn ? 'Event Kind' : 'Loại sự kiện',
              value: '${e.kind} (${e.formatKind(isEn: isEn)})',
            ),

            // Phase
            if (e.phase != null)
              _buildField(
                label: isEn ? 'Phase' : 'Giai đoạn',
                value: e.phase!,
              ),

            // Actor
            _buildField(
              label: isEn ? 'Actor' : 'Tác nhân thực hiện',
              value: e.formatActor(isEn: isEn),
            ),

            // Safety Level
            if (e.classification != null && e.classification!.isNotEmpty)
              _buildField(
                label: isEn ? 'Classification' : 'Phân loại bảo mật',
                value: e.classification!,
              ),

            // Structured Summary parameters if present
            if (e.summaryData.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text(
                isEn ? 'Event Parameters (Allowlisted)' : 'Thông số sự kiện (Đã lọc an toàn)',
                style: const TextStyle(
                  color: Colors.white70,
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 8),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFF0F172A),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: const Color(0xFF334155)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: e.summaryData.entries.map((entry) {
                    return Padding(
                      padding: const EdgeInsets.only(bottom: 6),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            '${entry.key}: ',
                            style: const TextStyle(
                              color: Color(0xFF93C5FD),
                              fontSize: 11.5,
                              fontFamily: 'monospace',
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          Expanded(
                            child: Text(
                              '${entry.value}',
                              style: const TextStyle(
                                color: Colors.white70,
                                fontSize: 11.5,
                                fontFamily: 'monospace',
                              ),
                            ),
                          ),
                        ],
                      ),
                    );
                  }).toList(),
                ),
              ),
            ],

            const SizedBox(height: 14),
            if (e.classification == 'restricted')
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.orange.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.orange.withValues(alpha: 0.3)),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.info_outline, color: Colors.orange, size: 20),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        isEn
                            ? 'Restricted: Content has been hidden for security.'
                            : 'Restricted: Nội dung đã được ẩn để bảo mật.',
                        style: const TextStyle(
                          color: Colors.orange,
                          fontSize: 12,
                        ),
                      ),
                    ),
                  ],
                ),
              ),

            const SizedBox(height: 20),
            Text(
              isEn
                  ? 'Note: Raw prompts, tokens, secrets, and sensitive payloads are not displayed for security.'
                  : 'Ghi chú: Token, prompt thô, bí mật và dữ liệu nhạy cảm được ẩn để đảm bảo an toàn.',
              style: const TextStyle(
                color: Colors.white54,
                fontSize: 11,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildField({required String label, required String value}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: TextStyle(
              color: Colors.white.withValues(alpha: 0.55),
              fontSize: 10.5,
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: 3),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
            decoration: BoxDecoration(
              color: const Color(0xFF1E293B).withValues(alpha: 0.8),
              borderRadius: BorderRadius.circular(6),
              border: Border.all(
                color: const Color(0xFF334155),
                width: 0.8,
              ),
            ),
            child: Text(
              value,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 11.5,
                fontFamily: 'monospace',
              ),
              maxLines: 3,
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      ),
    );
  }
}
