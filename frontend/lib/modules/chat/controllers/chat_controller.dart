import 'dart:async';
import 'package:flutter/foundation.dart';

import 'package:get/get.dart';
import 'package:uuid/uuid.dart';

import '../../../core/services/voice_service.dart';
import '../../../data/services/ai_service.dart';
import '../../../data/services/chat_service.dart';
import '../../../data/services/connectors_service.dart';

class ChatController extends GetxController {
  ChatController({
    ChatGateway? chatService,
    AiService? aiService,
    ConnectorsService? connectorsService,
    IVoiceService? voiceService,
  }) : _chatService = chatService ?? ChatService(),
       _aiService = aiService ?? AiService(),
       _connectorsService = connectorsService ?? ConnectorsService(),
       _voiceService = voiceService ?? VoiceService();

  final ChatGateway _chatService;
  final AiService _aiService;
  final ConnectorsService _connectorsService;
  final IVoiceService _voiceService;
  final _uuid = const Uuid();

  final sessions = [].obs;
  final currentSessionId = RxnString();
  final messages = [].obs;

  final models = [].obs;
  final Rxn<Map<String, dynamic>> selectedModel = Rxn<Map<String, dynamic>>();

  final isLoadingSessions = false.obs;
  final isLoadingMessages = false.obs;
  final isSending = false.obs;
  final isRecordingVoice = false.obs;

  Timer? _pollTimer;
  StreamSubscription<Map<String, dynamic>>? _streamSubscription;

  Future<void> toggleVoiceRecording() async {
    if (isRecordingVoice.value) {
      isRecordingVoice.value = false;
      final transcript = await _voiceService.stopRecordingAndTranscribe();
      if (transcript != null && transcript.trim().isNotEmpty) {
        await sendMessage(transcript);
      }
    } else {
      final started = await _voiceService.startRecording();
      // Only reflect "recording" in the UI if the mic actually started -
      // otherwise a denied permission (or unsupported web platform) would
      // show a listening indicator for a recording that never happened.
      isRecordingVoice.value = started;
    }
  }

  @override
  void onInit() {
    super.onInit();
    loadSessions();
    loadModels();
  }

  // Dùng khi getModels() trả về rỗng (vd. workspace_id chưa kịp cache lúc app khởi động
  // lại, xem DashboardController._ensureWorkspaceCached) để picker không hiện trống.
  //
  // CỐ TÌNH không có 'provider'/'model': đoán một cặp cứng ở client là nguồn gốc lỗi "Không
  // thể tạo phản hồi AI lúc này." - cặp đoán ra (deepseek/deepseek-chat) không có API key
  // trên server nên session tạo ra chết ngay từ câu đầu. Gửi null thì server tự điền
  // CHAT_DEFAULT_PROVIDER/MODEL, thứ chắc chắn đã được cấu hình.
  static const _fallbackDefaultModel = {'label': 'Model mặc định của máy chủ'};

  // true khi selectedModel hiện tại chỉ là fallback tĩnh (chưa có dữ liệu thật từ backend),
  // để lần loadModels() kế tiếp (vd. sau khi DashboardController cache xong workspace_id)
  // biết mà thay bằng model thật thay vì giữ nguyên fallback.
  bool _usingFallbackModel = false;

  Future<void> loadModels() async {
    final result = await _aiService.getModels();
    models.value = result;
    if (selectedModel.value == null || _usingFallbackModel) {
      if (result.isNotEmpty) {
        // Ưu tiên model có API key. Lấy đại phần tử đầu danh sách nghĩa là mọi đoạn chat
        // mới đều tạo với provider đầu tiên trong registry, kể cả khi provider đó chưa
        // được cấu hình - và người dùng chỉ biết khi câu trả lời báo lỗi.
        final configured = result.cast<Map<String, dynamic>>().firstWhere(
          (model) => model['configured'] == true,
          orElse: () => <String, dynamic>{},
        );
        selectedModel.value = Map<String, dynamic>.from(
          configured.isNotEmpty ? configured : result.first as Map,
        );
        _usingFallbackModel = false;
      } else if (selectedModel.value == null) {
        selectedModel.value = Map<String, dynamic>.from(_fallbackDefaultModel);
        _usingFallbackModel = true;
      }
    }
  }

