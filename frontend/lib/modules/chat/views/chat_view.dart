import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:get/get.dart';

import '../../../core/theme/app_theme.dart';
import '../../../shared/widgets/ai_advisory_disclosure.dart';
import '../controllers/chat_controller.dart';
import '../models/chat_models.dart';

class ChatView extends GetView<ChatController> {

  const ChatView({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.backgroundDark,
      body: LayoutBuilder(
        builder: (context, constraints) {
          final isWide = constraints.maxWidth >= 768;
          return Row(
            children: [
              if (isWide)
                SizedBox(
                  width: 280,
                  child: _buildSidebar(context),
                ),
              Expanded(
                child: _buildChatArea(context, showMenuButton: !isWide),
              ),
            ],
          );
        },
      ),
      drawer: LayoutBuilder(
        builder: (context, constraints) {
          if (constraints.maxWidth < 768) {
            return Drawer(
              backgroundColor: AppTheme.surfaceDark,
              child: _buildSidebar(context, inDrawer: true),
            );
          }
          return const SizedBox.shrink();
        },
      ),
    );
  }

  Widget _buildSidebar(BuildContext context, {bool inDrawer = false}) {
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
                  return _buildConversationItem(conv, isSelected, inDrawer);
                },
              );
            }),
          ),
        ],
      ),
    );
  }

  Widget _buildConversationItem(ChatConversation conv, bool isSelected, bool inDrawer) {
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

  Widget _buildChatArea(BuildContext context, {required bool showMenuButton}) {
    return Column(
      children: [
        _buildChatHeader(context, showMenuButton),
        const Padding(
          padding: EdgeInsets.symmetric(horizontal: 16, vertical: 6),
          child: AiAdvisoryDisclosure(domain: 'Trợ lý Doanh nghiệp'),
        ),
        _buildReconnectBanner(),
        Expanded(child: _buildMessagesList()),
        _buildComposer(),
      ],
    );
  }


  Widget _buildChatHeader(BuildContext context, bool showMenuButton) {
    return Container(
      height: 60,
      padding: const EdgeInsets.symmetric(horizontal: 16),
      decoration: const BoxDecoration(
        color: AppTheme.surfaceDarkHeader,
        border: Border(bottom: BorderSide(color: AppTheme.borderDark)),
      ),
      child: Row(
        children: [
          if (showMenuButton)
            IconButton(
              icon: const Icon(Icons.menu, color: AppTheme.textDark),
              onPressed: () => Scaffold.of(context).openDrawer(),
            ),
          Obx(() {
            final profile = controller.activeConversation.value?.activeAgentProfile ?? 'founder_assistant';
            return Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(6),
                  decoration: BoxDecoration(
                    color: AppTheme.primary.withValues(alpha: 0.15),
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(Icons.smart_toy, size: 18, color: AppTheme.primary),
                ),
                const SizedBox(width: 10),
                Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _formatProfileName(profile),
                      style: const TextStyle(
                        color: AppTheme.textDark,
                        fontSize: 14,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    Text(
                      'AI Specialist',
                      style: TextStyle(
                        color: AppTheme.primary.withValues(alpha: 0.8),
                        fontSize: 11,
                      ),
                    ),
                  ],
                ),
              ],
            );
          }),
          const Spacer(),
          Obx(() {
            final status = controller.runStatus.value;
            final isStreaming = controller.isStreaming.value;
            if (status == 'idle' && !isStreaming) return const SizedBox.shrink();

            return Row(
              children: [
                _buildStatusBadge(status),
                if (isStreaming) ...[
                  const SizedBox(width: 8),
                  IconButton(
                    icon: const Icon(Icons.stop_circle, color: AppTheme.error, size: 22),
                    tooltip: 'Cancel run',
                    onPressed: () => controller.cancelActiveRun(),
                  ),
                ],
              ],
            );
          }),
        ],
      ),
    );
  }

  Widget _buildReconnectBanner() {
    return Obx(() {
      if (!controller.reconnecting.value) return const SizedBox.shrink();
      return Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 16),
        color: AppTheme.warning.withValues(alpha: 0.2),
        child: const Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            SizedBox(
              width: 12,
              height: 12,
              child: CircularProgressIndicator(strokeWidth: 2, color: AppTheme.warning),
            ),
            SizedBox(width: 8),
            Text(
              'Reconnecting to event stream...',
              style: TextStyle(color: AppTheme.warning, fontSize: 12, fontWeight: FontWeight.w600),
            ),
          ],
        ),
      );
    });
  }

  Widget _buildStatusBadge(String status) {
    Color color;
    String label;
    switch (status) {
      case 'running':
        color = AppTheme.secondary;
        label = 'Running';
        break;
      case 'waiting_approval':
        color = AppTheme.warning;
        label = 'Waiting Approval';
        break;
      case 'completed':
        color = AppTheme.success;
        label = 'Completed';
        break;
      case 'failed':
        color = AppTheme.error;
        label = 'Failed';
        break;
      case 'cancelled':
        color = AppTheme.preview;
        label = 'Cancelled';
        break;
      default:
        color = AppTheme.primary;
        label = status.toUpperCase();
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(100),
        border: Border.all(color: color.withValues(alpha: 0.4)),
      ),
      child: Text(
        label,
        style: TextStyle(color: color, fontSize: 11, fontWeight: FontWeight.bold),
      ),
    );
  }

  Widget _buildMessagesList() {
    return Obx(() {
      final msgs = controller.messages;
      if (msgs.isEmpty) {
        return Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.chat_outlined, size: 48, color: AppTheme.textDimDark.withValues(alpha: 0.5)),
              const SizedBox(height: 12),
              const Text(
                'How can I help you today?',
                style: TextStyle(color: AppTheme.textMutedDark, fontSize: 15, fontWeight: FontWeight.w500),
              ),
              const SizedBox(height: 4),
              const Text(
                'Ask questions, request analysis, or execute approved workflows.',
                style: TextStyle(color: AppTheme.textDimDark, fontSize: 12),
              ),
            ],
          ),
        );
      }

      return ListView.builder(
        controller: controller.scrollController,
        padding: const EdgeInsets.all(16),
        itemCount: msgs.length + 1,
        itemBuilder: (context, index) {
          if (index == msgs.length) {
            return _buildLiveActivitiesAndApprovals();
          }
          final msg = msgs[index];
          return _buildMessageBubble(msg);
        },
      );
    });
  }

  Widget _buildMessageBubble(ChatMessage msg) {
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
              MarkdownBody(
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

  Widget _buildLiveActivitiesAndApprovals() {
    return Obx(() {
      final reasoning = controller.reasoningStatus.value;
      final activities = controller.toolActivities;
      final approvals = controller.pendingApprovals;

      if (reasoning.isEmpty && activities.isEmpty && approvals.isEmpty) {
        return const SizedBox.shrink();
      }

      return Container(
        margin: const EdgeInsets.only(bottom: 16),
        constraints: const BoxConstraints(maxWidth: 720),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (reasoning.isNotEmpty)
              Container(
                margin: const EdgeInsets.only(bottom: 8),
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(
                  color: AppTheme.surfaceDarkLighter,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const SizedBox(
                      width: 12,
                      height: 12,
                      child: CircularProgressIndicator(strokeWidth: 1.5, color: AppTheme.secondary),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      reasoning,
                      style: const TextStyle(color: AppTheme.secondaryLight, fontSize: 12),
                    ),
                  ],
                ),
              ),

            // Tool Activity Cards
            ...activities.map((act) => _buildToolActivityCard(act)),

            // Approval Cards
            ...approvals.map((appr) => _buildApprovalCard(appr)),
          ],
        ),
      );
    });
  }

  Widget _buildToolActivityCard(ChatToolActivity act) {
    Color statusColor = act.status == 'completed'
        ? AppTheme.success
        : (act.status == 'failed' ? AppTheme.error : AppTheme.secondary);

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDarkLighter,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppTheme.borderDark),
      ),
      child: Row(
        children: [
          Icon(Icons.build_circle_outlined, size: 16, color: statusColor),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              'Tool: ${act.toolName}',
              style: const TextStyle(color: AppTheme.textDark, fontSize: 12, fontWeight: FontWeight.w600),
            ),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
            decoration: BoxDecoration(
              color: statusColor.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(4),
            ),
            child: Text(
              act.status.toUpperCase(),
              style: TextStyle(color: statusColor, fontSize: 10, fontWeight: FontWeight.bold),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildApprovalCard(ChatApproval appr) {
    final isPending = appr.status == 'PENDING';
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDark,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppTheme.warning.withValues(alpha: 0.5)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.gavel, color: AppTheme.warning, size: 18),
              const SizedBox(width: 8),
              const Text(
                'Approval Required',
                style: TextStyle(color: AppTheme.warning, fontSize: 13, fontWeight: FontWeight.bold),
              ),
              const Spacer(),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(
                  color: (isPending ? AppTheme.warning : (appr.status == 'APPROVED' ? AppTheme.success : AppTheme.error))
                      .withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  appr.status,
                  style: TextStyle(
                    color: isPending ? AppTheme.warning : (appr.status == 'APPROVED' ? AppTheme.success : AppTheme.error),
                    fontSize: 10,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            'Action: ${appr.action}',
            style: const TextStyle(color: AppTheme.textDark, fontSize: 12, fontWeight: FontWeight.w600),
          ),
          if (appr.subject.isNotEmpty) ...[
            const SizedBox(height: 4),
            Text(
              'Subject: ${appr.subject}',
              style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 12),
            ),
          ],
          if (isPending) ...[
            const SizedBox(height: 12),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                OutlinedButton(
                  onPressed: () => controller.handleApprovalDecision(appr.id, false),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: AppTheme.error,
                    side: const BorderSide(color: AppTheme.error),
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                  ),
                  child: const Text('Reject'),
                ),
                const SizedBox(width: 8),
                ElevatedButton(
                  onPressed: () => controller.handleApprovalDecision(appr.id, true),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.success,
                    foregroundColor: Colors.black,
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  ),
                  child: const Text('Approve'),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildComposer() {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: const BoxDecoration(
        color: AppTheme.surfaceDarkHeader,
        border: Border(top: BorderSide(color: AppTheme.borderDark)),
      ),
      child: SafeArea(
        child: Row(
          children: [
            Expanded(
              child: TextField(
                controller: controller.textController,
                style: const TextStyle(color: AppTheme.textDark, fontSize: 14),
                minLines: 1,
                maxLines: 4,
                decoration: const InputDecoration(
                  hintText: 'Type your message or ask anything...',
                  contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                ),
                onSubmitted: (_) => controller.sendMessage(),
              ),
            ),
            const SizedBox(width: 8),
            IconButton.filled(
              onPressed: () => controller.sendMessage(),
              icon: const Icon(Icons.send, size: 18),
              style: IconButton.styleFrom(
                backgroundColor: AppTheme.primary,
                foregroundColor: const Color(0xFF04070E),
              ),
            ),
          ],
        ),
      ),
    );
  }

  String _formatProfileName(String key) {
    switch (key) {
      case 'founder_assistant':
        return 'Founder Assistant';
      case 'marketing_lead':
        return 'Marketing Specialist';
      case 'sales_exec':
        return 'Sales Specialist';
      case 'finance_legal':
        return 'Finance & Legal Advisor';
      default:
        return key.replaceAll('_', ' ').capitalizeFirst ?? key;
    }
  }
}
