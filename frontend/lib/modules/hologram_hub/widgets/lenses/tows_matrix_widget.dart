import 'package:flutter/material.dart';
import '../../../../data/models/strategy_lens_model.dart';

class TowsMatrixWidget extends StatelessWidget {
  final List<TowsOptionModel> towsOptions;
  final Function(TowsType quadrant, String title, String description) onCreateOption;
  final Function(int optionId, String tacticTitle, int weekNumber, String leadIndicator) onConvertToTactics;

  const TowsMatrixWidget({
    super.key,
    required this.towsOptions,
    required this.onCreateOption,
    required this.onConvertToTactics,
  });

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
                  onCreateOption(
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

  void _showTacticConvertDialog(BuildContext context, TowsOptionModel option) {
    final tacticCtrl = TextEditingController(text: 'Thực thi thử nghiệm cho ${option.title}');
    final leadCtrl = TextEditingController(text: 'Tiếp cận 30 khách hàng mục tiêu & đo lường conversion');
    int selectedWeek = 1;

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setState) => AlertDialog(
          backgroundColor: const Color(0xFF0F172A),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
            side: const BorderSide(color: Color(0xFF38BDF8), width: 1.5),
          ),
          title: const Row(
            children: [
              Icon(Icons.calendar_month, color: Color(0xFF38BDF8), size: 20),
              SizedBox(width: 8),
              Text(
                'Chuyển Thành Kế Hoạch 12 Tuần',
                style: TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.bold),
              ),
            ],
          ),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Chiến lược nguồn: [${option.quadrant.name.toUpperCase()}] ${option.title}',
                  style: const TextStyle(color: Color(0xFF38BDF8), fontSize: 12, fontStyle: FontStyle.italic),
                ),
                const SizedBox(height: 14),
                DropdownButtonFormField<int>(
                  initialValue: selectedWeek,
                  dropdownColor: const Color(0xFF1E293B),
                  decoration: const InputDecoration(
                    labelText: 'Tuần thực thi (12-Week Year)',
                    labelStyle: TextStyle(color: Colors.white70),
                  ),
                  items: List.generate(12, (i) => i + 1).map((w) {
                    return DropdownMenuItem(
                      value: w,
                      child: Text('Tuần $w / 12', style: const TextStyle(color: Colors.white, fontSize: 13)),
                    );
                  }).toList(),
                  onChanged: (val) {
                    if (val != null) setState(() => selectedWeek = val);
                  },
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: tacticCtrl,
                  style: const TextStyle(color: Colors.white, fontSize: 13),
                  decoration: const InputDecoration(
                    labelText: 'Tên hành động chiến thuật (Tactic) (*)',
                    labelStyle: TextStyle(color: Colors.white70),
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: leadCtrl,
                  maxLines: 2,
                  style: const TextStyle(color: Colors.white, fontSize: 13),
                  decoration: const InputDecoration(
                    labelText: 'Chỉ số dẫn dắt (Lead Indicator) (*)',
                    labelStyle: TextStyle(color: Colors.white70),
                    hintText: 'Hành động cụ thể bạn kiểm soát được hàng ngày...',
                    hintStyle: TextStyle(color: Colors.white30, fontSize: 12),
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
                backgroundColor: const Color(0xFF38BDF8),
                foregroundColor: Colors.black,
              ),
              onPressed: () {
                if (tacticCtrl.text.trim().isNotEmpty) {
                  onConvertToTactics(
                    option.id,
                    tacticCtrl.text.trim(),
                    selectedWeek,
                    leadCtrl.text.trim(),
                  );
                  Navigator.of(ctx).pop();
                }
              },
              child: const Text('Tạo Tactic 12WY', style: TextStyle(fontWeight: FontWeight.bold)),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // Header
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: const Color(0xFF38BDF8).withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: const Color(0xFF38BDF8).withValues(alpha: 0.3)),
          ),
          child: const Row(
            children: [
              Icon(Icons.alt_route, color: Color(0xFF38BDF8), size: 20),
              SizedBox(width: 10),
              Expanded(
                child: Text(
                  'Ma trận TOWS ghép cặp SO, WO, ST, WT để sinh chiến lược đột phá và tự động chuyển hóa thành Kế hoạch hành động 12 Tuần (12WY Tactics & Lead Indicators).',
                  style: TextStyle(color: Colors.white70, fontSize: 12, height: 1.4),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),

        // 2x2 TOWS Grid
        Expanded(
          child: GridView.count(
            crossAxisCount: 2,
            crossAxisSpacing: 12,
            mainAxisSpacing: 12,
            childAspectRatio: 1.18,
            children: TowsType.values.map((type) {
              final options = towsOptions.where((o) => o.quadrant == type).toList();

              return Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFF1E293B).withValues(alpha: 0.6),
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: type.color.withValues(alpha: 0.4), width: 1.2),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Quadrant title & add
                    Row(
                      children: [
                        Container(
                          width: 8,
                          height: 8,
                          decoration: BoxDecoration(color: type.color, shape: BoxShape.circle),
                        ),
                        const SizedBox(width: 6),
                        Expanded(
                          child: Text(
                            type.labelVi,
                            style: TextStyle(color: type.color, fontSize: 12, fontWeight: FontWeight.bold),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        IconButton(
                          tooltip: 'Thêm chiến lược ${type.name.toUpperCase()}',
                          icon: Icon(Icons.add_circle_outline, color: type.color, size: 18),
                          onPressed: () => _showAddTowsDialog(context, type),
                          padding: EdgeInsets.zero,
                          constraints: const BoxConstraints(minWidth: 24, minHeight: 24),
                        ),
                      ],
                    ),
                    const Divider(color: Colors.white12, height: 10),

                    // Options list
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
                              separatorBuilder: (_, _) => const SizedBox(height: 6),
                              itemBuilder: (context, idx) {
                                final opt = options[idx];
                                final hasTactics = opt.tactics12wy.isNotEmpty;

                                return Container(
                                  padding: const EdgeInsets.all(8),
                                  decoration: BoxDecoration(
                                    color: Colors.black.withValues(alpha: 0.25),
                                    borderRadius: BorderRadius.circular(8),
                                  ),
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        opt.title,
                                        style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.bold),
                                        maxLines: 2,
                                        overflow: TextOverflow.ellipsis,
                                      ),
                                      if (opt.tradeoffs != null && opt.tradeoffs!.isNotEmpty) ...[
                                        const SizedBox(height: 2),
                                        Text(
                                          opt.tradeoffs!,
                                          style: const TextStyle(color: Colors.white60, fontSize: 10),
                                          maxLines: 2,
                                          overflow: TextOverflow.ellipsis,
                                        ),
                                      ],
                                      const SizedBox(height: 6),
                                      Row(
                                        children: [
                                          if (hasTactics)
                                            Container(
                                              padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
                                              decoration: BoxDecoration(
                                                color: const Color(0xFF10B981).withValues(alpha: 0.15),
                                                borderRadius: BorderRadius.circular(4),
                                              ),
                                              child: Text(
                                                '${opt.tactics12wy.length} Tactic 12WY',
                                                style: const TextStyle(color: Color(0xFF10B981), fontSize: 9, fontWeight: FontWeight.bold),
                                              ),
                                            ),
                                          const Spacer(),
                                          InkWell(
                                            onTap: () => _showTacticConvertDialog(context, opt),
                                            borderRadius: BorderRadius.circular(4),
                                            child: Container(
                                              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                              decoration: BoxDecoration(
                                                color: const Color(0xFF38BDF8).withValues(alpha: 0.15),
                                                borderRadius: BorderRadius.circular(4),
                                                border: Border.all(color: const Color(0xFF38BDF8).withValues(alpha: 0.3)),
                                              ),
                                              child: const Row(
                                                mainAxisSize: MainAxisSize.min,
                                                children: [
                                                  Icon(Icons.calendar_today, color: Color(0xFF38BDF8), size: 10),
                                                  SizedBox(width: 3),
                                                  Text('+ Tactic 12WY', style: TextStyle(color: Color(0xFF38BDF8), fontSize: 9, fontWeight: FontWeight.bold)),
                                                ],
                                              ),
                                            ),
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