  void selectModel(Map<String, dynamic> model) {
    // Đổi model chỉ áp dụng cho đoạn chat MỚI - session đã tạo giữ nguyên provider/model
    // đã chọn lúc tạo, khớp đúng thiết kế backend (mỗi session gắn 1 provider/model cố định).
    _usingFallbackModel = false;
    selectedModel.value = model;
  }

  @override
  void onClose() {
    _pollTimer?.cancel();
    _streamSubscription?.cancel();
    super.onClose();
  }

  Future<void> loadSessions() async {
    isLoadingSessions.value = true;
    try {
      sessions.value = await _chatService.getSessions();
    } finally {
      isLoadingSessions.value = false;
    }
  }

  void createNewSession() {
    _pollTimer?.cancel();
    currentSessionId.value = null;
    messages.clear();
    emailApprovals.clear();
    isSending.value = false;
  }

  Future<void> selectSession(String sessionId) async {
    _pollTimer?.cancel();
    currentSessionId.value = sessionId;
    await loadMessages();
    await loadEmailApprovals();
  }

  Future<void> deleteSession(String sessionId) async {
    final success = await _chatService.deleteSession(sessionId);
    if (success) {
      if (currentSessionId.value == sessionId) {
        createNewSession();
      }
      await loadSessions();
    } else {
      Get.snackbar('Lỗi', 'Không thể xóa đoạn chat',
          backgroundColor: Get.theme.colorScheme.error,
          colorText: Get.theme.colorScheme.onError);
    }
  }

  /// Đồng bộ picker với provider/model server thực sự gắn cho session vừa tạo.
  ///
  /// Chỉ cần thiết khi client gửi lên null (nhánh fallback) - lúc đó server mới là bên
  /// quyết định. Không làm thì header hiện một nhãn khác hẳn model đang trả lời.
  void _adoptSessionModel(Map<String, dynamic> session) {
    final provider = session['provider'] as String?;
    final model = session['model'] as String?;
    if (provider == null || model == null) return;
    if (selectedModel.value?['provider'] == provider &&
        selectedModel.value?['model'] == model) {
      return;
    }

    final known = models.cast<Map<String, dynamic>>().firstWhere(
      (item) => item['provider'] == provider && item['model'] == model,
      orElse: () => <String, dynamic>{},
    );
    selectedModel.value = known.isNotEmpty
        ? Map<String, dynamic>.from(known)
        : {'provider': provider, 'model': model, 'label': model};
    _usingFallbackModel = false;
  }

  Future<void> sendMessage(String content) async {
    final trimmedContent = content.trim();
    if (trimmedContent.isEmpty || isSending.value) return;

    isSending.value = true;
    try {
      var sessionId = currentSessionId.value;
      if (sessionId == null) {
        final session = await _chatService.createSession(
          provider: selectedModel.value?['provider'] as String?,
          model: selectedModel.value?['model'] as String?,
        );
        sessionId = session?['id'] as String?;
        if (sessionId == null) return;
        currentSessionId.value = sessionId;
        _adoptSessionModel(session!);
        await loadSessions();
      }

      final message = await _chatService.sendUserMessage(
        sessionId: sessionId,
        content: trimmedContent,
        clientMessageId: _uuid.v4(),
      );
      if (message == null) return;

      messages.add(message);
      _streamSubscription?.cancel();
      _streamSubscription = _chatService
          .streamSession(sessionId, afterMessageId: message['id'] as String?)
          .listen(
            _applyStreamEvent,
            onError: (_) =>
                _pollForAssistantReply(sessionId!, message['id'] as String?),
          );
    } finally {
      if ((_pollTimer == null || !_pollTimer!.isActive) &&
          _streamSubscription == null) {
        isSending.value = false;
      }
    }
  }

  static const _terminalStatuses = {'delivered', 'error', 'cancelled'};

