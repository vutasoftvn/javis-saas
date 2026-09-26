import 'dart:async';
import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../models/chat_models.dart';
import '../models/data_access_declaration.dart';
import '../services/agent_chat_service.dart';

class ChatController extends GetxController {
  ChatController({AgentChatService? service})
      : _service = service ?? AgentChatService();

  final AgentChatService _service;

  final conversations = <ChatConversation>[].obs;
  final activeConversation = Rxn<ChatConversation>();
  final messages = <ChatMessage>[].obs;

  final isLoading = false.obs;
  final isStreaming = false.obs;
  final currentRunId = ''.obs;
  final runStatus = 'idle'.obs;
  final reasoningStatus = ''.obs;
  final reconnecting = false.obs;
  final lastSequence = 0.obs;

  final toolActivities = <ChatToolActivity>[].obs;
  final pendingApprovals = <ChatApproval>[].obs;

  /// Task 2 (2026-09-11 Project-scoped Founder Hub) — Project đang hoạt động
  /// cho module chat chung này. KHÔNG auto-select/company-wide: `null` nghĩa
  /// là chưa có Project nào được chọn, và `createNewConversation()`/
  /// `sendMessage()` PHẢI từ chối dispatch (surface trạng thái "cần chọn
  /// Project" cục bộ) thay vì gọi API thiếu project_id rồi nhận 422 từ server.
  final RxnString activeProjectId = RxnString();

  /// Đặt Project đang hoạt động cho module chat chung này. `onInit()` gọi
  /// `loadConversations()` sớm hơn khi chưa có Project nào (no-op, xem
  /// docstring `loadConversations()`) — set project ở đây rồi tự động nạp
  /// lại danh sách conversation của đúng Project đó.
  void setActiveProjectId(String? projectId) {
    activeProjectId.value = projectId;
    if (projectId != null && projectId.isNotEmpty) {
      loadConversations();
    }
  }

  /// Khai báo phân loại dữ liệu (data access) người dùng chọn cho tin nhắn
  /// SẮP gửi — bắt buộc khớp field `data_access` của API (Task 5). Reset về
  /// rỗng sau mỗi lần gửi thành công để tránh rò rỉ classification cũ sang
  /// tin nhắn mới.
  final dataAccess = const DataAccessDeclaration().obs;

  /// Send chỉ được bật khi đã chọn category hợp lệ (và có subject_reference
  /// nếu category yêu cầu) — validate phía client trước khi gọi API để UX
  /// tốt hơn 422 từ server.
  bool get canSendMessage => dataAccess.value.isValid;

  void toggleDataAccessCategory(DataAccessCategory category) {
    final current = Set<DataAccessCategory>.from(dataAccess.value.categories);
    if (!current.remove(category)) {
      current.add(category);
    }
    dataAccess.value = dataAccess.value.copyWith(categories: current);
  }

  void setDataAccessSubjectReference(String value) {
    dataAccess.value = dataAccess.value.copyWith(
      subjectReference: value,
      clearSubjectReference: value.trim().isEmpty,
    );
  }

  final textController = TextEditingController();
  final scrollController = ScrollController();

  StreamSubscription<Map<String, dynamic>>? _sseSubscription;

  @override
  void onInit() {
    super.onInit();
    loadConversations();
  }

  @override
  void onClose() {
    _sseSubscription?.cancel();
    textController.dispose();
    scrollController.dispose();
    super.onClose();
  }

  /// Task 2 (2026-09-11 Project-scoped Founder Hub, review Finding 2) —
  /// list/get/update giờ cũng bắt buộc Project qua server
  /// (`apps/cosa/api/conversation_routes.py`). Không có Project đang hoạt
  /// động (mặc định lúc `onInit()` chạy, trước khi bất kỳ ai chọn Project)
  /// thì KHÔNG được gọi API thiếu project_id — chỉ bỏ qua fetch, giữ
  /// `conversations` rỗng, giống pattern "surface trạng thái cục bộ, không
  /// dispatch" đã dùng cho `createNewConversation()`/`sendMessage()`.
  Future<void> loadConversations() async {
    final projectId = activeProjectId.value;
    if (projectId == null || projectId.isEmpty) {
      return;
    }
    isLoading.value = true;
    try {
      final list = await _service.getConversations(projectId: projectId);
      conversations.assignAll(list);
      if (activeConversation.value == null && conversations.isNotEmpty) {
        selectConversation(conversations.first);
      }
    } finally {
      isLoading.value = false;
    }
  }

