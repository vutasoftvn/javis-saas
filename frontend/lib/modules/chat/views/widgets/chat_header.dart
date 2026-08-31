import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/theme/app_theme.dart';
import '../../controllers/chat_controller.dart';

class ChatHeader extends StatelessWidget {
  final ChatController controller;
  final bool showMenuButton;

  const ChatHeader({
    super.key,
    required this.controller,
    required this.showMenuButton,
  });

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

  @override
  Widget build(BuildContext context) {
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
}
