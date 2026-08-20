import 'dart:async';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:uuid/uuid.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../../../modules/auth/services/auth_service.dart';
import '../../../../modules/dashboard/services/hub_service.dart';
import '../../../../modules/hologram_hub/services/chat_service.dart';
import '../../domain/hologram_runtime_state.dart';

mixin HubChatMixin on GetxController {
  // ── Abstract service getters ─────────────────────────────────────────────
  AuthService get authService;
  HubService get hubService;
  ChatService get chatService;

  // ── Shared state refs (provided by HubCommandMixin) ──────────────────────
  // These are declared in HubCommandMixin and accessed here via the merged class.
  RxList<Map<String, dynamic>> get mobileMessages;
  RxBool get showMobileHistory;

  // ── Observables (owned by this mixin) ────────────────────────────────────
  final runtimeState = HologramRuntimeState.idle.obs;
  final latestTelemetry = Rxn<Map<String, dynamic>>();

  // ── Internal state ───────────────────────────────────────────────────────
  String? _activeChatSessionId;
  StreamSubscription<Map<String, dynamic>>? _hubChatStreamSub;
  Timer? _resetStateTimer;
  final _uuid = const Uuid();

  void cancelChatStream() => _hubChatStreamSub?.cancel();
  void cancelResetTimer() => _resetStateTimer?.cancel();

  // ── Quick Commands ───────────────────────────────────────────────────────

  void handleQuickCommand(String command) {
    if (command == 'Tổng quan hôm nay' || command == 'daily_brief') {
      runQuickAction('daily_brief', 'Tổng quan vận hành hôm nay');
    } else if (command == 'Kiểm tra công việc' ||
        command == 'Kiểm tra tiến độ OKRs' ||
        command == 'okr_check') {
      runQuickAction('okr_check', 'Kiểm tra tiến độ OKRs');
    } else if (command == 'Nhiệm vụ ưu tiên' ||
        command == 'Nhiệm vụ cần ưu tiên giải quyết' ||
        command == 'task_prioritize') {
      runQuickAction('task_prioritize', 'Nhiệm vụ cần ưu tiên giải quyết');
    } else if (command == 'Báo cáo tài chính' ||
        command == 'Tóm tắt tài chính' ||
        command == 'finance_summary') {
      runQuickAction('finance_summary', 'Báo cáo tóm tắt tài chính');
    } else {
      executePrompt(command);
    }
  }

  Future<void> runQuickAction(String actionKey, String userLabel) async {
    runtimeState.value = HologramRuntimeState.thinking;
    mobileMessages.add({'role': 'user', 'text': userLabel});
    showMobileHistory.value = true;
    final int assistantIndex = mobileMessages.length;
    mobileMessages.add({
      'role': 'assistant',
      'text': 'Đang kết nối COSA Capability Pipeline...',
      'status': 'streaming',
    });

    try {
      final res = await hubService.executeQuickAction(actionKey);
      if (res != null) {
        final content =
            res['content_markdown'] as String? ?? 'Hoàn thành xử lý.';
        latestTelemetry.value = res;
        mobileMessages[assistantIndex] = {
          'role': 'assistant',
          'text': content,
          'status': 'delivered',
          'run_id': res['run_id']?.toString() ?? '',
          'capability': res['capability']?.toString() ?? '',
          'prompt_version': res['prompt_version']?.toString() ?? '',
          'tools_used': (res['tools_used'] as List?)?.join(', ') ?? '',
          'latency_ms': res['latency_ms']?.toString() ?? '',
        };
        runtimeState.value = HologramRuntimeState.success;
      } else {
        mobileMessages[assistantIndex] = {
          'role': 'assistant',
          'text': 'Không thể thực thi capability $actionKey.',
          'status': 'error',
        };
        runtimeState.value = HologramRuntimeState.error;
      }
    } catch (e) {
      mobileMessages[assistantIndex] = {
        'role': 'assistant',
        'text': 'Lỗi khi gọi capability: $e',
        'status': 'error',
      };
      runtimeState.value = HologramRuntimeState.error;
    } finally {
      scheduleResetRuntimeState();
    }
  }

  // ── Main chat execution ──────────────────────────────────────────────────

  Future<void> executePrompt(String prompt) async {
    final trimmedPrompt = prompt.trim();
    if (trimmedPrompt.isEmpty) return;

    runtimeState.value = HologramRuntimeState.thinking;
    mobileMessages.add({'role': 'user', 'text': trimmedPrompt});
    showMobileHistory.value = true;

    final int assistantIndex = mobileMessages.length;
    mobileMessages.add({'role': 'assistant', 'text': '', 'status': 'streaming'});

    try {
      if (_activeChatSessionId == null) {
        final prefs = await SharedPreferences.getInstance();
        if (prefs.getString('workspace_id') == null ||
            prefs.getString('brain_id') == null) {
          debugPrint(
            '[HologramHub] workspace_id/brain_id missing – refreshing via getMe()',
          );
          await authService.getMe();
        }
        final session = await chatService.createSession(title: 'COSA Hub Chat');
        debugPrint('[HologramHub] createSession response: $session');
        _activeChatSessionId = session?['id'] as String?;
      }

      if (_activeChatSessionId == null) {
        mobileMessages[assistantIndex] = {
          'role': 'assistant',
          'text': 'Không thể kết nối phiên làm việc với COSA Brain.',
          'status': 'error',
        };
        runtimeState.value = HologramRuntimeState.error;
        scheduleResetRuntimeState();
        return;
      }

      final userMsg = await chatService.sendUserMessage(
        sessionId: _activeChatSessionId!,
        content: trimmedPrompt,
        clientMessageId: _uuid.v4(),
      );

      if (userMsg == null) {
        mobileMessages[assistantIndex] = {
          'role': 'assistant',
          'text': 'Không thể gửi tin nhắn đến máy chủ.',
          'status': 'error',
        };
        runtimeState.value = HologramRuntimeState.error;
        scheduleResetRuntimeState();
        return;
      }

      _hubChatStreamSub?.cancel();
      String fullAssistantText = '';

      _hubChatStreamSub = chatService
          .streamSession(
            _activeChatSessionId!,
            afterMessageId: userMsg['id'] as String?,
          )
          .listen(
            (event) {
              final type = event['type'];
              if (type == 'delta') {
                final chunk = (event['text'] as String?) ?? '';
                fullAssistantText += chunk;
                if (assistantIndex < mobileMessages.length) {
                  mobileMessages[assistantIndex] = {
                    'role': 'assistant',
                    'text': fullAssistantText,
                    'status': 'streaming',
                  };
                }
              } else if (type == 'message') {
                final content =
                    (event['content'] as String?) ?? (event['text'] as String?) ?? '';
                if (content.isNotEmpty) fullAssistantText = content;
                final status = event['status'] as String? ?? 'delivered';
                final proposals = (event['proposals'] as List?) ??
                    (event['citations'] is Map
                        ? (event['citations']['proposals'] as List?)
                        : null);

                if (assistantIndex < mobileMessages.length) {
                  mobileMessages[assistantIndex] = {
                    'role': 'assistant',
                    'text': fullAssistantText,
                    'status': status,
                    if (proposals != null && proposals.isNotEmpty)
                      'proposals': proposals,
                  };
                }
                if (status == 'delivered' ||
                    status == 'error' ||
                    status == 'cancelled') {
                  runtimeState.value = status == 'error'
                      ? HologramRuntimeState.error
                      : HologramRuntimeState.success;
                  scheduleResetRuntimeState();
                  _hubChatStreamSub?.cancel();
                  if (status == 'delivered') loadNeedsYou();
                }
              }
            },
            onError: (err) async {
              debugPrint(
                '[HologramHub] Stream error: $err, fallback fetching messages',
              );
              try {
                final msgs = await chatService.getMessages(_activeChatSessionId!);
                final lastAssistant = msgs.reversed.firstWhere(
                  (m) => (m as Map)['role'] == 'assistant',
                  orElse: () => null,
                );
                if (lastAssistant != null) {
                  final content =
                      (lastAssistant as Map)['content'] as String? ?? '';
                  final proposals = lastAssistant['proposals'] ??
                      (lastAssistant['citations'] is Map
                          ? lastAssistant['citations']['proposals']
                          : null);
                  if (assistantIndex < mobileMessages.length) {
                    mobileMessages[assistantIndex] = {
                      'role': 'assistant',
                      'text': content.isNotEmpty ? content : fullAssistantText,
                      'status': 'delivered',
                      if (proposals != null &&
                          (proposals is List) &&
                          proposals.isNotEmpty)
                        'proposals': proposals,
                    };
                  }
                  runtimeState.value = HologramRuntimeState.success;
                  loadNeedsYou();
                } else {
                  if (assistantIndex < mobileMessages.length) {
                    mobileMessages[assistantIndex] = {
                      'role': 'assistant',
                      'text': fullAssistantText.isNotEmpty
                          ? fullAssistantText
                          : 'Đã nhận yêu cầu nhưng máy chủ chưa phản hồi.',
                      'status':
                          fullAssistantText.isNotEmpty ? 'delivered' : 'error',
                    };
                  }
                  runtimeState.value = fullAssistantText.isNotEmpty
                      ? HologramRuntimeState.success
                      : HologramRuntimeState.error;
                }
              } catch (_) {
                if (assistantIndex < mobileMessages.length) {
                  mobileMessages[assistantIndex] = {
                    'role': 'assistant',
                    'text': fullAssistantText.isNotEmpty
                        ? fullAssistantText
                        : 'Không thể kết nối đến máy chủ.',
                    'status':
                        fullAssistantText.isNotEmpty ? 'delivered' : 'error',
                  };
                }
                runtimeState.value = fullAssistantText.isNotEmpty
                    ? HologramRuntimeState.success
                    : HologramRuntimeState.error;
              }
              scheduleResetRuntimeState();
            },
            onDone: () {
              if (assistantIndex < mobileMessages.length &&
                  mobileMessages[assistantIndex]['status'] == 'streaming') {
                mobileMessages[assistantIndex] = {
                  'role': 'assistant',
                  'text': fullAssistantText,
                  'status': 'delivered',
                };
                runtimeState.value = HologramRuntimeState.success;
                scheduleResetRuntimeState();
                loadNeedsYou();
              }
            },
          );
    } catch (e) {
      debugPrint('[HologramHub] Error executing prompt: $e');
      if (assistantIndex < mobileMessages.length) {
        mobileMessages[assistantIndex] = {
          'role': 'assistant',
          'text': 'Lỗi tạo phản hồi: $e',
          'status': 'error',
        };
      }
      runtimeState.value = HologramRuntimeState.error;
      scheduleResetRuntimeState();
    }
  }

  void scheduleResetRuntimeState() {
    _resetStateTimer?.cancel();
    _resetStateTimer = Timer(const Duration(seconds: 2), () {
      runtimeState.value = HologramRuntimeState.idle;
    });
  }

  void clearMobileHistory() => mobileMessages.clear();
  void toggleMobileHistory() =>
      showMobileHistory.value = !showMobileHistory.value;

  // ── Must be implemented by HubCommandMixin ───────────────────────────────
  Future<void> loadNeedsYou();
}
