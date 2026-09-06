import 'package:flutter/material.dart';
import 'package:frontend/modules/strategy/models/strategy_workflow_models.dart';

class TowsPrioritizationStep extends StatefulWidget {
  final StrategicObjectiveModel selectedObjective;
  final List<BscFocusScopeModel> bscFocusScopes;
  final List<TowsOptionModel> towsOptions;
  final int selectionLimit;
  final Future<void> Function({
    required TowsOptionType optionType,
    required String title,
    String? description,
    List<String>? swotLinkIds,
  }) onCreateOption;
  final Future<void> Function(
    String optionId, {
    required double impactScore,
    required double difficultyScore,
    String? rationale,
  }) onEvaluateOption;
  final Future<void> Function(
    String optionId, {
    required String selectionRationale,
  }) onSelectOption;
  final Future<void> Function(
    String optionId, {
    required String rejectionReason,
  }) onRejectOption;
  final VoidCallback onBack;

  const TowsPrioritizationStep({
    super.key,
    required this.selectedObjective,
    required this.bscFocusScopes,
    required this.towsOptions,
    required this.selectionLimit,
    required this.onCreateOption,
    required this.onEvaluateOption,
    required this.onSelectOption,
    required this.onRejectOption,
    required this.onBack,
  });

  @override
  State<TowsPrioritizationStep> createState() => _TowsPrioritizationStepState();
}

class _TowsPrioritizationStepState extends State<TowsPrioritizationStep> {
  TowsOptionType _activeQuadrant = TowsOptionType.so;
  String? _serverError;
  bool _isProcessing = false;

  int get _selectedCount =>
      widget.towsOptions.where((o) => o.status == TowsOptionStatus.selected).length;

  bool get _isLimitReached => _selectedCount >= widget.selectionLimit;

