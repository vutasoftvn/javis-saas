import 'package:flutter/material.dart';
import 'package:frontend/core/theme/app_theme.dart';
import 'package:frontend/modules/strategy/models/strategy_workflow_models.dart';

class BscFocusScopeStep extends StatefulWidget {
  final StrategicObjectiveModel selectedObjective;
  final WorkspaceStrategySettingsModel settings;
  final List<BscFocusScopeModel> focusScopes;
  final Future<void> Function(List<BscFocusScopeModel> scopes) onSaveFocusScopes;
  final VoidCallback onNext;
  final VoidCallback onBack;

  const BscFocusScopeStep({
    super.key,
    required this.selectedObjective,
    required this.settings,
    required this.focusScopes,
    required this.onSaveFocusScopes,
    required this.onNext,
    required this.onBack,
  });

  @override
  State<BscFocusScopeStep> createState() => _BscFocusScopeStepState();
}

class _BscFocusScopeStepState extends State<BscFocusScopeStep> {
  late List<BscFocusScopeModel> _currentScopes;
  bool _isSaving = false;
  String? _errorMessage;

  // Controllers for adding a new scope
  BscPerspective? _selectedPerspective;
  final _focusDescController = TextEditingController();
  final _weightController = TextEditingController(text: '1.0');
  bool _isAdding = false;

  @override
  void initState() {
    super.initState();
    _currentScopes = List.from(widget.focusScopes);
    final available = _availablePerspectives;
    if (available.isNotEmpty) {
      _selectedPerspective = available.first;
    }
  }