  void _applyStreamEvent(Map<String, dynamic> event) {
    final id = event['id'];
    final index = messages.indexWhere((item) => item['id'] == id);

    if (event['type'] == 'delta') {
      // Delta chỉ mang phần text mới - nối vào, không thay thế.
      final chunk = (event['text'] as String?) ?? '';
      if (index >= 0) {
        final current = messages[index] as Map;
        messages[index] = {
          ...current,
          'content': ((current['content'] as String?) ?? '') + chunk,
        };
      } else {
        messages.add({
          'id': id,
          'role': 'assistant',
          'content': chunk,
          'status': 'streaming',
        });
      }
      return;
    }

    // Sự kiện `message` là ảnh chụp đầy đủ từ DB, luôn thắng phần nối từ delta.
    if (index >= 0) {
      messages[index] = {...messages[index] as Map, ...event};
    } else {
      messages.add(event);
    }

    if (_terminalStatuses.contains(event['status'])) {
      isSending.value = false;
      _streamSubscription?.cancel();
      loadSessions();
      // AI có thể vừa soạn xong một bản nháp đang chờ duyệt - nạp lại để thẻ duyệt hiện
      // ngay dưới câu trả lời thay vì đợi người dùng mở lại đoạn chat.
      loadEmailApprovals();
    }
  }

  // --- Thư AI soạn, chờ người duyệt ---

  final emailApprovals = <Map<String, dynamic>>[].obs;
  final decidingApprovalId = RxnString();

  Future<void> loadEmailApprovals() async {
    final sessionId = currentSessionId.value;
    if (sessionId == null) {
      emailApprovals.clear();
      return;
    }
    try {
      final result = await _connectorsService.getEmailApprovals(sessionId: sessionId);
      emailApprovals.value = result.cast<Map<String, dynamic>>();
    } catch (e) {
      debugPrint('[ChatController] loadEmailApprovals failed: $e');
    }
  }

  /// Bấm duyệt ở đây là hành động DUY NHẤT khiến thư rời hòm thư - model không có tool
  /// gửi thư, kể cả khi nội dung email nó vừa đọc có dụ nó làm vậy.
  Future<void> decideEmailApproval(String approvalId, {required bool approve}) async {
    decidingApprovalId.value = approvalId;
    try {
      final error = await _connectorsService.decideEmailApproval(
        approvalId,
        approve: approve,
      );
      if (error != null) {
        Get.snackbar('Không thực hiện được', error,
            backgroundColor: Get.theme.colorScheme.error,
            colorText: Get.theme.colorScheme.onError);
      } else {
        Get.snackbar(
          approve ? 'Đã gửi thư' : 'Đã bỏ qua',
          approve
              ? 'Thư đã được gửi đi từ hòm thư Gmail của bạn.'
              : 'Bản nháp vẫn nằm trong Gmail, bạn có thể tự sửa hoặc xoá.',
        );
      }
      await loadEmailApprovals();
    } finally {
      decidingApprovalId.value = null;
    }
  }

  Future<void> stopGenerating() async {
    final sessionId = currentSessionId.value;
    if (sessionId == null || !isSending.value) return;
    await _chatService.cancel(sessionId);
    // Không tắt isSending ở đây - để stream/poll tự cập nhật khi thấy status
    // 'cancelled', tránh lệch trạng thái nếu request cancel tới trễ hơn message cuối.
  }

  Future<void> loadMessages() async {
    final sessionId = currentSessionId.value;
    if (sessionId == null) return;

    isLoadingMessages.value = true;
    try {
      messages.value = await _chatService.getMessages(sessionId);
    } finally {
      isLoadingMessages.value = false;
    }
  }

  void _pollForAssistantReply(String sessionId, String? userMessageId) {
    _pollTimer?.cancel();
    _pollTimer = Timer.periodic(const Duration(seconds: 1), (timer) async {
      if (currentSessionId.value != sessionId) {
        timer.cancel();
        isSending.value = false;
        return;
      }

      final updatedMessages = await _chatService.getMessages(sessionId);
      messages.value = updatedMessages;
      final userMessageIndex = updatedMessages.indexWhere(
        (message) => message['id'] == userMessageId,
      );
      final hasAssistantReply =
          userMessageIndex >= 0 &&
          updatedMessages
              .skip(userMessageIndex + 1)
              .any((message) => message['role'] == 'assistant');
      if (hasAssistantReply) {
        timer.cancel();
        isSending.value = false;
        await loadSessions();
      }
    });
  }
}
