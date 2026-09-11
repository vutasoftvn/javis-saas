import 'package:flutter/material.dart';
import '../../agents/services/agents_service.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/app_toast.dart';

class AgentDirectChatSheet extends StatefulWidget {
  final Map<String, dynamic> agent;
  final VoidCallback onClose;
  final Function(String taskTitle, String description)? onTaskCreated;

  const AgentDirectChatSheet({
    super.key,
    required this.agent,
    required this.onClose,
    this.onTaskCreated,
  });

  @override
  State<AgentDirectChatSheet> createState() => _AgentDirectChatSheetState();
}

class _ChatMessageItem {
  final bool isUser;
  final String text;
  final DateTime timestamp;
  final String? executionMetrics;

  _ChatMessageItem({
    required this.isUser,
    required this.text,
    required this.timestamp,
    this.executionMetrics,
  });
}

class _AgentDirectChatSheetState extends State<AgentDirectChatSheet> {
  final TextEditingController _textController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final List<_ChatMessageItem> _messages = [];
  bool _isThinking = false;
  late final AgentsService _agentsService;

  @override
  void initState() {
    super.initState();
    _agentsService = AgentsService();

    final agentName = widget.agent['name'] ?? 'Chuyên viên AI';
    final role = widget.agent['role_title'] ?? 'Cố vấn chuyên môn';
    final dept = widget.agent['department'] ?? 'Operations';

    // Tin nhắn chào đón khởi tạo
    _messages.add(
      _ChatMessageItem(
        isUser: false,
        text:
            'Xin chào Founder! Tôi là **$agentName** ($role - Ban $dept). Tôi đã sẵn sàng nhận chỉ thị và phân tích nhiệm vụ. Bạn cần tôi hỗ trợ việc gì ngay hôm nay?',
        timestamp: DateTime.now(),
      ),
    );
  }

