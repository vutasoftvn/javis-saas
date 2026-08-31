import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/theme/app_theme.dart';
import '../../../shared/widgets/ai_advisory_disclosure.dart';
import '../controllers/chat_controller.dart';
import 'widgets/chat_sidebar.dart';
import 'widgets/chat_header.dart';
import 'widgets/chat_message_bubble.dart';
import 'widgets/chat_activity_cards.dart';
import 'widgets/chat_composer.dart';

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
                  child: ChatSidebar(controller: controller),
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
              child: ChatSidebar(controller: controller, inDrawer: true),
            );
          }
          return const SizedBox.shrink();
        },
      ),
    );
  }

  Widget _buildChatArea(BuildContext context, {required bool showMenuButton}) {
    return Column(
      children: [
        ChatHeader(controller: controller, showMenuButton: showMenuButton),
        const Padding(
          padding: EdgeInsets.symmetric(horizontal: 16, vertical: 6),
          child: AiAdvisoryDisclosure(domain: 'Trợ lý Doanh nghiệp'),
        ),
        _buildReconnectBanner(),
        Expanded(child: _buildMessagesList()),
        ChatComposer(controller: controller),
      ],
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

  Widget _buildMessagesList() {
    return Obx(() {
      final msgs = controller.messages;
      if (msgs.isEmpty) {
        return LayoutBuilder(
          builder: (context, constraints) {
            return SingleChildScrollView(
              child: ConstrainedBox(
                constraints: BoxConstraints(minHeight: constraints.maxHeight),
                child: Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    mainAxisSize: MainAxisSize.min,
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
                ),
              ),
            );
          },
        );
      }

      return ListView.builder(
        controller: controller.scrollController,
        padding: const EdgeInsets.all(16),
        itemCount: msgs.length + 1,
        itemBuilder: (context, index) {
          if (index == msgs.length) {
            return ChatActivityCards(controller: controller);
          }
          final msg = msgs[index];
          return ChatMessageBubble(msg: msg);
        },
      );
    });
  }
}
