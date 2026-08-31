import 'package:flutter/material.dart';
import '../../../../core/services/secure_storage_service.dart';
import '../../../../core/theme/app_theme.dart';
import '../../models/workspace_orientation.dart';
import '../../services/workspace_orientation_service.dart';

class WorkspaceOrientationSettingsCard extends StatefulWidget {
  const WorkspaceOrientationSettingsCard({
    super.key,
    this.service,
    this.readWorkspaceId,
  });

  final WorkspaceOrientationService? service;
  final Future<String?> Function()? readWorkspaceId;

  @override
  State<WorkspaceOrientationSettingsCard> createState() =>
      _WorkspaceOrientationSettingsCardState();
}

class _WorkspaceOrientationSettingsCardState
    extends State<WorkspaceOrientationSettingsCard> {
  late final WorkspaceOrientationService _service;
  String? _workspaceId;
  WorkspaceOrientation? _orientation;
  bool _isLoading = true;
  String? _errorMessage;
  bool _isEditing = false;
  bool _isSaving = false;

  final TextEditingController _visionController = TextEditingController();
  final TextEditingController _missionController = TextEditingController();
  final TextEditingController _coreValuesController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _service = widget.service ?? WorkspaceOrientationService();
    _loadOrientation();
  }

  @override
  void dispose() {
    _visionController.dispose();
    _missionController.dispose();
    _coreValuesController.dispose();
    super.dispose();
  }

  Future<void> _loadOrientation() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final wsId = widget.readWorkspaceId != null
          ? await widget.readWorkspaceId!()
          : await SecureStorageService.read('workspace_id');

      if (wsId == null || wsId.isEmpty) {
        setState(() {
          _workspaceId = null;
          _isLoading = false;
        });
        return;
      }

      _workspaceId = wsId;
      final orientation = await _service.fetch(wsId);
      setState(() {
        _orientation = orientation;
        _isLoading = false;
        _isEditing = false;
        _populateControllers(orientation);
      });
    } catch (e) {
      setState(() {
        _errorMessage = e.toString();
        _isLoading = false;
      });
    }
  }

  void _populateControllers(WorkspaceOrientation? orientation) {
    _visionController.text = orientation?.vision ?? '';
    _missionController.text = orientation?.mission ?? '';
    _coreValuesController.text = orientation?.coreValues ?? '';
  }

  Future<void> _saveChanges() async {
    if (_workspaceId == null) return;
    setState(() {
      _isSaving = true;
      _errorMessage = null;
    });

    try {
      final updated = await _service.update(
        _workspaceId!,
        vision: _visionController.text.trim().isEmpty
            ? null
            : _visionController.text,
        mission: _missionController.text.trim().isEmpty
            ? null
            : _missionController.text,
        coreValues: _coreValuesController.text.trim().isEmpty
            ? null
            : _coreValuesController.text,
      );

      setState(() {
        _orientation = updated;
        _isSaving = false;
        _isEditing = false;
        _populateControllers(updated);
      });
    } catch (e) {
      setState(() {
        _errorMessage = e.toString();
        _isSaving = false;
      });
    }
  }

  Future<void> _clearOrientation() async {
    if (_workspaceId == null) return;
    setState(() {
      _isSaving = true;
      _errorMessage = null;
    });

    try {
      final updated = await _service.update(
        _workspaceId!,
        vision: null,
        mission: null,
        coreValues: null,
      );

      setState(() {
        _orientation = updated;
        _isSaving = false;
        _isEditing = false;
        _populateControllers(updated);
      });
    } catch (e) {
      setState(() {
        _errorMessage = e.toString();
        _isSaving = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B).withValues(alpha: 0.6),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withValues(alpha: 0.1)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildHeader(),
          const SizedBox(height: 16),
          _buildContent(),
        ],
      ),
    );
  }

  Widget _buildHeader() {
    return Row(
      children: [
        Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: AppTheme.primary.withValues(alpha: 0.15),
            borderRadius: BorderRadius.circular(10),
          ),
          child: const Icon(Icons.explore_rounded,
              color: AppTheme.primary, size: 22),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Định hướng workspace',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                'Ghi chú tuỳ chọn về đích đến dài hạn, mục tiêu và nguyên tắc của nhóm',
                style: TextStyle(
                  color: AppTheme.textMutedDark,
                  fontSize: 12,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildContent() {
    if (_isLoading) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: 24),
        child: Center(
          child: CircularProgressIndicator(color: AppTheme.primary),
        ),
      );
    }

    if (_errorMessage != null) {
      return Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: AppTheme.error.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: AppTheme.error.withValues(alpha: 0.3)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              _errorMessage!,
              style: const TextStyle(color: Colors.white, fontSize: 13),
            ),
            const SizedBox(height: 10),
            ElevatedButton.icon(
              onPressed: _loadOrientation,
              icon: const Icon(Icons.refresh_rounded, size: 16),
              label: const Text('Thử lại'),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.surfaceDarkElevated,
                foregroundColor: Colors.white,
              ),
            ),
          ],
        ),
      );
    }

    if (_workspaceId == null) {
      return Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.03),
          borderRadius: BorderRadius.circular(10),
        ),
        child: const Text(
          'Chưa chọn workspace',
          style: TextStyle(color: AppTheme.textMutedDark, fontSize: 13),
        ),
      );
    }

    if (!_isEditing && (_orientation == null || !_orientation!.hasContent)) {
      return _buildEmptyState();
    }

    if (!_isEditing && _orientation!.hasContent) {
      return _buildSummaryState();
    }

    return _buildEditForm();
  }

  Widget _buildEmptyState() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.03),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.white.withValues(alpha: 0.05)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: const Text(
                  'Chưa xác định',
                  style: TextStyle(
                    color: AppTheme.textMutedDark,
                    fontSize: 12,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          const Text(
            'Các ghi chú định hướng là hoàn toàn không bắt buộc. Bạn có thể bổ sung bất kỳ lúc nào để làm tài liệu tham chiếu chung.',
            style: TextStyle(
              color: AppTheme.textMutedDark,
              fontSize: 13,
              height: 1.4,
            ),
          ),
          const SizedBox(height: 14),
          ElevatedButton.icon(
            onPressed: () {
              setState(() {
                _isEditing = true;
              });
            },
            icon: const Icon(Icons.add_rounded, size: 16),
            label: const Text('Thêm định hướng'),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppTheme.primaryDark,
              foregroundColor: Colors.white,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSummaryState() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (_orientation?.vision != null && _orientation!.vision!.isNotEmpty) ...[
          _buildItemDisplay(
            label: 'Đích đến dài hạn (Vision)',
            value: _orientation!.vision!,
          ),
          const SizedBox(height: 12),
        ],
        if (_orientation?.mission != null && _orientation!.mission!.isNotEmpty) ...[
          _buildItemDisplay(
            label: 'Vấn đề/kết quả đang hướng tới (Mission)',
            value: _orientation!.mission!,
          ),
          const SizedBox(height: 12),
        ],
        if (_orientation?.coreValues != null &&
            _orientation!.coreValues!.isNotEmpty) ...[
          _buildItemDisplay(
            label: 'Nguyên tắc không muốn đánh đổi (Core Values)',
            value: _orientation!.coreValues!,
          ),
          const SizedBox(height: 12),
        ],
        const SizedBox(height: 6),
        Row(
          children: [
            ElevatedButton.icon(
              onPressed: () {
                setState(() {
                  _isEditing = true;
                });
              },
              icon: const Icon(Icons.edit_rounded, size: 16),
              label: const Text('Chỉnh sửa'),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.surfaceDarkElevated,
                foregroundColor: Colors.white,
              ),
            ),
            const SizedBox(width: 12),
            OutlinedButton.icon(
              onPressed: _isSaving ? null : _clearOrientation,
              icon: const Icon(Icons.delete_outline_rounded,
                  size: 16, color: AppTheme.error),
              label: const Text(
                'Xóa định hướng',
                style: TextStyle(color: AppTheme.error),
              ),
              style: OutlinedButton.styleFrom(
                side: BorderSide(color: AppTheme.error.withValues(alpha: 0.5)),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildItemDisplay({required String label, required String value}) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.03),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: Colors.white.withValues(alpha: 0.06)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: const TextStyle(
              color: AppTheme.textAccent,
              fontSize: 12,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            value,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 13,
              height: 1.4,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildEditForm() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildTextField(
          controller: _visionController,
          label: 'Đích đến dài hạn (Vision)',
          hint: 'Ví dụ: Trở thành nền tảng số 1...',
        ),
        const SizedBox(height: 14),
        _buildTextField(
          controller: _missionController,
          label: 'Vấn đề/kết quả đang hướng tới (Mission)',
          hint: 'Ví dụ: Trao quyền cho founder bằng dữ liệu thật...',
        ),
        const SizedBox(height: 14),
        _buildTextField(
          controller: _coreValuesController,
          label: 'Nguyên tắc không muốn đánh đổi (Core Values)',
          hint: 'Ví dụ: Minh bạch, Tốc độ, Lấy khách hàng làm trung tâm...',
        ),
        const SizedBox(height: 16),
        Row(
          children: [
            ElevatedButton.icon(
              onPressed: _isSaving ? null : _saveChanges,
              icon: _isSaving
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: Colors.white,
                      ),
                    )
                  : const Icon(Icons.save_rounded, size: 16),
              label: Text(_isSaving ? 'Đang lưu...' : 'Lưu thay đổi'),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.primary,
                foregroundColor: Colors.white,
              ),
            ),
            const SizedBox(width: 10),
            TextButton(
              onPressed: _isSaving
                  ? null
                  : () {
                      setState(() {
                        _isEditing = false;
                        _populateControllers(_orientation);
                      });
                    },
              child: const Text(
                'Hủy',
                style: TextStyle(color: AppTheme.textMutedDark),
              ),
            ),
            if (_orientation != null && _orientation!.hasContent) ...[
              const Spacer(),
              OutlinedButton.icon(
                onPressed: _isSaving ? null : _clearOrientation,
                icon: const Icon(Icons.delete_outline_rounded,
                    size: 16, color: AppTheme.error),
                label: const Text(
                  'Xóa định hướng',
                  style: TextStyle(color: AppTheme.error),
                ),
                style: OutlinedButton.styleFrom(
                  side: BorderSide(
                      color: AppTheme.error.withValues(alpha: 0.5)),
                ),
              ),
            ],
          ],
        ),
      ],
    );
  }

  Widget _buildTextField({
    required TextEditingController controller,
    required String label,
    required String hint,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 13,
            fontWeight: FontWeight.w500,
          ),
        ),
        const SizedBox(height: 6),
        TextField(
          controller: controller,
          maxLines: 2,
          minLines: 1,
          style: const TextStyle(color: Colors.white, fontSize: 13),
          decoration: InputDecoration(
            hintText: hint,
            hintStyle: TextStyle(
              color: AppTheme.textMutedDark.withValues(alpha: 0.6),
              fontSize: 13,
            ),
            filled: true,
            fillColor: const Color(0xFF0F172A).withValues(alpha: 0.8),
            contentPadding:
                const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
              borderSide: BorderSide(color: Colors.white.withValues(alpha: 0.1)),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
              borderSide: BorderSide(color: Colors.white.withValues(alpha: 0.1)),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
              borderSide: const BorderSide(color: AppTheme.primary),
            ),
          ),
        ),
      ],
    );
  }
}
