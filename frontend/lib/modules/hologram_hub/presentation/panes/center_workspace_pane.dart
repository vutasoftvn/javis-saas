import 'package:flutter/material.dart';
import '../../../../shared/widgets/presenters/tool_presenter_factory.dart';

class CenterWorkspacePane extends StatelessWidget {
  final String activeAgentId;
  final List<Map<String, dynamic>> messages;
  final TextEditingController inputController;
  final VoidCallback onSendMessage;
  final Function(String chipText)? onQuickChipSelected;
  final VoidCallback? onApproveAction;
  final VoidCallback? onRejectAction;

  const CenterWorkspacePane({
    super.key,
    required this.activeAgentId,
    required this.messages,
    required this.inputController,
    required this.onSendMessage,
    this.onQuickChipSelected,
    this.onApproveAction,
    this.onRejectAction,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      color: const Color(0xFF0A0D14),
      child: Column(
        children: [
          // Active Agent Header
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: const BoxDecoration(
              color: Color(0xFF101622),
              border: Border(bottom: BorderSide(color: Color(0x1FFFFFFF))),
            ),
            child: Row(
              children: [
                Container(
                  width: 8,
                  height: 8,
                  decoration: const BoxDecoration(
                    color: Color(0xFF00FF66),
                    shape: BoxShape.circle,
                  ),
                ),
                const SizedBox(width: 8),
                Text(
                  "AGENT: ${activeAgentId.toUpperCase()}",
                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13, letterSpacing: 0.5),
                ),
                const Spacer(),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: const Color(0x2000F0FF),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: const Color(0x4000F0FF)),
                  ),
                  child: const Text("ONE RUNTIME • REASONING", style: TextStyle(color: Color(0xFF00F0FF), fontSize: 10, fontWeight: FontWeight.bold)),
                )
              ],
            ),
          ),

          // Message & Tool Result Stream
          Expanded(
            child: messages.isEmpty
                ? const Center(
                    child: Text(
                      "Bắt đầu điều hành doanh nghiệp với Agent...",
                      style: TextStyle(color: Colors.white38, fontSize: 13),
                    ),
                  )
                : ListView.builder(
                    itemCount: messages.length,
                    padding: const EdgeInsets.all(16),
                    itemBuilder: (context, index) {
                      final item = messages[index];
                      final isUser = item['sender'] == 'user';
                      final presenterPayload = item['presenter_payload'] as Map<String, dynamic>?;

                      return Column(
                        crossAxisAlignment: isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
                        children: [
                          if (item['content'] != null && item['content'].toString().isNotEmpty)
                            Container(
                              margin: const EdgeInsets.only(bottom: 6),
                              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                              constraints: const BoxConstraints(maxWidth: 600),
                              decoration: BoxDecoration(
                                color: isUser ? const Color(0xFF00F0FF).withValues(alpha: 0.15) : const Color(0xFF161F30),
                                borderRadius: BorderRadius.circular(10),
                                border: Border.all(
                                  color: isUser ? const Color(0x6000F0FF) : const Color(0x20FFFFFF),
                                ),
                              ),
                              child: Text(
                                item['content'],
                                style: const TextStyle(color: Colors.white, fontSize: 13, height: 1.4),
                              ),
                            ),
                          // Tool Presenter Card Rendering
                          if (presenterPayload != null)
                            ConstrainedBox(
                              constraints: const BoxConstraints(maxWidth: 600),
                              child: ToolPresenterFactory.build(
                                presenterPayload,
                                onApprove: onApproveAction,
                                onReject: onRejectAction,
                              ),
                            ),
                          const SizedBox(height: 8),
                        ],
                      );
                    },
                  ),
          ),

          // Quick Action Chips
          Container(
            height: 36,
            padding: const EdgeInsets.symmetric(horizontal: 12),
            child: ListView(
              scrollDirection: Axis.horizontal,
              children: [
                _buildQuickChip("chào"),
                _buildQuickChip("Nghiên cứu thị trường EdTech"),
                _buildQuickChip("Báo cáo P&L Q1-2026"),
                _buildQuickChip("Tìm kiếm 5 Leads mới"),
                _buildQuickChip("Deploy Staging @mID"),
              ],
            ),
          ),
          const SizedBox(height: 6),

          // Input Command Bar
          Container(
            padding: const EdgeInsets.all(12),
            decoration: const BoxDecoration(
              color: Color(0xFF101622),
              border: Border(top: BorderSide(color: Color(0x1FFFFFFF))),
            ),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: inputController,
                    style: const TextStyle(color: Colors.white, fontSize: 13),
                    decoration: const InputDecoration(
                      hintText: "Nhập chỉ thị hoặc câu lệnh cho Agent...",
                      hintStyle: TextStyle(color: Colors.white38, fontSize: 13),
                      border: InputBorder.none,
                      isDense: true,
                    ),
                    onSubmitted: (_) => onSendMessage(),
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.send_rounded, color: Color(0xFF00F0FF), size: 20),
                  tooltip: "Gửi chỉ thị",
                  onPressed: onSendMessage,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildQuickChip(String label) {
    return Padding(
      padding: const EdgeInsets.only(right: 6),
      child: ActionChip(
        backgroundColor: const Color(0x18FFFFFF),
        side: const BorderSide(color: Color(0x20FFFFFF)),
        label: Text(label, style: const TextStyle(color: Colors.white70, fontSize: 11)),
        onPressed: () => onQuickChipSelected?.call(label),
      ),
    );
  }
}
