import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/localization/locale_controller.dart';
import '../../../core/localization/supported_locale.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/app_toast.dart';
import '../../chat/models/data_access_declaration.dart';
import '../../chat/services/agent_chat_service.dart';
import '../../tasks/services/task_service.dart';
import '../controllers/direct_agent_chat_controller.dart';

/// Chat trực tiếp với 1 specialist của Project đang hoạt động. Toàn bộ trạng thái đến từ
/// [DirectAgentChatController] (API thật); sheet không tự sinh câu trả lời hay toast thành công.
class AgentDirectChatSheet extends StatefulWidget {
  final Map<String, dynamic> agent;

  /// Project đang hoạt động của Hub; null thì sheet báo lỗi và không gửi gì.
  final String? projectId;

  /// Profile key backend (vd. `finance`), khác `agent['key']` dùng cho hiển thị.
  final String profileKey;
  final VoidCallback onClose;
  final void Function(String taskId)? onTaskCreated;

  /// Chỉ dùng cho test: tiêm controller đã dựng sẵn.
  final DirectAgentChatController? controller;

  const AgentDirectChatSheet({
    super.key,
    required this.agent,
    required this.projectId,
    required this.profileKey,
    required this.onClose,
    this.onTaskCreated,
    this.controller,
  });

  @override
  State<AgentDirectChatSheet> createState() => _AgentDirectChatSheetState();
}

class _AgentDirectChatSheetState extends State<AgentDirectChatSheet> {
  final TextEditingController _textController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  late final DirectAgentChatController _controller;
  late final bool _ownsController;
  DataAccessDeclaration _dataAccess = const DataAccessDeclaration();

  bool _isEnglish() {
    if (Get.isRegistered<LocaleController>()) {
      return Get.find<LocaleController>().current.value == SupportedLocale.enUS;
    }
    return Get.locale?.languageCode == 'en';
  }

  @override
  void initState() {
    super.initState();
    _ownsController = widget.controller == null;
    _controller = widget.controller ??
        DirectAgentChatController(
          projectId: widget.projectId,
          profileKey: widget.profileKey,
          chatService: AgentChatService(),
          taskService: TaskService(),
        );
    _controller.addListener(_scrollToBottom);
  }

