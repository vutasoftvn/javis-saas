import 'package:flutter/material.dart';

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

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: false,
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
    );
  }
}
