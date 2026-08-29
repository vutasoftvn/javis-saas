import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../controllers/hologram_hub_controller.dart';
import 'chat/hub_chat_empty_state.dart';
import 'chat/hub_chat_header.dart';
import 'chat/hub_chat_input_bar.dart';
import 'chat/hub_chat_message_bubble.dart';
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

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: EdgeInsets.zero,
      borderRadius: 16,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // 1. Header
          HubChatHeader(controller: widget.controller),

          // 2. Chat Body (Messages or Quick Prompt Empty State)
          Expanded(
            child: Obx(() {
              final messages = widget.controller.mobileMessages;

              if (messages.isEmpty) {
                return HubChatEmptyState(onSelectPrompt: _handleSubmitted);
              }

              return _buildMessageList(messages);
            }),
          ),

          // 3. Input Toolbar & Voice Bar
          HubChatInputBar(
            controller: widget.controller,
            textController: _textController,
            focusNode: _focusNode,
            waveController: _waveController,
            isComposing: _isComposing,
            onSubmit: _handleSubmitted,
          ),
        ],
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
          return HubChatMessageBubble(
            message: messages[index],
            controller: widget.controller,
          );
        },
      ),
    );
  }
}