  Future<void> _handleSelect(TowsOptionModel option) async {
    if (option.status == TowsOptionStatus.selected) return;
    if (_isLimitReached) {
      setState(() {
        _serverError = 'Đã đạt giới hạn chọn tối đa (${widget.selectionLimit} chiến lược). '
            'Vui lòng hủy chọn chiến lược khác trước khi chọn chiến lược mới.';
      });
      return;
    }

    final reasonCtrl = TextEditingController();
    final shouldProceed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF1E293B),
        title: Text('Xác nhận chọn chiến lược: ${option.title}',
            style: const TextStyle(color: Colors.white, fontSize: 16)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Chiến lược được chọn sẽ trở thành căn cứ lập Kế hoạch Hành động (Initiative) trong chu kỳ thực thi.',
              style: TextStyle(color: Colors.white70, fontSize: 13),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: reasonCtrl,
              style: const TextStyle(color: Colors.white),
              decoration: const InputDecoration(
                labelText: 'Lý do lựa chọn / Luận điểm quyết định (*)',
                hintText: 'Ví dụ: Tác động doanh thu ngắn hạn cao nhất...',
                border: OutlineInputBorder(),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Hủy')),
          ElevatedButton(
            onPressed: () {
              if (reasonCtrl.text.trim().isNotEmpty) {
                Navigator.pop(ctx, true);
              }
            },
            child: const Text('Xác nhận chọn'),
          ),
        ],
      ),
    );

    if (shouldProceed != true) return;

    setState(() {
      _isProcessing = true;
      _serverError = null;
    });
    try {
      await widget.onSelectOption(option.id, selectionRationale: reasonCtrl.text.trim());
    } catch (e) {
      setState(() {
        _serverError = 'Không thể chọn chiến lược: $e';
      });
    } finally {
      if (mounted) setState(() => _isProcessing = false);
    }
  }

  Future<void> _handleEvaluate(TowsOptionModel option) async {
    double impact = option.impactScore ?? 3.0;
    double difficulty = option.difficultyScore ?? 3.0;
    final notesCtrl = TextEditingController(text: option.evaluationNotes ?? '');

    final shouldSave = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDState) => AlertDialog(
          backgroundColor: const Color(0xFF1E293B),
          title: Text('Đánh giá chiến lược: ${option.title}',
              style: const TextStyle(color: Colors.white, fontSize: 16)),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text('Điểm tác động (Impact 1-5):', style: TextStyle(color: Colors.white70)),
                    Text('${impact.toInt()}', style: const TextStyle(color: Colors.lightGreenAccent, fontWeight: FontWeight.bold)),
                  ],
                ),
                Slider(
                  value: impact,
                  min: 1,
                  max: 5,
                  divisions: 4,
                  label: '${impact.toInt()}',
                  onChanged: (val) => setDState(() => impact = val),
                ),
                const SizedBox(height: 8),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text('Độ khó / Kháng trở (Difficulty 1-5):', style: TextStyle(color: Colors.white70)),
                    Text('${difficulty.toInt()}', style: const TextStyle(color: Colors.amberAccent, fontWeight: FontWeight.bold)),
                  ],
                ),
                Slider(
                  value: difficulty,
                  min: 1,
                  max: 5,
                  divisions: 4,
                  label: '${difficulty.toInt()}',
                  onChanged: (val) => setDState(() => difficulty = val),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: notesCtrl,
                  maxLines: 2,
                  style: const TextStyle(color: Colors.white),
                  decoration: const InputDecoration(
                    labelText: 'Ghi chú đánh giá / Luận chứng xếp hạng',
                    border: OutlineInputBorder(),
                  ),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Hủy')),
            ElevatedButton(
              onPressed: () => Navigator.pop(ctx, true),
              child: const Text('Lưu đánh giá'),
            ),
          ],
        ),
      ),
    );

    if (shouldSave != true) return;

    setState(() {
      _isProcessing = true;
      _serverError = null;
    });
    try {
      await widget.onEvaluateOption(
        option.id,
        impactScore: impact,
        difficultyScore: difficulty,
        rationale: notesCtrl.text.trim().isEmpty ? null : notesCtrl.text.trim(),
      );
    } catch (e) {
      setState(() {
        _serverError = 'Lỗi lưu đánh giá: $e';
      });
    } finally {
      if (mounted) setState(() => _isProcessing = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final filteredOptions = widget.towsOptions.where((o) => o.optionType == _activeQuadrant).toList();

    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildObjectiveAndBscContext(),
          const SizedBox(height: 16),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Bước 4: Ưu tiên & Quyết định lựa chọn TOWS',
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(
                            fontWeight: FontWeight.bold,
                            color: Colors.white,
                          ),
                    ),
                    const SizedBox(height: 4),
                    const Text(
                      'Đánh giá tác động (1-5), độ khó (1-5) và quyết định chiến lược vào kế hoạch hành động',
                      style: TextStyle(color: Colors.white70, fontSize: 13),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              _buildSelectionCounter(),
            ],
          ),
        if (_serverError != null) ...[
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.red.withValues(alpha: 0.2),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: Colors.redAccent),
            ),
            child: Row(
              children: [
                const Icon(Icons.error_outline, color: Colors.redAccent, size: 20),
                const SizedBox(width: 8),
                Expanded(child: Text(_serverError!, style: const TextStyle(color: Colors.redAccent))),
                IconButton(
                  icon: const Icon(Icons.close, color: Colors.white54, size: 16),
                  onPressed: () => setState(() => _serverError = null),
                ),
              ],
            ),
          ),
        ],
        const SizedBox(height: 16),
        _buildQuadrantSelector(),
        const SizedBox(height: 12),
        Row(
          mainAxisAlignment: MainAxisAlignment.end,
          children: [
            ElevatedButton.icon(
              key: const Key('btn_create_tows_option'),
              onPressed: _showCreateOptionDialog,
              icon: const Icon(Icons.add, size: 16),
              label: Text('Tạo chiến lược ${_activeQuadrant.displayNameVi}'),
            ),
          ],
        ),
        const SizedBox(height: 12),
        SizedBox(
          height: 380,
          child: filteredOptions.isEmpty
              ? _buildEmptyQuadrantState()
              : ListView.builder(
                  itemCount: filteredOptions.length,
                  itemBuilder: (context, index) {
                    final opt = filteredOptions[index];
                    return _buildOptionCard(opt);
                  },
                ),
        ),
        const SizedBox(height: 24),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            OutlinedButton.icon(
              key: const Key('btn_back_step'),
              onPressed: widget.onBack,
              icon: const Icon(Icons.arrow_back, size: 18),
              label: const Text('Quay lại: Phân tích chiến lược'),
            ),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              decoration: BoxDecoration(
                color: _selectedCount > 0 ? Colors.green.withValues(alpha: 0.2) : Colors.white10,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: _selectedCount > 0 ? Colors.green : Colors.white24),
              ),
              child: Row(
                children: [
                  Icon(
                    _selectedCount > 0 ? Icons.check_circle : Icons.info_outline,
                    size: 16,
                    color: _selectedCount > 0 ? Colors.lightGreenAccent : Colors.white60,
                  ),
                  const SizedBox(width: 6),
                  Text(
                    _selectedCount > 0
                        ? 'Đã chốt $_selectedCount chiến lược thực thi'
                        : 'Chưa có chiến lược nào được chọn',
                    style: TextStyle(
                      color: _selectedCount > 0 ? Colors.lightGreenAccent : Colors.white70,
                      fontWeight: FontWeight.bold,
                      fontSize: 13,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ],
    ),
  );
}

  Widget _buildSelectionCounter() {
    return Container(
      key: const Key('tows_selection_counter'),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
      decoration: BoxDecoration(
        color: _isLimitReached ? Colors.amber.withValues(alpha: 0.2) : const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: _isLimitReached ? Colors.amber : Colors.white24,
          width: 1.5,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            '$_selectedCount / ${widget.selectionLimit} chiến lược đã chọn',
            style: TextStyle(
              color: _isLimitReached ? Colors.amber : Colors.white,
              fontWeight: FontWeight.bold,
              fontSize: 13,
            ),
          ),
          if (_isLimitReached) ...[
            const SizedBox(width: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
              decoration: BoxDecoration(
                color: Colors.amber.withValues(alpha: 0.25),
                borderRadius: BorderRadius.circular(4),
              ),
              child: const Text(
                'Đã đạt giới hạn tối đa theo chính sách',
                style: TextStyle(color: Colors.amber, fontSize: 11, fontWeight: FontWeight.bold),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildObjectiveAndBscContext() {
    return Container(
      key: const Key('tows_context_header'),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: Colors.blueAccent.withValues(alpha: 0.4)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.flag, color: Colors.blueAccent, size: 18),
              const SizedBox(width: 8),
              Text(
                'Mục tiêu chiến lược: ${widget.selectedObjective.title}',
                style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.white, fontSize: 13),
              ),
            ],
          ),
          if (widget.bscFocusScopes.isNotEmpty) ...[
            const SizedBox(height: 6),
            Wrap(
              spacing: 6,
              runSpacing: 4,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                const Text('Trọng tâm BSC định hướng:', style: TextStyle(color: Colors.white60, fontSize: 12)),
                ...widget.bscFocusScopes.map((scope) {
                  return Chip(
                    label: Text(
                      '${scope.perspective.displayNameVi}: ${scope.focusDescription}',
                      style: const TextStyle(fontSize: 11, color: Colors.white),
                    ),
                    backgroundColor: const Color(0xFF334155),
                    padding: EdgeInsets.zero,
                    materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                  );
                }),
              ],
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildQuadrantSelector() {
    return Row(
      children: [
        _buildQuadrantTab(TowsOptionType.so, 'Chiến lược SO (Thế mạnh x Cơ hội)', Colors.green),
        const SizedBox(width: 8),
        _buildQuadrantTab(TowsOptionType.wo, 'Chiến lược WO (Khắc phục x Cơ hội)', Colors.blueAccent),
        const SizedBox(width: 8),
        _buildQuadrantTab(TowsOptionType.st, 'Chiến lược ST (Thế mạnh x Thách thức)', Colors.amber),
        const SizedBox(width: 8),
        _buildQuadrantTab(TowsOptionType.wt, 'Chiến lược WT (Phòng thủ x Thách thức)', Colors.redAccent),
      ],
    );
  }

  Widget _buildQuadrantTab(TowsOptionType type, String title, Color color) {
    final isSelected = _activeQuadrant == type;
    final count = widget.towsOptions.where((o) => o.optionType == type).length;

    return Expanded(
      child: InkWell(
        onTap: () => setState(() => _activeQuadrant = type),
        borderRadius: BorderRadius.circular(8),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 8),
          decoration: BoxDecoration(
            color: isSelected ? color.withValues(alpha: 0.2) : const Color(0xFF1E293B),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: isSelected ? color : Colors.white10, width: isSelected ? 2 : 1),
          ),
          child: Column(
            children: [
              Text(
                type.displayNameVi,
                style: TextStyle(
                  color: isSelected ? color : Colors.white70,
                  fontWeight: FontWeight.bold,
                  fontSize: 13,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                '$count phương án',
                style: TextStyle(color: isSelected ? Colors.white : Colors.white38, fontSize: 11),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildOptionCard(TowsOptionModel option) {
    final isSelected = option.status == TowsOptionStatus.selected;
    final isRejected = option.status == TowsOptionStatus.rejected;
    final hasScores = option.impactScore != null && option.difficultyScore != null;

    return Card(
      key: Key('card_tows_option_${option.id}'),
      color: isSelected ? const Color(0xFF064E3B) : const Color(0xFF1E293B),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(10),
        side: BorderSide(
          color: isSelected ? Colors.greenAccent : (isRejected ? Colors.redAccent : Colors.white10),
          width: isSelected ? 2 : 1,
        ),
      ),
      margin: const EdgeInsets.only(bottom: 10),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    option.title,
                    style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 15),
                  ),
                ),
                if (isSelected)
                  const Chip(
                    key: Key('chip_selected_status'),
                    label: Text('ĐÃ CHỌN', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 11)),
                    backgroundColor: Color(0xFF059669),
                  )
                else if (isRejected)
                  const Chip(
                    label: Text('ĐÃ TỪ CHỐI', style: TextStyle(color: Colors.white70, fontSize: 11)),
                    backgroundColor: Color(0xFF991B1B),
                  )
                else
                  Chip(
                    label: Text(option.status.name.toUpperCase(), style: const TextStyle(color: Colors.white70, fontSize: 11)),
                    backgroundColor: const Color(0xFF334155),
                  ),
              ],
            ),
            if (option.description != null && option.description!.isNotEmpty) ...[
              const SizedBox(height: 6),
              Text(option.description!, style: const TextStyle(color: Colors.white70, fontSize: 13)),
            ],
            const SizedBox(height: 10),
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: Colors.black26,
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Row(
                    children: [
                      const Text('Tác động: ', style: TextStyle(color: Colors.white60, fontSize: 12)),
                      Text(
                        option.impactScore != null ? '${option.impactScore!.toInt()}/5' : 'Chưa chấm',
                        style: const TextStyle(color: Colors.lightGreenAccent, fontWeight: FontWeight.bold, fontSize: 12),
                      ),
                      const SizedBox(width: 12),
                      const Text('Độ khó: ', style: TextStyle(color: Colors.white60, fontSize: 12)),
                      Text(
                        option.difficultyScore != null ? '${option.difficultyScore!.toInt()}/5' : 'Chưa chấm',
                        style: const TextStyle(color: Colors.amberAccent, fontWeight: FontWeight.bold, fontSize: 12),
                      ),
                      if (option.rankingScore != null) ...[
                        const SizedBox(width: 12),
                        const Text('Điểm ưu tiên: ', style: TextStyle(color: Colors.white60, fontSize: 12)),
                        Text(
                          option.rankingScore!.toStringAsFixed(1),
                          style: const TextStyle(color: Colors.cyanAccent, fontWeight: FontWeight.bold, fontSize: 12),
                        ),
                      ],
                    ],
                  ),
                ),
                const Spacer(),
                OutlinedButton.icon(
                  key: Key('btn_evaluate_${option.id}'),
                  onPressed: _isProcessing ? null : () => _handleEvaluate(option),
                  icon: const Icon(Icons.star_half, size: 16),
                  label: Text(hasScores ? 'Chấm lại' : 'Đánh giá điểm'),
                  style: OutlinedButton.styleFrom(visualDensity: VisualDensity.compact),
                ),
                const SizedBox(width: 8),
                if (!isSelected)
                  ElevatedButton.icon(
                    key: Key('btn_select_${option.id}'),
                    onPressed: (_isProcessing || _isLimitReached) ? null : () => _handleSelect(option),
                    icon: const Icon(Icons.check, size: 16),
                    label: const Text('Chọn chiến lược'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF059669),
                      foregroundColor: Colors.white,
                      visualDensity: VisualDensity.compact,
                    ),
                  ),
              ],
            ),
            if (option.evaluationNotes != null && option.evaluationNotes!.isNotEmpty) ...[
              const SizedBox(height: 6),
              Text(
                'Giải thích: ${option.evaluationNotes!}',
                style: const TextStyle(color: Colors.white54, fontSize: 12, fontStyle: FontStyle.italic),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyQuadrantState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.alt_route, size: 40, color: Colors.white24),
            const SizedBox(height: 8),
            Text('Chưa có phương án ${_activeQuadrant.displayNameVi}',
                style: const TextStyle(color: Colors.white70, fontWeight: FontWeight.bold)),
            const SizedBox(height: 4),
            const Text('Bấm "Tạo chiến lược" để ghép nối điểm mạnh/yếu với cơ hội/thách thức.',
                style: TextStyle(color: Colors.white38, fontSize: 12)),
          ],
        ),
      ),
    );
  }

  void _showCreateOptionDialog() {
    final titleCtrl = TextEditingController();
    final descCtrl = TextEditingController();

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF1E293B),
        title: Text('Tạo phương án chiến lược ${_activeQuadrant.displayNameVi}',
            style: const TextStyle(color: Colors.white)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: titleCtrl,
              style: const TextStyle(color: Colors.white),
              decoration: const InputDecoration(
                labelText: 'Tên chiến lược (*)',
                hintText: 'Ví dụ: Tận dụng chi phí vốn rẻ để xây dựng dây chuyền mới',
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: descCtrl,
              maxLines: 3,
              style: const TextStyle(color: Colors.white),
              decoration: const InputDecoration(
                labelText: 'Mô tả cơ chế ghép cặp & Đánh đổi (Trade-offs)',
              ),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Hủy')),
          ElevatedButton(
            onPressed: () {
              if (titleCtrl.text.trim().isNotEmpty) {
                widget.onCreateOption(
                  optionType: _activeQuadrant,
                  title: titleCtrl.text.trim(),
                  description: descCtrl.text.trim().isEmpty ? null : descCtrl.text.trim(),
                );
                Navigator.pop(ctx);
              }
            },
            child: const Text('Lưu chiến lược'),
          ),
        ],
      ),
    );
  }
}