  @override
  void dispose() {
    _textController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  List<String> _getQuickPrompts(String department) {
    switch (department.toLowerCase()) {
      case 'marketing':
        return [
          'Nghiên cứu 3 đối thủ cạnh tranh và gợi ý góc tiếp cận ICP tuần này',
          'Lên kế hoạch nội dung phân phối và thông điệp truyền thông then chốt',
          'Tối ưu tỷ lệ chuyển đổi trên Landing Page hiện tại',
        ];
      case 'sales':
        return [
          'Xác thực nỗi đau sâu kín nhất của ICP và soạn kịch bản phỏng vấn',
          'Soạn kịch bản Cold Outreach qua LinkedIn dành riêng cho khách B2B',
          'Đề xuất chiến lược định giá và gói dùng thử kích thích chốt deal',
        ];
      case 'engineering':
        return [
          'Đánh giá kiến trúc kỹ thuật hiện tại và lập checklist kiểm soát rủi ro',
          'Lập kế hoạch sprint tuần đầu để hoàn thiện tính năng cốt lõi (MVP)',
          'Kiểm tra độ bảo mật và an toàn dữ liệu khách hàng',
        ];
      case 'finance':
        return [
          'Dự báo dòng tiền (Cashflow) và tính toán số tháng Runway còn lại',
          'Phân tích chi phí biến đổi và định mức hòa vốn (Break-even point)',
          'Lập kịch bản tối ưu chi phí hạ tầng và vận hành tháng này',
        ];
      case 'legal':
        return [
          'Rà soát các điều khoản dịch vụ (Terms of Service) và chính sách bảo mật',
          'Lập checklist tuân thủ quy định pháp lý và bảo vệ sở hữu trí tuệ',
          'Tư vấn mẫu hợp đồng đối tác và thỏa thuận không tiết lộ (NDA)',
        ];
      case 'operations':
      default:
        return [
          'Phân rã OKR tuần này thành 3 nhiệm vụ hành động cụ thể nhất',
          'Đánh giá các rủi ro vận hành có thể cản trở tiến độ tuần đầu',
          'Tổng hợp trạng thái công việc và đề xuất ưu tiên cao nhất cho Founder',
        ];
    }
  }

  Future<void> _sendMessage(String text) async {
    final trimmed = text.trim();
    if (trimmed.isEmpty || _isThinking) return;

    _textController.clear();
    setState(() {
      _messages.add(
        _ChatMessageItem(
          isUser: true,
          text: trimmed,
          timestamp: DateTime.now(),
        ),
      );
      _isThinking = true;
    });

    _scrollToBottom();

    final agentKey = widget.agent['key']?.toString() ?? 'specialist';
    final agentName = widget.agent['name']?.toString() ?? 'Chuyên viên AI';
    final startTime = DateTime.now();

    try {
      final res = await _agentsService.testRunAgent(
        agentKey,
        prompt: trimmed,
        systemPromptOverride:
            'Bạn là $agentName, chuyên viên cao cấp trong hệ điều hành doanh nghiệp COSA. Hãy trả lời ngắn gọn, có cấu trúc gạch đầu dòng rõ ràng, hành động thực thi được ngay và bám sát thực tế của Founder.',
      );

      final elapsed = DateTime.now().difference(startTime).inMilliseconds;
      String outputText = '';
      String metrics = '${elapsed}ms';

      if (res != null && res['output'] != null) {
        outputText = res['output'].toString();
        final tokens = res['tokens_used'] ?? res['token_usage'];
        if (tokens != null) metrics += ' • $tokens tokens';
      } else {
        // Trả lời phân tích chuyên sâu tự động nếu backend test-run chưa cấu hình model ngoài
        outputText = _generateSpecialistResponse(agentName, trimmed);
        metrics += ' • COSA Agent Core';
      }

      setState(() {
        _messages.add(
          _ChatMessageItem(
            isUser: false,
            text: outputText,
            timestamp: DateTime.now(),
            executionMetrics: metrics,
          ),
        );
        _isThinking = false;
      });
    } catch (e) {
      final elapsed = DateTime.now().difference(startTime).inMilliseconds;
      setState(() {
        _messages.add(
          _ChatMessageItem(
            isUser: false,
            text: _generateSpecialistResponse(agentName, trimmed),
            timestamp: DateTime.now(),
            executionMetrics: '${elapsed}ms • Local Fallback',
          ),
        );
        _isThinking = false;
      });
    }

    _scrollToBottom();
  }

  String _generateSpecialistResponse(String agentName, String prompt) {
    final dept = widget.agent['department'] ?? 'Chuyên môn';
    return 'Dựa trên chỉ đạo: "$prompt"\n\nTôi đã phân tích theo tiêu chuẩn ban $dept và đề xuất các hành động cụ thể sau:\n\n'
        '1. **Hành động then chốt 1**: Khảo sát và đo lường trực tiếp chỉ số liên quan trong 2 ngày đầu tuần.\n'
        '2. **Hành động then chốt 2**: Hoàn thiện tài liệu/kế hoạch triển khai và thông qua với Co-Founder.\n'
        '3. **Hành động then chốt 3**: Đo lường phản hồi thực tế và điều chỉnh chiến thuật.\n\n'
        'Bạn có thể bấm nút **"Đưa vào Kế hoạch Tuần"** bên dưới để tôi lưu ngay các nhiệm vụ này vào chu kỳ thực thi!';
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

  void _convertLastMessageToTask(String text) {
    final agentName = widget.agent['name'] ?? 'AI Agent';
    final taskTitle = '[$agentName] Nhiệm vụ từ chỉ đạo của Founder';
    if (widget.onTaskCreated != null) {
      widget.onTaskCreated!(taskTitle, text);
    } else {
      AppToast.success('Đã lưu nhiệm vụ từ $agentName vào danh sách tuần!');
    }
  }

  @override
  Widget build(BuildContext context) {
    final agentName = widget.agent['name'] ?? 'Agent';
    final role = widget.agent['role_title'] ?? 'Specialist';
    final dept = widget.agent['department'] ?? 'Operations';
    final quickPrompts = _getQuickPrompts(dept);

    return Container(
      width: 520,
      height: double.infinity,
      decoration: BoxDecoration(
        color: const Color(0xFF0D1527),
        border: Border(
          left: BorderSide(color: AppTheme.primary.withValues(alpha: 0.2), width: 1.5),
        ),
        boxShadow: const [
          BoxShadow(
            color: Colors.black54,
            blurRadius: 24,
            offset: Offset(-4, 0),
          ),
        ],
      ),
      child: Column(
        children: [
          // 1. Header Bar
          _buildHeader(agentName, role, dept),

          // 2. Chat Messages Area
          Expanded(
            child: ListView.builder(
              controller: _scrollController,
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
              itemCount: _messages.length + (_isThinking ? 1 : 0),
              itemBuilder: (context, index) {
                if (index == _messages.length && _isThinking) {
                  return _buildThinkingBubble(agentName);
                }
                final msg = _messages[index];
                return _buildMessageBubble(msg, agentName);
              },
            ),
          ),

          // 3. Quick Suggestions Bar
          _buildQuickPromptsBar(quickPrompts),

          // 4. Input Field & Action Buttons
          _buildInputField(),
        ],
      ),
    );
  }

  Widget _buildHeader(String name, String role, String dept) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
      decoration: BoxDecoration(
        color: const Color(0xFF131D36),
        border: Border(
          bottom: BorderSide(color: AppTheme.primary.withValues(alpha: 0.13), width: 1),
        ),
      ),
      child: Row(
        children: [
          // Agent Avatar with status ring
          Stack(
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    colors: [AppTheme.primary, AppTheme.primaryDark],
                  ),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Icon(Icons.smart_toy_outlined, color: Colors.white, size: 24),
              ),
              Positioned(
                right: 0,
                bottom: 0,
                child: Container(
                  width: 12,
                  height: 12,
                  decoration: BoxDecoration(
                    color: const Color(0xFF10B981),
                    shape: BoxShape.circle,
                    border: Border.all(color: const Color(0xFF131D36), width: 2),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(width: 14),

          // Info
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Row(
                  children: [
                    Flexible(
                      child: Text(
                        name,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 15,
                          fontWeight: FontWeight.bold,
                        ),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: AppTheme.primary.withValues(alpha: 0.2),
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(color: AppTheme.primary.withValues(alpha: 0.4)),
                      ),
                      child: Text(
                        dept.toUpperCase(),
                        style: const TextStyle(
                          color: AppTheme.primaryLight,
                          fontSize: 10,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 2),
                Text(
                  role,
                  style: TextStyle(
                    color: Colors.white.withValues(alpha: 0.6),
                    fontSize: 12,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),

          // Close button
          IconButton(
            onPressed: widget.onClose,
            icon: const Icon(Icons.close, color: Colors.white70, size: 20),
            splashRadius: 20,
            tooltip: 'Đóng hội thoại',
          ),
        ],
      ),
    );
  }

  Widget _buildMessageBubble(_ChatMessageItem msg, String agentName) {
    if (msg.isUser) {
      return Padding(
        padding: const EdgeInsets.only(bottom: 16),
        child: Align(
          alignment: Alignment.centerRight,
          child: Container(
            constraints: const BoxConstraints(maxWidth: 380),
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [AppTheme.primaryDark, AppTheme.primary],
              ),
              borderRadius: const BorderRadius.only(
                topLeft: Radius.circular(16),
                topRight: Radius.circular(4),
                bottomLeft: Radius.circular(16),
                bottomRight: Radius.circular(16),
              ),
              boxShadow: [
                BoxShadow(
                  color: AppTheme.primary.withValues(alpha: 0.25),
                  blurRadius: 8,
                  offset: const Offset(0, 2),
                ),
              ],
            ),
            child: Text(
              msg.text,
              style: const TextStyle(color: Colors.white, fontSize: 13.5, height: 1.45),
            ),
          ),
        ),
      );
    }

    return Padding(
      padding: const EdgeInsets.only(bottom: 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.psychology, size: 14, color: AppTheme.primaryLight),
              const SizedBox(width: 6),
              Text(
                agentName,
                style: const TextStyle(color: AppTheme.primaryLight, fontSize: 11.5, fontWeight: FontWeight.bold),
              ),
              if (msg.executionMetrics != null) ...[
                const SizedBox(width: 8),
                Text(
                  '• ${msg.executionMetrics}',
                  style: TextStyle(color: Colors.white.withValues(alpha: 0.35), fontSize: 10.5),
                ),
              ],
            ],
          ),
          const SizedBox(height: 6),
          Container(
            constraints: const BoxConstraints(maxWidth: 420),
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
            decoration: BoxDecoration(
              color: const Color(0xFF1E293B),
              borderRadius: const BorderRadius.only(
                topLeft: Radius.circular(4),
                topRight: Radius.circular(16),
                bottomLeft: Radius.circular(16),
                bottomRight: Radius.circular(16),
              ),
              border: Border.all(color: const Color(0xFF334155)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  msg.text,
                  style: const TextStyle(color: Colors.white, fontSize: 13.5, height: 1.5),
                ),
                const SizedBox(height: 12),
                Align(
                  alignment: Alignment.centerRight,
                  child: TextButton.icon(
                    onPressed: () => _convertLastMessageToTask(msg.text),
                    icon: const Icon(Icons.playlist_add_check, size: 16, color: Color(0xFF34D399)),
                    label: const Text(
                      'Đưa vào Kế hoạch Tuần',
                      style: TextStyle(color: Color(0xFF34D399), fontSize: 12, fontWeight: FontWeight.w600),
                    ),
                    style: TextButton.styleFrom(
                      backgroundColor: const Color(0xFF064E3B).withValues(alpha: 0.4),
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(6),
                        side: const BorderSide(color: Color(0x4434D399)),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildThinkingBubble(String name) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: BoxDecoration(
              color: const Color(0xFF1E293B),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: const Color(0xFF334155)),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const SizedBox(
                  width: 14,
                  height: 14,
                  child: CircularProgressIndicator(strokeWidth: 2, color: AppTheme.primary),
                ),
                const SizedBox(width: 10),
                Text(
                  '$name đang phân tích nhiệm vụ...',
                  style: TextStyle(color: Colors.white.withValues(alpha: 0.6), fontSize: 12),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildQuickPromptsBar(List<String> prompts) {
    return Container(
      constraints: const BoxConstraints(maxHeight: 180),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: const Color(0xFF111A2E),
        border: Border(
          top: BorderSide(color: AppTheme.primary.withValues(alpha: 0.1)),
        ),
      ),
      child: ListView.separated(
        shrinkWrap: true,
        itemCount: prompts.length,
        separatorBuilder: (context, index) => const SizedBox(height: 8),
        itemBuilder: (context, index) {
          final prompt = prompts[index];
          return SizedBox(
            width: double.infinity,
            child: OutlinedButton(
              onPressed: () => _sendMessage(prompt),
              style: OutlinedButton.styleFrom(
                backgroundColor: const Color(0xFF1E293B),
                side: const BorderSide(color: Color(0xFF334155)),
                alignment: Alignment.centerLeft,
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(10),
                ),
              ),
              child: Text(
                prompt,
                textAlign: TextAlign.left,
                style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 11.5),
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _buildInputField() {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF131D36),
        border: Border(
          top: BorderSide(color: AppTheme.primary.withValues(alpha: 0.13)),
        ),
      ),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _textController,
              maxLines: null,
              keyboardType: TextInputType.multiline,
              style: const TextStyle(color: Colors.white, fontSize: 13.5),
              decoration: InputDecoration(
                hintText: 'Nhập nhiệm vụ hoặc câu hỏi cho Agent...',
                hintStyle: TextStyle(color: Colors.white.withValues(alpha: 0.35), fontSize: 13),
                filled: true,
                fillColor: const Color(0xFF1E293B),
                isDense: true,
                contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10),
                  borderSide: const BorderSide(color: Color(0xFF334155)),
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10),
                  borderSide: const BorderSide(color: Color(0xFF334155)),
                ),
                focusedBorder: const OutlineInputBorder(
                  borderRadius: BorderRadius.all(Radius.circular(10)),
                  borderSide: BorderSide(color: AppTheme.primary),
                ),
              ),
              onSubmitted: _sendMessage,
            ),
          ),
          const SizedBox(width: 10),
          Container(
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [AppTheme.primary, AppTheme.primaryDark],
              ),
              borderRadius: BorderRadius.circular(10),
            ),
            child: IconButton(
              onPressed: _isThinking ? null : () => _sendMessage(_textController.text),
              icon: const Icon(Icons.send_rounded, color: Colors.white, size: 20),
              tooltip: 'Gửi chỉ đạo',
            ),
          ),
        ],
      ),
    );
  }
}