  @override
  void didUpdateWidget(covariant BscFocusScopeStep oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.focusScopes != widget.focusScopes) {
      _currentScopes = List.from(widget.focusScopes);
    }
  }

  @override
  void dispose() {
    _focusDescController.dispose();
    _weightController.dispose();
    super.dispose();
  }

  List<BscPerspective> get _availablePerspectives {
    if (widget.settings.enabledBscPerspectives.isNotEmpty) {
      return widget.settings.enabledBscPerspectives
          .where((p) => p != BscPerspective.unknown)
          .toList();
    }
    return [
      BscPerspective.financial,
      BscPerspective.customer,
      BscPerspective.internalProcess,
      BscPerspective.learningAndGrowth,
    ];
  }

  bool get _canProceed {
    if (widget.settings.bscMode == BscMode.off) return true;
    if (widget.settings.bscMode == BscMode.optional) return true;
    // For required mode, must have at least one focus scope
    return _currentScopes.isNotEmpty;
  }

  Future<void> _handleAddScope() async {
    final desc = _focusDescController.text.trim();
    if (desc.isEmpty || _selectedPerspective == null) return;
    final weight = double.tryParse(_weightController.text.trim()) ?? 1.0;

    final newScope = BscFocusScopeModel(
      id: 'temp_${DateTime.now().millisecondsSinceEpoch}',
      strategicObjectiveId: widget.selectedObjective.id,
      perspective: _selectedPerspective!,
      focusDescription: desc,
      weight: weight,
    );

    setState(() {
      _currentScopes.add(newScope);
      _isAdding = false;
      _focusDescController.clear();
      _weightController.text = '1.0';
    });

    await _persistScopes();
  }

  Future<void> _handleRemoveScope(int index) async {
    setState(() {
      _currentScopes.removeAt(index);
    });
    await _persistScopes();
  }

  Future<void> _persistScopes() async {
    setState(() {
      _isSaving = true;
      _errorMessage = null;
    });
    try {
      await widget.onSaveFocusScopes(_currentScopes);
    } catch (e) {
      setState(() {
        _errorMessage = 'Lỗi lưu trọng tâm BSC: $e';
      });
    } finally {
      if (mounted) setState(() => _isSaving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final bscMode = widget.settings.bscMode;

    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildObjectiveContextCard(),
          const SizedBox(height: 16),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Bước 2: Xác định trọng tâm Balanced Scorecard (BSC)',
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(
                            fontWeight: FontWeight.bold,
                            color: Colors.white,
                          ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      _getModeSubtitle(bscMode),
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            color: Colors.white70,
                          ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              if (bscMode != BscMode.off && !_isAdding)
                ElevatedButton.icon(
                  key: const Key('btn_add_scope'),
                  onPressed: () => setState(() => _isAdding = true),
                  icon: const Icon(Icons.add, size: 18),
                  label: const Text('Thêm trọng tâm'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.primaryColor,
                    foregroundColor: Colors.white,
                  ),
                ),
            ],
          ),
        const SizedBox(height: 16),
        if (_errorMessage != null)
          Container(
            padding: const EdgeInsets.all(12),
            margin: const EdgeInsets.only(bottom: 16),
            decoration: BoxDecoration(
              color: Colors.red.withValues(alpha: 0.2),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: Colors.redAccent),
            ),
            child: Text(_errorMessage!, style: const TextStyle(color: Colors.redAccent)),
          ),
        if (bscMode == BscMode.off) _buildBscOffNotice(),
        if (bscMode != BscMode.off && _isAdding) _buildAddScopeForm(),
        if (bscMode != BscMode.off && _currentScopes.isEmpty && !_isAdding) _buildEmptyScopesNotice(bscMode),
        if (bscMode != BscMode.off && _currentScopes.isNotEmpty) _buildScopesList(),
        const SizedBox(height: 24),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            OutlinedButton.icon(
              key: const Key('btn_back_step'),
              onPressed: widget.onBack,
              icon: const Icon(Icons.arrow_back, size: 18),
              label: const Text('Quay lại: Mục tiêu'),
            ),
            ElevatedButton.icon(
              key: const Key('btn_next_step'),
              onPressed: _canProceed && !_isSaving ? widget.onNext : null,
              icon: const Icon(Icons.arrow_forward, size: 18),
              label: Text(bscMode == BscMode.off
                  ? 'Bỏ qua & Sang phân tích'
                  : (bscMode == BscMode.optional && _currentScopes.isEmpty
                      ? 'Bỏ qua & Tiếp tục'
                      : 'Tiếp tục: Phân tích chiến lược')),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.primaryColor,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
              ),
            ),
          ],
        ),
      ],
    ),
  );
}

  String _getModeSubtitle(BscMode mode) {
    switch (mode) {
      case BscMode.off:
        return 'Chế độ BSC đang TẮT theo chính sách Workspace.';
      case BscMode.optional:
        return 'Chế độ BSC TÙY CHỌN: bạn có thể thiết lập trọng tâm hoặc bỏ qua.';
      case BscMode.required:
        return 'Chế độ BSC BẮT BUỘC: bạn phải xác định ít nhất 1 trọng tâm để lọc phân tích.';
      case BscMode.unknown:
        return 'Xác định định hướng các khía cạnh cân bằng';
    }
  }

  Widget _buildObjectiveContextCard() {
    return Container(
      key: const Key('selected_objective_context_card'),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: Colors.blueAccent.withValues(alpha: 0.4)),
      ),
      child: Row(
        children: [
          const Icon(Icons.flag, color: Colors.blueAccent, size: 20),
          const SizedBox(width: 8),
          Expanded(
            child: RichText(
              text: TextSpan(
                style: const TextStyle(fontSize: 13, color: Colors.white),
                children: [
                  const TextSpan(
                    text: 'Mục tiêu đang chọn: ',
                    style: TextStyle(color: Colors.white60),
                  ),
                  TextSpan(
                    text: widget.selectedObjective.title,
                    style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.white),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildBscOffNotice() {
    return Container(
      key: const Key('bsc_off_notice'),
      width: double.infinity,
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.white10),
      ),
      child: Column(
        children: [
          const Icon(Icons.layers_clear, size: 40, color: Colors.white38),
          const SizedBox(height: 12),
          Text(
            'Mô hình Balanced Scorecard (BSC) đang bị TẮT',
            style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
          ),
          SizedBox(height: 6),
          Text(
            'Cấu hình Workspace đang áp dụng phương pháp Chiến lược cổ điển (Classic Strategy), '
            'bỏ qua bộ lọc BSC và đi thẳng vào phân tích PESTEL & Nguồn lực.',
            style: TextStyle(color: Colors.white70, fontSize: 13),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 16),
          ElevatedButton.icon(
            key: const Key('btn_bsc_skip'),
            onPressed: widget.onNext,
            icon: const Icon(Icons.arrow_forward, size: 16),
            label: const Text('Bỏ qua & Tiếp tục'),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppTheme.primaryColor,
              foregroundColor: Colors.white,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyScopesNotice(BscMode mode) {
    final isRequired = mode == BscMode.required;

    return Container(
      key: const Key('empty_bsc_scopes_notice'),
      width: double.infinity,
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: isRequired ? Colors.amber.withValues(alpha: 0.5) : Colors.white10,
        ),
      ),
      child: Column(
        children: [
          Icon(
            isRequired ? Icons.warning_amber_rounded : Icons.info_outline,
            size: 40,
            color: isRequired ? Colors.amber : Colors.white38,
          ),
          const SizedBox(height: 12),
          Text(
            isRequired ? 'Bắt buộc cấu hình Trọng tâm BSC' : 'Chưa thiết lập Trọng tâm BSC',
            style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 6),
          Text(
            isRequired
                ? 'Theo chính sách của Không gian làm việc, bạn phải thiết lập ít nhất 1 trọng tâm BSC '
                    'để hệ thống có căn cứ định hướng các bộ lọc PESTEL, Nguồn lực và SWOT.'
                : 'Bạn đang chọn không áp dụng trọng tâm BSC cho mục tiêu này. '
                    'Hệ thống sẽ chuyển thẳng vào phân tích đa chiều.',
            style: const TextStyle(color: Colors.white70, fontSize: 13),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  Widget _buildAddScopeForm() {
    return Container(
      padding: const EdgeInsets.all(16),
      margin: const EdgeInsets.only(bottom: 16),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.primaryColor.withValues(alpha: 0.5)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'Thêm trọng tâm BSC',
                style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 15),
              ),
              IconButton(
                icon: const Icon(Icons.close, color: Colors.white54, size: 18),
                onPressed: () => setState(() => _isAdding = false),
              ),
            ],
          ),
          const SizedBox(height: 12),
          DropdownButtonFormField<BscPerspective>(
            key: const Key('dropdown_bsc_perspective'),
            initialValue: _selectedPerspective,
            dropdownColor: const Color(0xFF1E293B),
            decoration: const InputDecoration(
              labelText: 'Khía cạnh Balanced Scorecard (*)',
              border: OutlineInputBorder(),
            ),
            items: _availablePerspectives.map((p) {
              return DropdownMenuItem(
                value: p,
                child: Text(p.displayNameVi, style: const TextStyle(color: Colors.white)),
              );
            }).toList(),
            onChanged: (val) {
              if (val != null) setState(() => _selectedPerspective = val);
            },
          ),
          const SizedBox(height: 12),
          TextField(
            key: const Key('input_bsc_focus_desc'),
            controller: _focusDescController,
            style: const TextStyle(color: Colors.white),
            decoration: const InputDecoration(
              labelText: 'Mô tả trọng tâm trọng điểm (*)',
              hintText: 'Ví dụ: Tối ưu chi phí chuyển đổi khách hàng (CAC) và giữ chân khách hàng',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            key: const Key('input_bsc_weight'),
            controller: _weightController,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            style: const TextStyle(color: Colors.white),
            decoration: const InputDecoration(
              labelText: 'Trọng số ưu tiên (Weight: 0.1 - 5.0)',
              hintText: '1.0',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 16),
          Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              TextButton(
                onPressed: () => setState(() => _isAdding = false),
                child: const Text('Hủy'),
              ),
              const SizedBox(width: 8),
              ElevatedButton(
                key: const Key('btn_submit_bsc_scope'),
                onPressed: _isSaving ? null : _handleAddScope,
                child: _isSaving
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Text('Thêm trọng tâm'),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildScopesList() {
    return ListView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: _currentScopes.length,
      itemBuilder: (context, index) {
        final scope = _currentScopes[index];

        return Card(
          key: Key('card_bsc_scope_${scope.id}'),
          color: const Color(0xFF1E293B),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(10),
            side: const BorderSide(color: Colors.white10),
          ),
          margin: const EdgeInsets.only(bottom: 8),
          child: ListTile(
            leading: Chip(
              label: Text(
                scope.perspective.displayNameVi,
                style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.white),
              ),
              backgroundColor: _getPerspectiveColor(scope.perspective),
            ),
            title: Text(
              scope.focusDescription,
              style: const TextStyle(color: Colors.white, fontSize: 14),
            ),
            subtitle: Text(
              'Trọng số: ${scope.weight}',
              style: const TextStyle(color: Colors.white54, fontSize: 12),
            ),
            trailing: IconButton(
              icon: const Icon(Icons.delete_outline, color: Colors.white38, size: 20),
              onPressed: () => _handleRemoveScope(index),
            ),
          ),
        );
      },
    );
  }

  Color _getPerspectiveColor(BscPerspective p) {
    switch (p) {
      case BscPerspective.financial:
        return const Color(0xFF059669);
      case BscPerspective.customer:
        return const Color(0xFF2563EB);
      case BscPerspective.internalProcess:
        return const Color(0xFFD97706);
      case BscPerspective.learningAndGrowth:
        return const Color(0xFF7C3AED);
      case BscPerspective.unknown:
        return Colors.grey;
    }
  }
}
