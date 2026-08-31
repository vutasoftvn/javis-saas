import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/theme/app_theme.dart';
import '../../controllers/chat_controller.dart';
import '../../models/chat_models.dart';

class ChatSidebar extends StatelessWidget {
  final ChatController controller;
  final bool inDrawer;

  const ChatSidebar({
    super.key,
    required this.controller,
    this.inDrawer = false,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        color: AppTheme.surfaceDark,
        border: Border(right: BorderSide(color: AppTheme.borderDark)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header & New Chat button
          Container(
            padding: const EdgeInsets.all(16),
            decoration: const BoxDecoration(
              border: Border(bottom: BorderSide(color: AppTheme.borderDark)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text(
                      'AgentOS Chat',
                      style: TextStyle(
                        color: AppTheme.textDark,
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    if (inDrawer)
                      IconButton(
                        icon: const Icon(Icons.close, color: AppTheme.textMutedDark, size: 20),
                        onPressed: () => Get.back(),
                      ),
                  ],
                ),
                const SizedBox(height: 12),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    onPressed: () {
                      controller.createNewConversation();
                      if (inDrawer) Get.back();
                    },
                    icon: const Icon(Icons.add, size: 18),
                    label: const Text('New Chat'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppTheme.primary,
                      foregroundColor: const Color(0xFF04070E),
                      padding: const EdgeInsets.symmetric(vertical: 12),
                    ),
                  ),
                ),
              ],
            ),
          ),

          // Conversation List
          Expanded(
            child: Obx(() {
              if (controller.isLoading.value && controller.conversations.isEmpty) {
                return const Center(
                  child: CircularProgressIndicator(color: AppTheme.primary),
                );
              }
              if (controller.conversations.isEmpty) {
                return const Center(
                  child: Text(
                    'No conversations yet',
                    style: TextStyle(color: AppTheme.textMutedDark, fontSize: 13),
                  ),
                );
              }
              return ListView.builder(
                padding: const EdgeInsets.symmetric(vertical: 8),
                itemCount: controller.conversations.length,
                itemBuilder: (context, index) {
                  final conv = controller.conversations[index];
                  final isSelected = controller.activeConversation.value?.id == conv.id;
                  return _buildConversationItem(conv, isSelected);
                },
              );
            }),
          ),
        ],
      ),
    );
  }

  Widget _buildConversationItem(ChatConversation conv, bool isSelected) {
    return InkWell(
      onTap: () {
        controller.selectConversation(conv);
        if (inDrawer) Get.back();
      },
      child: Container(
        margin: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        decoration: BoxDecoration(
          color: isSelected ? AppTheme.primary.withValues(alpha: 0.15) : Colors.transparent,
          borderRadius: BorderRadius.circular(8),
          border: isSelected ? Border.all(color: AppTheme.primary.withValues(alpha: 0.5)) : null,
        ),
        child: Row(
          children: [
            Icon(
              Icons.chat_bubble_outline,
              size: 16,
              color: isSelected ? AppTheme.primary : AppTheme.textMutedDark,
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                conv.title,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  color: isSelected ? AppTheme.textDark : AppTheme.textMutedDark,
                  fontSize: 13,
                  fontWeight: isSelected ? FontWeight.w600 : FontWeight.normal,
                ),
              ),
            ),
            PopupMenuButton<String>(
              icon: const Icon(Icons.more_vert, size: 16, color: AppTheme.textDimDark),
              color: AppTheme.surfaceDark,
              onSelected: (val) {
                if (val == 'archive') {
                  controller.archiveConversation(conv.id);
                }
              },
              itemBuilder: (context) => [
                const PopupMenuItem(
                  value: 'archive',
                  child: Row(
                    children: [
                      Icon(Icons.archive_outlined, size: 16, color: AppTheme.textMutedDark),
                      SizedBox(width: 8),
                      Text('Archive', style: TextStyle(color: AppTheme.textDark, fontSize: 13)),
                    ],
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