  @override
  void dispose() {
    _controller.removeListener(_scrollToBottom);
    if (_ownsController) _controller.dispose();
    _textController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  List<String> _getQuickPrompts(String department) {
    final isEn = _isEnglish();
    if (isEn) {
      switch (department.toLowerCase()) {
        case 'marketing':
          return [
            'Research 3 key competitors and recommend this week\'s ICP angles',
            'Plan distribution content and core communication messages',
            'Optimize conversion rate on the current landing page',
          ];
        case 'sales':
          return [
            'Validate the deepest pain point of ICP and draft an interview script',
            'Draft a cold outreach script via LinkedIn specifically for B2B leads',
            'Propose a pricing and trial strategy to accelerate deal closing',
          ];
        case 'engineering':
          return [
            'Assess current technical architecture and draft risk mitigation checklist',
            'Plan first week sprint to complete the core MVP feature set',
            'Audit security and customer data safety protocols',
          ];
        case 'finance':
          return [
            'Forecast cashflow and calculate remaining runway months',
            'Analyze variable costs and break-even point threshold',
            'Model scenarios to optimize infrastructure and operational expenses',
          ];
        case 'legal':
          return [
            'Review Terms of Service and Privacy Policy agreements',
            'Prepare compliance checklist and intellectual property protections',
            'Consult on standard partnership agreements and non-disclosure agreements (NDA)',
          ];
        case 'operations':
        default:
          return [
            'Decompose this week\'s OKRs into 3 concrete tactical action items',
            'Draft weekly execution SOP for the cross-functional team',
            'Identify bottlenecks and optimize internal operational workflows',
          ];
      }
    }
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
          'Xây dựng SOP quy trình phối hợp nội bộ cho team đa nhiệm vụ',
          'Đánh giá các nút thắt cổ chai và tối ưu hiệu suất vận hành',
        ];
    }
  }

  Future<void> _sendMessage(String text) async {
    final trimmed = text.trim();
    if (trimmed.isEmpty || _controller.isBusy) return;
    _textController.clear();
    await _controller.send(trimmed, _dataAccess);
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

  String _taskTitleFor(String responseText) {
    final agentName = widget.agent['name'] ?? 'AI Agent';
    final firstLine = responseText.trim().split('\n').first.trim();
    final summary = firstLine.length > 100 ? '${firstLine.substring(0, 100)}…' : firstLine;
    return '[$agentName] $summary';
  }

  /// Toast thành công CHỈ sau khi Company trả task id; lỗi giữ nguyên câu trả lời để retry.
  Future<void> _convertToTask(DirectChatMessage message) async {
    final isEn = _isEnglish();
    try {
      final taskId = await _controller.createTaskFromResponse(
        message,
        title: _taskTitleFor(message.text),
      );
      AppToast.success(
        isEn ? 'Task created (id $taskId)' : 'Đã tạo task (id $taskId)',
      );
      widget.onTaskCreated?.call(taskId);
    } catch (e) {
      AppToast.error(
        isEn ? 'Could not create task: $e' : 'Không tạo được task: $e',
      );
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

          // 2. Chat Messages Area (trạng thái thật từ controller)
          Expanded(
            child: ListenableBuilder(
              listenable: _controller,
              builder: (context, _) {
                final messages = _controller.messages;
                if (messages.isEmpty) return _buildEmptyState();
                return ListView.builder(
                  controller: _scrollController,
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
                  itemCount: messages.length,
                  itemBuilder: (context, index) => _buildMessageBubble(messages[index], agentName),
                );
              },
            ),
          ),

          // 3. Lỗi recoverable / thiếu Project
          ListenableBuilder(
            listenable: _controller,
            builder: (context, _) => _buildStatusBanner(),
          ),

          // 4. Quick Suggestions Bar + data access + input
          if (_controller.hasProject) ...[
            _buildQuickPromptsBar(quickPrompts),
            _buildDataAccessBar(),
          ],
          ListenableBuilder(
            listenable: _controller,
            builder: (context, _) => _buildInputField(),
          ),
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
            tooltip: _isEnglish() ? 'Close conversation' : 'Đóng hội thoại',
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyState() {
    final isEn = _isEnglish();
    final text = _controller.hasProject
        ? (isEn
            ? 'Send an instruction. The answer comes from a real agent run in this Project.'
            : 'Gửi chỉ đạo. Câu trả lời đến từ một run agent thật trong Project này.')
        : (_controller.unavailableReason ?? '');
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Text(
          text,
          textAlign: TextAlign.center,
          style: TextStyle(color: Colors.white.withValues(alpha: 0.55), fontSize: 13),
        ),
      ),
    );
  }

  Widget _buildStatusBanner() {
    final error = _controller.hasProject ? _controller.errorMessage : _controller.unavailableReason;
    if (error == null) return const SizedBox.shrink();
    return Container(
      key: const Key('direct_chat_error_banner'),
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      color: const Color(0xFF2A1B1B),
      child: Row(
        children: [
          const Icon(Icons.error_outline, color: Color(0xFFF87171), size: 18),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              error,
              style: const TextStyle(color: Color(0xFFFCA5A5), fontSize: 12),
            ),
          ),
          if (_controller.hasProject)
            TextButton(
              onPressed: _controller.clearError,
              child: Text(_isEnglish() ? 'Dismiss' : 'Đóng'),
            ),
        ],
      ),
    );
  }

  Widget _buildMessageBubble(DirectChatMessage msg, String agentName) {
    final failed = msg.state == DirectChatMessageState.failed;
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
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(
                  msg.text,
                  style: const TextStyle(color: Colors.white, fontSize: 13.5, height: 1.45),
                ),
                if (failed)
                  Padding(
                    padding: const EdgeInsets.only(top: 6),
                    child: Text(
                      _isEnglish() ? 'Not sent' : 'Chưa gửi được',
                      style: const TextStyle(color: Color(0xFFFCA5A5), fontSize: 11),
                    ),
                  ),
              ],
            ),
          ),
        ),
      );
    }

    final running = msg.state == DirectChatMessageState.running;
    final completed = msg.state == DirectChatMessageState.completed;
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
              if (msg.runId != null) ...[
                const SizedBox(width: 8),
                Text(
                  '• run ${msg.runId}',
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
              border: Border.all(color: failed ? const Color(0xFFF87171) : const Color(0xFF334155)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (running && msg.text.isEmpty)
                  Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const SizedBox(
                        width: 14,
                        height: 14,
                        child: CircularProgressIndicator(strokeWidth: 2, color: AppTheme.primary),
                      ),
                      const SizedBox(width: 10),
                      Text(
                        _isEnglish() ? '$agentName is running...' : '$agentName đang chạy...',
                        style: TextStyle(color: Colors.white.withValues(alpha: 0.6), fontSize: 12),
                      ),
                    ],
                  )
                else if (msg.text.isNotEmpty)
                  Text(
                    msg.text,
                    style: const TextStyle(color: Colors.white, fontSize: 13.5, height: 1.5),
                  ),
                if (failed && msg.error != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: Text(
                      msg.error!,
                      style: const TextStyle(color: Color(0xFFFCA5A5), fontSize: 12),
                    ),
                  ),
                if (completed && msg.text.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  Align(
                    alignment: Alignment.centerRight,
                    child: msg.taskId != null
                        ? Text(
                            _isEnglish() ? 'Task ${msg.taskId} created' : 'Đã tạo task ${msg.taskId}',
                            key: const Key('direct_chat_task_created'),
                            style: const TextStyle(color: Color(0xFF34D399), fontSize: 12),
                          )
                        : TextButton.icon(
                            key: const Key('direct_chat_create_task_button'),
                            onPressed: () => _convertToTask(msg),
                            icon: const Icon(Icons.playlist_add_check, size: 16, color: Color(0xFF34D399)),
                            label: Text(
                              _isEnglish() ? 'Create task' : 'Tạo task',
                              style: const TextStyle(color: Color(0xFF34D399), fontSize: 12, fontWeight: FontWeight.w600),
                            ),
                          ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDataAccessBar() {
    final isEn = _isEnglish();
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      color: const Color(0xFF111A2E),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            isEn ? 'Data this message may contain' : 'Dữ liệu tin nhắn có thể chứa',
            style: TextStyle(color: Colors.white.withValues(alpha: 0.5), fontSize: 11),
          ),
          const SizedBox(height: 4),
          Wrap(
            spacing: 8,
            runSpacing: 4,
            children: DataAccessCategory.values.map((category) {
              final selected = _dataAccess.categories.contains(category);
              return FilterChip(
                key: Key('direct_chat_category_${category.apiValue}'),
                label: Text(category.label, style: const TextStyle(fontSize: 12)),
                selected: selected,
                onSelected: (value) {
                  final next = {..._dataAccess.categories};
                  value ? next.add(category) : next.remove(category);
                  setState(() {
                    _dataAccess = _dataAccess.copyWith(categories: next);
                  });
                },
              );
            }).toList(),
          ),
          if (_dataAccess.requiresSubjectReference)
            TextField(
              key: const Key('direct_chat_subject_reference_field'),
              style: const TextStyle(color: Colors.white, fontSize: 13),
              decoration: InputDecoration(
                hintText: isEn ? 'Data subject reference' : 'Mã đối tượng dữ liệu (subject reference)',
                isDense: true,
              ),
              onChanged: (value) => setState(() {
                _dataAccess = _dataAccess.copyWith(subjectReference: value);
              }),
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
                hintText: _isEnglish()
                    ? 'Enter mission or question for Agent...'
                    : 'Nhập nhiệm vụ hoặc câu hỏi cho Agent...',
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
              enabled: _controller.hasProject,
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
              onPressed: (_controller.isBusy || !_controller.hasProject)
                  ? null
                  : () => _sendMessage(_textController.text),
              icon: const Icon(Icons.send_rounded, color: Colors.white, size: 20),
              tooltip: _isEnglish() ? 'Send instruction' : 'Gửi chỉ đạo',
            ),
          ),
        ],
      ),
    );
  }
}
