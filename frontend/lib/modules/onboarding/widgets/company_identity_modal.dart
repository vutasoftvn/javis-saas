import 'dart:async';

import 'package:flutter/material.dart';

import '../../chat/models/data_access_declaration.dart';
import '../../chat/services/agent_chat_service.dart';
import '../services/company_identity_draft_parser.dart';
import '../services/company_identity_service.dart';

/// Modal chặn cứng bắt founder điền Vision/Mission/Core Values — dùng chung
/// cho cả luồng "workspace vừa tạo" lẫn "đăng nhập vào workspace cũ thiếu
/// dữ liệu" (gate duy nhất, xem HubAuthMixin.ensureAuthenticated).
/// KHÔNG có nút đóng — founder phải lưu xong mới rời được màn hình này.
class CompanyIdentityModal extends StatefulWidget {
  const CompanyIdentityModal({required this.workspaceId, super.key});

  final String workspaceId;

  @override
  State<CompanyIdentityModal> createState() => _CompanyIdentityModalState();
}

class _CompanyIdentityModalState extends State<CompanyIdentityModal> {
  final _visionController = TextEditingController();
  final _missionController = TextEditingController();
  final _valuesController = TextEditingController();
  final _service = CompanyIdentityService();

  final _chatService = AgentChatService();
  String? _conversationId;
  StreamSubscription<Map<String, dynamic>>? _aiSseSubscription;
  bool _isAiLoading = false;

  static const _aiDataAccess = DataAccessDeclaration(
    categories: {DataAccessCategory.businessConfidential},
  );

  bool _isSaving = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    for (final c in [_visionController, _missionController, _valuesController]) {
      c.addListener(() => setState(() {}));
    }
  }

  @override
  void dispose() {
    _aiSseSubscription?.cancel();
    _visionController.dispose();
    _missionController.dispose();
    _valuesController.dispose();
    super.dispose();
  }

  bool get _canSave =>
      _visionController.text.trim().isNotEmpty &&
      _missionController.text.trim().isNotEmpty &&
      _valuesController.text.trim().isNotEmpty &&
      !_isSaving;

  Future<void> _save() async {
    if (!_canSave) {
      return;
    }
    setState(() {
      _isSaving = true;
      _errorMessage = null;
    });
    try {
      await _service.save(
        widget.workspaceId,
        vision: _visionController.text.trim(),
        mission: _missionController.text.trim(),
        coreValues: _valuesController.text.trim(),
      );
      // Thành công — signal completion và thoát modal
      if (mounted) {
        Navigator.of(context).pop(true);
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isSaving = false;
          _errorMessage = 'Không lưu được: $e';
        });
      }
    }
  }

  Future<void> _askAiToDraft() async {
    setState(() {
      _isAiLoading = true;
      _errorMessage = null;
    });
    try {
      _conversationId ??= (await _chatService.createConversation(
        title: 'Company Identity Draft',
        activeAgentProfile: 'strategy',
      ))
          ?.id;
      final conversationId = _conversationId;
      if (conversationId == null) {
        throw Exception('Không tạo được conversation với COSA runtime.');
      }

      final response = await _chatService.sendMessage(
        conversationId,
        content:
            'Hãy soạn Vision, Mission và Core Values cho công ty này. '
            'Trả lời ĐÚNG định dạng sau, mỗi mục một dòng bắt đầu bằng nhãn viết hoa:\n'
            'VISION: <nội dung>\nMISSION: <nội dung>\nVALUES: <nội dung>',
        dataAccess: _aiDataAccess,
      );
      final runId = response?['run_id']?.toString();
      if (runId == null) {
        throw Exception('COSA runtime không trả về run_id.');
      }
      _subscribeAiSse(runId);
    } catch (e) {
      setState(() {
        _errorMessage = 'Không nhờ được AI soạn: $e';
        _isAiLoading = false;
      });
    }
  }

  void _subscribeAiSse(String runId) {
    final buffer = StringBuffer();
    _aiSseSubscription?.cancel();
    _aiSseSubscription = _chatService.streamRunEvents(runId).listen(
      (event) {
        final eventType = event['event_type']?.toString() ?? '';
        final payload = (event['payload'] as Map<String, dynamic>?) ?? {};
        if (eventType == 'message.delta') {
          buffer.write(payload['delta']?.toString() ?? '');
        } else if (eventType == 'run.completed' ||
            eventType == 'run.failed' ||
            eventType == 'run.cancelled') {
          _applyAiDraft(buffer.toString());
        }
      },
      onError: (_) => setState(() {
        _isAiLoading = false;
        _errorMessage = 'Mất kết nối khi nhận câu trả lời từ AI — vui lòng thử lại.';
      }),
      onDone: () => setState(() => _isAiLoading = false),
    );
  }

  void _applyAiDraft(String rawText) {
    final draft = parseCompanyIdentityDraft(rawText);
    setState(() {
      // Chỉ điền các mục AI thực sự trả lời đúng định dạng — không ghi đè
      // những gì founder đã gõ bằng field null/rỗng, và không đổ text thô
      // vào Vision (Vision sẽ được lưu thẳng làm dữ liệu công ty thật).
      if (draft.vision != null && draft.vision!.trim().isNotEmpty) {
        _visionController.text = draft.vision!;
      }
      if (draft.mission != null && draft.mission!.trim().isNotEmpty) {
        _missionController.text = draft.mission!;
      }
      if (draft.coreValues != null && draft.coreValues!.trim().isNotEmpty) {
        _valuesController.text = draft.coreValues!;
      }
      if (!draft.isComplete && rawText.trim().isNotEmpty) {
        _errorMessage =
            'AI trả lời chưa đủ định dạng — đã điền phần đọc được, vui lòng tự bổ sung phần còn thiếu.';
      }
      _isAiLoading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: false,
      child: Dialog(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
              const Text(
                'Thiết lập Vision / Mission / Core Values',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              const Text(
                'Founder cần điền đủ 3 mục này trước khi vào Command Center.',
              ),
              const SizedBox(height: 16),
              Align(
                alignment: Alignment.centerLeft,
                child: OutlinedButton(
                  onPressed: _isAiLoading ? null : _askAiToDraft,
                  child: _isAiLoading
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Text('Nhờ AI soạn'),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                key: const Key('company_identity_vision_field'),
                controller: _visionController,
                maxLines: 3,
                decoration: const InputDecoration(labelText: 'Vision'),
              ),
              const SizedBox(height: 12),
              TextField(
                key: const Key('company_identity_mission_field'),
                controller: _missionController,
                maxLines: 3,
                decoration: const InputDecoration(labelText: 'Mission'),
              ),
              const SizedBox(height: 12),
              TextField(
                key: const Key('company_identity_values_field'),
                controller: _valuesController,
                maxLines: 3,
                decoration: const InputDecoration(labelText: 'Core Values'),
              ),
              if (_errorMessage != null) ...[
                const SizedBox(height: 12),
                Text(_errorMessage!, style: const TextStyle(color: Colors.red)),
              ],
              const SizedBox(height: 20),
              Align(
                alignment: Alignment.centerRight,
                child: ElevatedButton(
                  onPressed: _canSave ? _save : null,
                  child: _isSaving
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Text('Lưu'),
                ),
              ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
