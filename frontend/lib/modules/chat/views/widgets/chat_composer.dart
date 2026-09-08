import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/localization/app_translations.dart';
import '../../controllers/chat_controller.dart';
import '../../models/data_access_declaration.dart';

class ChatComposer extends StatelessWidget {
  final ChatController controller;

  const ChatComposer({super.key, required this.controller});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: const BoxDecoration(
        color: AppTheme.surfaceDarkHeader,
        border: Border(top: BorderSide(color: AppTheme.borderDark)),
      ),
      child: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildDataAccessSelector(),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: TextField(
                    key: const Key('chat_message_field'),
                    controller: controller.textController,
                    style: const TextStyle(color: AppTheme.textDark, fontSize: 14),
                    minLines: 1,
                    maxLines: 4,
                    decoration: InputDecoration(
                      hintText: L10nKey.chatComposerHint.tr,
                      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                    ),
                    onSubmitted: (_) => controller.sendMessage(),
                  ),
                ),
                const SizedBox(width: 8),
                Obx(() {
                  final canSend = controller.canSendMessage;
                  return IconButton.filled(
                    onPressed: canSend ? () => controller.sendMessage() : null,
                    icon: const Icon(Icons.send, size: 18),
                    style: IconButton.styleFrom(
                      backgroundColor: canSend ? AppTheme.primary : AppTheme.borderDark,
                      foregroundColor: const Color(0xFF04070E),
                    ),
                  );
                }),
              ],
            ),
            Obx(() {
              final reason = controller.sendBlockedReason.value;
              if (reason.isEmpty) return const SizedBox.shrink();
              return Padding(
                padding: const EdgeInsets.only(top: 6),
                child: Row(
                  children: [
                    Expanded(
                      child: Text(
                        reason,
                        style: const TextStyle(color: AppTheme.warning, fontSize: 12),
                      ),
                    ),
                    // Retry chỉ gửi lại nội dung đã gõ khi user chủ động bấm —
                    // không auto-resubmit, giữ nguyên hành vi optimistic rollback
                    // của sendMessage() (đã xoá message optimistic + trả text về ô nhập).
                    TextButton(
                      key: const Key('chat_retry_button'),
                      onPressed: () => controller.sendMessage(),
                      style: TextButton.styleFrom(
                        padding: const EdgeInsets.symmetric(horizontal: 8),
                        minimumSize: Size.zero,
                        tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                      ),
                      child: const Text(
                        'Retry',
                        style: TextStyle(color: AppTheme.primary, fontSize: 12, fontWeight: FontWeight.w600),
                      ),
                    ),
                  ],
                ),
              );
            }),
          ],
        ),
      ),
    );
  }

  Widget _buildDataAccessSelector() {
    return Obx(() {
      final declaration = controller.dataAccess.value;
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Data access classification',
            style: TextStyle(color: AppTheme.textMutedDark, fontSize: 11, fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 6),
          Wrap(
            spacing: 8,
            runSpacing: 4,
            children: DataAccessCategory.values.map((category) {
              final selected = declaration.categories.contains(category);
              return FilterChip(
                label: Text(category.label, style: const TextStyle(fontSize: 12)),
                selected: selected,
                onSelected: (_) => controller.toggleDataAccessCategory(category),
                selectedColor: AppTheme.primary.withValues(alpha: 0.25),
                backgroundColor: AppTheme.surfaceDark,
                labelStyle: TextStyle(color: selected ? AppTheme.primary : AppTheme.textMutedDark),
              );
            }).toList(),
          ),
          if (declaration.requiresSubjectReference) ...[
            const SizedBox(height: 8),
            TextField(
              key: const Key('chat_subject_reference_field'),
              style: const TextStyle(color: AppTheme.textDark, fontSize: 13),
              decoration: const InputDecoration(
                hintText: 'Subject reference (who this personal data is about)',
                isDense: true,
                contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              ),
              onChanged: controller.setDataAccessSubjectReference,
            ),
            if (!declaration.hasSubjectReference) ...[
              const SizedBox(height: 4),
              const Text(
                'Add a subject reference before sending personal data.',
                style: TextStyle(color: AppTheme.warning, fontSize: 11),
              ),
            ],
          ],
        ],
      );
    });
  }
}
