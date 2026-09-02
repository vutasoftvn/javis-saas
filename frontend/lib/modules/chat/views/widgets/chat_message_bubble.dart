import 'package:flutter/material.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/widgets/app_markdown_body.dart';
import '../../models/chat_models.dart';

class ChatMessageBubble extends StatelessWidget {
  final ChatMessage msg;

  const ChatMessageBubble({super.key, required this.msg});

  @override
  Widget build(BuildContext context) {
    final isUser = msg.role == 'user';
    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.only(bottom: 16),
        constraints: const BoxConstraints(maxWidth: 720),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: isUser ? AppTheme.primary.withValues(alpha: 0.15) : AppTheme.surfaceDark,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: isUser ? AppTheme.primary.withValues(alpha: 0.3) : AppTheme.borderDark,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  isUser ? Icons.person : Icons.smart_toy,
                  size: 14,
                  color: isUser ? AppTheme.primary : AppTheme.secondary,
                ),
                const SizedBox(width: 6),
                Text(
                  isUser ? 'You' : 'Assistant',
                  style: TextStyle(
                    color: isUser ? AppTheme.primary : AppTheme.secondary,
                    fontSize: 11,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            if (msg.content.isEmpty && msg.status == 'started')
              const Row(
                children: [
                  SizedBox(
                    width: 14,
                    height: 14,
                    child: CircularProgressIndicator(strokeWidth: 2, color: AppTheme.primary),
                  ),
                  SizedBox(width: 8),
                  Text('Generating answer...', style: TextStyle(color: AppTheme.textMutedDark, fontSize: 13)),
                ],
              )
            else
              AppMarkdownBody(
                data: msg.content,
                selectable: true,
                styleSheet: MarkdownStyleSheet(
                  p: const TextStyle(color: AppTheme.textDark, fontSize: 14, height: 1.5),
                  code: const TextStyle(color: AppTheme.secondaryLight, backgroundColor: AppTheme.surfaceDarkLighter),
                  codeblockDecoration: BoxDecoration(
                    color: AppTheme.surfaceDarkLighter,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: AppTheme.borderDark),
                  ),
                ),
              ),
            if (msg.attachments.isNotEmpty) ...[
              const SizedBox(height: 8),
              Wrap(
                spacing: 6,
                runSpacing: 6,
                children: msg.attachments.map((a) => _buildAttachmentChip(a)).toList(),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildAttachmentChip(ChatAttachment attachment) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDarkLighter,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: AppTheme.borderDark),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.attach_file, size: 12, color: AppTheme.primary),
          const SizedBox(width: 4),
          Text(
            attachment.fileName,
            style: const TextStyle(color: AppTheme.textDark, fontSize: 11),
          ),
        ],
      ),
    );
  }
}
