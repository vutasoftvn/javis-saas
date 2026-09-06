import 'package:flutter/material.dart';
import '../../../../data/models/strategy_lens_model.dart';

class TowsMatrixWidget extends StatefulWidget {
  final List<TowsOptionModel> towsOptions;
  final int selectionLimit;
  final Function(TowsType quadrant, String title, String description) onCreateOption;
  final Function(int optionId, String tacticTitle, int weekNumber, String leadIndicator)? onConvertToTactics;
  final Function(int optionId, double impactScore, double difficultyScore, String? rationale)? onEvaluateOption;
  final Function(int optionId, String reason)? onSelectOption;

  const TowsMatrixWidget({
    super.key,
    required this.towsOptions,
    this.selectionLimit = 1,
    required this.onCreateOption,
    this.onConvertToTactics,
    this.onEvaluateOption,
    this.onSelectOption,
  });

  @override
  State<TowsMatrixWidget> createState() => _TowsMatrixWidgetState();
}

class _TowsMatrixWidgetState extends State<TowsMatrixWidget> {
  int get _selectedCount => widget.towsOptions.where((o) => o.status == 'selected').length;
  bool get _isLimitReached => _selectedCount >= widget.selectionLimit;

  void _showAddTowsDialog(BuildContext context, TowsType initialQuadrant) {
    final titleCtrl = TextEditingController();
    final descCtrl = TextEditingController();
    TowsType selectedQuadrant = initialQuadrant;

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setState) => AlertDialog(
          backgroundColor: const Color(0xFF0F172A),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
            side: BorderSide(color: selectedQuadrant.color, width: 1.5),
          ),
          title: Row(
            children: [
              Icon(Icons.alt_route, color: selectedQuadrant.color, size: 20),
              const SizedBox(width: 8),
              const Text(
                'Tạo Chiến Lược TOWS',
                style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
              ),
            ],
          ),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                DropdownButtonFormField<TowsType>(
                  initialValue: selectedQuadrant,
                  dropdownColor: const Color(0xFF1E293B),
                  decoration: const InputDecoration(
                    labelText: 'Cặp ghép chiến lược TOWS',
                    labelStyle: TextStyle(color: Colors.white70),
                  ),
                  items: TowsType.values.map((t) {
                    return DropdownMenuItem(
                      value: t,
                      child: Text(t.labelVi, style: TextStyle(color: t.color, fontWeight: FontWeight.bold, fontSize: 12)),
                    );
                  }).toList(),
                  onChanged: (val) {
                    if (val != null) setState(() => selectedQuadrant = val);
                  },
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: titleCtrl,
                  style: const TextStyle(color: Colors.white, fontSize: 13),
                  decoration: const InputDecoration(
                    labelText: 'Tên chiến lược (*)',
                    labelStyle: TextStyle(color: Colors.white70),
                    hintText: 'Ví dụ: Ra mắt gói Starter AI giá thấp...',
                    hintStyle: TextStyle(color: Colors.white30, fontSize: 12),
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: descCtrl,
                  maxLines: 3,
                  style: const TextStyle(color: Colors.white, fontSize: 13),
                  decoration: const InputDecoration(
                    labelText: 'Mô tả cơ chế ghép cặp & Đánh đổi (Trade-offs)',
                    labelStyle: TextStyle(color: Colors.white70),
                  ),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(),
              child: const Text('Hủy', style: TextStyle(color: Colors.white60)),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: selectedQuadrant.color,
                foregroundColor: Colors.black,
              ),
              onPressed: () {
                if (titleCtrl.text.trim().isNotEmpty) {
                  widget.onCreateOption(
                    selectedQuadrant,
                    titleCtrl.text.trim(),
                    descCtrl.text.trim(),
                  );
                  Navigator.of(ctx).pop();
                }
              },
              child: const Text('Lưu Chiến Lược', style: TextStyle(fontWeight: FontWeight.bold)),
            ),
          ],
        ),
      ),
    );
  }

  void _showEvaluateDialog(BuildContext context, TowsOptionModel option) {
    double impact = 3.0;
    double difficulty = 3.0;
    final notesCtrl = TextEditingController();

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setState) => AlertDialog(
          backgroundColor: const Color(0xFF0F172A),
          title: Text('Đánh giá chiến lược: ${option.title}',
              style: const TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.bold)),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text('Điểm tác động (1-5):', style: TextStyle(color: Colors.white70)),
                  Text('${impact.toInt()}', style: const TextStyle(color: Colors.greenAccent, fontWeight: FontWeight.bold)),
                ],
              ),
              Slider(
                value: impact,
                min: 1,
                max: 5,
                divisions: 4,
                label: '${impact.toInt()}',
                onChanged: (val) => setState(() => impact = val),
              ),
              const SizedBox(height: 8),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text('Độ khó / rào cản (1-5):', style: TextStyle(color: Colors.white70)),
                  Text('${difficulty.toInt()}', style: const TextStyle(color: Colors.amberAccent, fontWeight: FontWeight.bold)),
                ],
              ),
              Slider(
                value: difficulty,
                min: 1,
                max: 5,
                divisions: 4,
                label: '${difficulty.toInt()}',
                onChanged: (val) => setState(() => difficulty = val),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: notesCtrl,
                style: const TextStyle(color: Colors.white, fontSize: 13),
                decoration: const InputDecoration(
                  labelText: 'Giải thích xếp hạng',
                  border: OutlineInputBorder(),
                ),
              ),
            ],
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Hủy')),
            ElevatedButton(
              onPressed: () {
                if (widget.onEvaluateOption != null) {
                  widget.onEvaluateOption!(option.id, impact, difficulty, notesCtrl.text.trim());
                }
                Navigator.pop(ctx);
              },
              child: const Text('Lưu đánh giá'),
            ),
          ],
        ),
      ),
    );
  }

  void _showSelectDialog(BuildContext context, TowsOptionModel option) {
    if (_isLimitReached) return;
    final reasonCtrl = TextEditingController();

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF0F172A),
        title: Text('Chọn chiến lược: ${option.title}',
            style: const TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.bold)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text(
              'Chiến lược được chọn sẽ trở thành căn cứ xây dựng Kế hoạch Hành động (Initiative).',
              style: TextStyle(color: Colors.white70, fontSize: 13),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: reasonCtrl,
              style: const TextStyle(color: Colors.white, fontSize: 13),
              decoration: const InputDecoration(
                labelText: 'Lý do lựa chọn (*)',
                border: OutlineInputBorder(),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Hủy')),
          ElevatedButton(
            onPressed: () {
              if (reasonCtrl.text.trim().isNotEmpty && widget.onSelectOption != null) {
                widget.onSelectOption!(option.id, reasonCtrl.text.trim());
                Navigator.pop(ctx);
              }
            },
            child: const Text('Xác nhận chọn'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // Header with selection counter
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: const Color(0xFF1E293B),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: Colors.white12),
          ),
          child: Row(
            children: [
              const Icon(Icons.alt_route, color: Colors.blueAccent, size: 20),
              const SizedBox(width: 8),
              const Expanded(
                child: Text(
                  'Ma trận TOWS: Ghép nối yếu tố bên trong và bên ngoài để ra quyết định chiến lược.',
                  style: TextStyle(color: Colors.white70, fontSize: 12),
                ),
              ),
              Container(
                key: const Key('tows_selection_counter'),
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: _isLimitReached ? Colors.amber.withValues(alpha: 0.2) : Colors.blue.withValues(alpha: 0.2),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: _isLimitReached ? Colors.amber : Colors.blueAccent),
                ),
                child: Text(
                  '$_selectedCount / ${widget.selectionLimit} chiến lược đã chọn',
                  style: TextStyle(
                    color: _isLimitReached ? Colors.amber : Colors.lightBlueAccent,
                    fontWeight: FontWeight.bold,
                    fontSize: 12,
                  ),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),

        // 4 Quadrants Grid
        Expanded(
          child: GridView.count(
            crossAxisCount: 2,
            crossAxisSpacing: 12,
            mainAxisSpacing: 12,
            childAspectRatio: 1.1,
            children: TowsType.values.map((quadrant) {
              final options = widget.towsOptions.where((o) => o.quadrant == quadrant).toList();

              return Container(
                key: Key('tows_quadrant_${quadrant.name}'),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFF1E293B).withValues(alpha: 0.6),
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: quadrant.color.withValues(alpha: 0.4), width: 1.2),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(Icons.alt_route, color: quadrant.color, size: 16),
                        const SizedBox(width: 6),
                        Expanded(
                          child: Text(
                            quadrant.labelVi,
                            style: TextStyle(color: quadrant.color, fontSize: 12, fontWeight: FontWeight.bold),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        IconButton(
                          tooltip: 'Thêm chiến lược ${quadrant.name.toUpperCase()}',
                          icon: Icon(Icons.add_circle_outline, color: quadrant.color, size: 18),
                          onPressed: () => _showAddTowsDialog(context, quadrant),
                          padding: EdgeInsets.zero,
                          constraints: const BoxConstraints(minWidth: 24, minHeight: 24),
                        ),
                      ],
                    ),
                    const Divider(color: Colors.white12, height: 10),
                    Expanded(
                      child: options.isEmpty
                          ? Center(
                              child: Text(
                                'Chưa có chiến lược',
                                style: TextStyle(color: Colors.white.withValues(alpha: 0.3), fontSize: 11),
                              ),
                            )
                          : ListView.separated(
                              itemCount: options.length,
                              separatorBuilder: (_, _) => const SizedBox(height: 8),
                              itemBuilder: (context, idx) {
                                final opt = options[idx];
                                final isSelected = opt.status == 'selected';

                                return Container(
                                  key: Key('tows_option_${opt.id}'),
                                  padding: const EdgeInsets.all(10),
                                  decoration: BoxDecoration(
                                    color: isSelected ? const Color(0xFF064E3B) : Colors.black.withValues(alpha: 0.25),
                                    borderRadius: BorderRadius.circular(8),
                                    border: Border.all(
                                      color: isSelected ? Colors.greenAccent : Colors.white10,
                                    ),
                                  ),
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Row(
                                        children: [
                                          Expanded(
                                            child: Text(
                                              opt.title,
                                              style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.bold),
                                            ),
                                          ),
                                          if (isSelected)
                                            const Chip(
                                              label: Text('ĐÃ CHỌN', style: TextStyle(fontSize: 9, color: Colors.white)),
                                              backgroundColor: Color(0xFF059669),
                                              padding: EdgeInsets.zero,
                                              materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                                            ),
                                        ],
                                      ),
                                      const SizedBox(height: 6),
                                      Row(
                                        children: [
                                          OutlinedButton(
                                            onPressed: () => _showEvaluateDialog(context, opt),
                                            style: OutlinedButton.styleFrom(
                                              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                              visualDensity: VisualDensity.compact,
                                            ),
                                            child: const Text('Chấm điểm (1-5)', style: TextStyle(fontSize: 10)),
                                          ),
                                          const Spacer(),
                                          if (!isSelected)
                                            ElevatedButton(
                                              onPressed: _isLimitReached ? null : () => _showSelectDialog(context, opt),
                                              style: ElevatedButton.styleFrom(
                                                backgroundColor: const Color(0xFF059669),
                                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                                                visualDensity: VisualDensity.compact,
                                              ),
                                              child: const Text('Chọn', style: TextStyle(fontSize: 10)),
                                            ),
                                        ],
                                      ),
                                    ],
                                  ),
                                );
                              },
                            ),
                    ),
                  ],
                ),
              );
            }).toList(),
          ),
        ),
      ],
    );
  }
}