  Future<void> selectConversation(ChatConversation conv) async {
    activeConversation.value = conv;
    messages.clear();
    toolActivities.clear();
    pendingApprovals.clear();
    runStatus.value = 'idle';
    reasoningStatus.value = '';

    final projectId = activeProjectId.value;
    if (projectId == null || projectId.isEmpty) {
      // Không có Project đang hoạt động — giữ conv tối thiểu đã có (từ
      // danh sách/kết quả tạo mới) thay vì gọi API thiếu project_id.
      return;
    }

    // Fetch full conversation detail
    isLoading.value = true;
    try {
      final fullConv = await _service.getConversation(
        conv.id,
        projectId: projectId,
      );
      if (fullConv != null) {
        activeConversation.value = fullConv;
        messages.assignAll(fullConv.messages);
        _scrollToBottom();
      }
    } finally {
      isLoading.value = false;
    }
  }

  Future<void> createNewConversation({String? agentProfile}) async {
    final projectId = activeProjectId.value;
    if (projectId == null || projectId.isEmpty) {
      // Task 2 — không dispatch khi chưa có Project; chỉ surface trạng thái
      // cục bộ để UI hiển thị, KHÔNG âm thầm bỏ qua hoặc tự chọn hộ.
      sendBlockedReason.value = 'Select a project before creating a conversation.';
      return;
    }
    isLoading.value = true;
    try {
      final newConv = await _service.createConversation(
        projectId: projectId,
        title: 'New Conversation',
        activeAgentProfile: agentProfile ?? 'founder_assistant',
      );
      if (newConv != null) {
        conversations.insert(0, newConv);
        await selectConversation(newConv);
      }
    } finally {
      isLoading.value = false;
    }
  }

  Future<void> archiveConversation(String convId) async {
    final projectId = activeProjectId.value;
    if (projectId == null || projectId.isEmpty) {
      return;
    }
    final success = await _service.updateConversation(
      convId,
      projectId: projectId,
      archived: true,
    );
    if (success != null) {
      conversations.removeWhere((c) => c.id == convId);
      if (activeConversation.value?.id == convId) {
        if (conversations.isNotEmpty) {
          selectConversation(conversations.first);
        } else {
          activeConversation.value = null;
          messages.clear();
        }
      }
    }
  }

  final sendBlockedReason = ''.obs;

  Future<void> sendMessage({List<ChatAttachment>? attachments}) async {
    final content = textController.text.trim();
    if (content.isEmpty && (attachments == null || attachments.isEmpty)) {
      return;
    }

    // Chỉ direct user text được phép gửi tới model trong đợt này —
    // Global Constraint: "Attachments, retrieval, connector output,
    // autopilot, and copilot remain blocked" áp dụng cho MỌI trường hợp có
    // attachment, không chỉ riêng attachment-only (không có text kèm theo).
    // Vì vậy chặn ngay khi `attachments` không rỗng, bất kể `content` có
    // hay không, để không có caller tương lai nào vô tình forward
    // attachment egress ra ngoài phạm vi đợt này.
    if (attachments != null && attachments.isNotEmpty) {
      sendBlockedReason.value = 'Attachments are not supported yet. Send text only.';
      return;
    }

    if (!canSendMessage) {
      sendBlockedReason.value = dataAccess.value.categories.isEmpty
          ? 'Select a data access category before sending.'
          : 'Add a subject reference before sending personal data.';
      return;
    }

    final projectId = activeProjectId.value;
    if (projectId == null || projectId.isEmpty) {
      // Task 2 — surface trạng thái "cần Project" cục bộ, không dispatch bất
      // kỳ side effect nào (không tạo conversation, không gửi message).
      sendBlockedReason.value = 'Select a project before sending.';
      return;
    }
    sendBlockedReason.value = '';

    final dataAccessForRequest = dataAccess.value;

    if (activeConversation.value == null) {
      await createNewConversation();
    }
    final conv = activeConversation.value;
    if (conv == null) return;

    textController.clear();

    // 1. Optimistically append User message
    final userMessage = ChatMessage(
      id: 'temp-${DateTime.now().millisecondsSinceEpoch}',
      conversationId: conv.id,
      role: 'user',
      content: content,
      createdAt: DateTime.now(),
      attachments: attachments ?? [],
    );
    messages.add(userMessage);

    // 2. Prepare Assistant message placeholder
    final assistantMessage = ChatMessage(
      id: 'assistant-temp-${DateTime.now().millisecondsSinceEpoch}',
      conversationId: conv.id,
      role: 'assistant',
      content: '',
      status: 'started',
      createdAt: DateTime.now(),
    );
    messages.add(assistantMessage);
    _scrollToBottom();

    isStreaming.value = true;
    runStatus.value = 'running';
    reasoningStatus.value = 'Thinking...';
    toolActivities.clear();
    lastSequence.value = 0;

    try {
      // 3. Send message to backend
      final response = await _service.sendMessage(
        conv.id,
        projectId: projectId,
        content: content,
        dataAccess: dataAccessForRequest,
        attachments: attachments?.map((a) => a.toJson()).toList(),
      );

      if (response != null && response['run_id'] != null) {
        final runId = response['run_id'].toString();
        currentRunId.value = runId;
        // Reset classification sau khi gửi thành công — tránh rò rỉ
        // classification cũ (vd. SENSITIVE_PERSONAL) sang tin nhắn tiếp theo.
        dataAccess.value = const DataAccessDeclaration();
        _subscribeToSSE(runId, assistantMessage);
        return;
      }
    } catch (_) {
      // API từ chối request (ví dụ profile locale Control Plane tạm không
      // sẵn sàng) trước khi tạo run. Không để optimistic state mồ côi ở UI.
    }

    messages.remove(userMessage);
    messages.remove(assistantMessage);
    messages.refresh();
    textController.text = content;
    currentRunId.value = '';
    isStreaming.value = false;
    runStatus.value = 'failed';
    reasoningStatus.value = '';
    sendBlockedReason.value = 'Unable to start the agent. Please try again.';
  }

  void _subscribeToSSE(String runId, ChatMessage assistantMsg, {int? sinceSeq}) {
    _sseSubscription?.cancel();
    reconnecting.value = false;

    _sseSubscription = _service
        .streamRunEvents(
          runId,
          sinceSequence: sinceSeq ?? lastSequence.value,
          conversationId: assistantMsg.conversationId,
        )
        .listen(
      (event) {
        final seq = (event['sequence'] as num?)?.toInt() ?? 0;
        if (seq > lastSequence.value) {
          lastSequence.value = seq;
        }

        final eventType = event['event_type']?.toString() ?? '';
        final payload = (event['payload'] as Map<String, dynamic>?) ?? {};

        switch (eventType) {
          case 'run.started':
            runStatus.value = 'running';
            break;

          case 'reasoning.status':
            final statusStr = payload['status']?.toString() ?? 'thinking';
            final tool = payload['tool']?.toString();
            if (tool != null) {
              reasoningStatus.value = 'Executing tool: $tool...';
            } else {
              reasoningStatus.value = '$statusStr...';
            }
            break;

          case 'message.delta':
            final delta = payload['delta']?.toString() ?? '';
            assistantMsg.content += delta;
            messages.refresh();
            _scrollToBottom();
            break;

          case 'tool.started':
            final tName = payload['tool_name']?.toString() ?? 'tool';
            toolActivities.add(ChatToolActivity(
              toolName: tName,
              status: 'started',
              arguments: payload['arguments'] as Map<String, dynamic>?,
            ));
            reasoningStatus.value = 'Calling tool: $tName...';
            break;

          case 'tool.completed':
            final completedTool = payload['tool_name']?.toString() ?? '';
            final act = toolActivities.firstWhereOrNull((a) => a.toolName == completedTool && a.status == 'started');
            if (act != null) {
              act.status = 'completed';
              act.result = payload['result'];
              toolActivities.refresh();
            }
            break;

          case 'tool.failed':
            final failedTool = payload['tool_name']?.toString() ?? '';
            final act = toolActivities.firstWhereOrNull((a) => a.toolName == failedTool && a.status == 'started');
            if (act != null) {
              act.status = 'failed';
              act.error = payload['error']?.toString();
              toolActivities.refresh();
            }
            break;

          case 'approval.required':
            runStatus.value = 'waiting_approval';
            reasoningStatus.value = 'Approval required';
            final apprId = payload['approval_id']?.toString() ?? '';
            final appr = ChatApproval(
              id: apprId,
              runId: runId,
              action: payload['action']?.toString() ?? 'Action',
              subject: payload['subject']?.toString() ?? 'Sensitive action',
              requester: 'agent',
            );
            pendingApprovals.add(appr);
            break;

          case 'approval.resolved':
            final resolvedId = payload['approval_id']?.toString() ?? '';
            final appr = pendingApprovals.firstWhereOrNull((a) => a.id == resolvedId);
            if (appr != null) {
              appr.status = payload['status']?.toString() ?? 'APPROVED';
              pendingApprovals.refresh();
            }
            break;

          case 'run.completed':
            runStatus.value = 'completed';
            isStreaming.value = false;
            reasoningStatus.value = '';
            assistantMsg.status = 'completed';
            if (payload['output'] != null && assistantMsg.content.isEmpty) {
              assistantMsg.content = payload['output'].toString();
            }
            messages.refresh();
            break;

          case 'run.failed':
            runStatus.value = 'failed';
            isStreaming.value = false;
            reasoningStatus.value = '';
            assistantMsg.status = 'failed';
            if (payload['error'] != null) {
              assistantMsg.content += '\n\n[Error: ${payload['error']}]';
            }
            messages.refresh();
            break;

          case 'run.cancelled':
            runStatus.value = 'cancelled';
            isStreaming.value = false;
            reasoningStatus.value = 'Run cancelled';
            assistantMsg.status = 'failed';
            messages.refresh();
            break;
        }
      },
      onError: (err) {
        debugPrint('[ChatController] SSE stream error: $err. Attempting reconnect...');
        if (isStreaming.value) {
          reconnecting.value = true;
          // Reconnect with sinceSequence
          Future.delayed(const Duration(seconds: 1), () {
            if (isStreaming.value) {
              _subscribeToSSE(runId, assistantMsg, sinceSeq: lastSequence.value);
            }
          });
        }
      },
      onDone: () {
        if (isStreaming.value && runStatus.value == 'running') {
          isStreaming.value = false;
          runStatus.value = 'completed';
        }
      },
      cancelOnError: false,
    );
  }

  Future<void> cancelActiveRun() async {
    final runId = currentRunId.value;
    if (runId.isNotEmpty && isStreaming.value) {
      try {
        await _service.cancelRun(runId);
        runStatus.value = 'cancelled';
        isStreaming.value = false;
        reasoningStatus.value = 'Cancelled';
      } catch (e) {
        debugPrint('[ChatController] cancelActiveRun failed: $e');
        reasoningStatus.value = 'Failed to cancel run';
      }
    }
  }

  Future<void> handleApprovalDecision(
    String approvalId,
    bool approved, {
    String? reason,
  }) async {
    try {
      await _service.decideApproval(
        approvalId,
        approved: approved,
        reason: reason,
      );
      final appr = pendingApprovals.firstWhereOrNull((a) => a.id == approvalId);
      if (appr != null) {
        appr.status = approved ? 'APPROVED' : 'DENIED';
        pendingApprovals.refresh();
      }
    } catch (e) {
      debugPrint('[ChatController] handleApprovalDecision failed: $e');
      reasoningStatus.value = 'Failed to submit approval decision';
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (scrollController.hasClients) {
        scrollController.animateTo(
          scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 250),
          curve: Curves.easeOut,
        );
      }
    });
  }
}
