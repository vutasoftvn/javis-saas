import 'package:flutter/material.dart';
import '../../../../data/models/strategy_lens_model.dart';

class PestelRadarWidget extends StatelessWidget {
  final List<PestelSignalModel> signals;
  final Function(PestelDimension dimension, String title, String desc, String impact, String horizon) onCreateSignal;
  final Function(int signalId) onConvertToHypothesis;

  const PestelRadarWidget({
    super.key,
    required this.signals,
    required this.onCreateSignal,
    required this.onConvertToHypothesis,
  });

  void _showAddSignalDialog(BuildContext context, PestelDimension initialDimension) {
    final titleCtrl = TextEditingController();
    final descCtrl = TextEditingController();
    PestelDimension selectedDimension = initialDimension;
    String impact = 'high';
    String horizon = 'short_term';

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
              Icon(Icons.radar_outlined, color: Color(0xFF38BDF8), size: 20),
              SizedBox(width: 8),
              Text(
                'Bắt Tín Hiệu Vĩ Mô PESTEL',
                style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
              ),
            ],
          ),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                DropdownButtonFormField<PestelDimension>(
                  initialValue: selectedDimension,
                  dropdownColor: const Color(0xFF1E293B),
                  decoration: const InputDecoration(
                    labelText: 'Chiều vĩ mô',
                    labelStyle: TextStyle(color: Colors.white70),
                  ),
                  items: PestelDimension.values.map((d) {
                    return DropdownMenuItem(
                      value: d,
                      child: Row(
                        children: [
                          Icon(d.icon, color: d.color, size: 16),
                          const SizedBox(width: 8),
                          Text(d.labelVi, style: TextStyle(color: d.color, fontSize: 13)),
                        ],
                      ),
                    );
                  }).toList(),
                  onChanged: (val) {
                    if (val != null) setState(() => selectedDimension = val);
                  },
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: titleCtrl,
                  style: const TextStyle(color: Colors.white, fontSize: 13),
                  decoration: const InputDecoration(
                    labelText: 'Tiêu đề tín hiệu (*)',
                    labelStyle: TextStyle(color: Colors.white70),
                    hintText: 'Ví dụ: Lãi suất tăng, AI Small Models phát triển...',
                    hintStyle: TextStyle(color: Colors.white30, fontSize: 12),
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: descCtrl,
                  maxLines: 3,
                  style: const TextStyle(color: Colors.white, fontSize: 13),
                  decoration: const InputDecoration(
                    labelText: 'Mô tả & Bối cảnh diễn biến',
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
                backgroundColor: const Color(0xFF38BDF8),
                foregroundColor: Colors.black,
              ),
              onPressed: () {
                if (titleCtrl.text.trim().isNotEmpty) {
                  onCreateSignal(
                    selectedDimension,
                    titleCtrl.text.trim(),
                    descCtrl.text.trim(),
                    impact,
                    horizon,
                  );
                  Navigator.of(ctx).pop();
                }
              },
              child: const Text('Lưu Tín Hiệu', style: TextStyle(fontWeight: FontWeight.bold)),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Header info
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: const Color(0xFF38BDF8).withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: const Color(0xFF38BDF8).withValues(alpha: 0.3)),
          ),
          child: const Row(
            children: [
              Icon(Icons.radar, color: Color(0xFF38BDF8), size: 20),
              SizedBox(width: 10),
              Expanded(
                child: Text(
                  'Lăng kính PESTEL quét 6 chiều vĩ mô để phát hiện cơ hội và rủi ro. Bạn có thể 1-click chuyển đổi tín hiệu thành Giả định cần kiểm chứng (Hypothesis).',
                  style: TextStyle(color: Colors.white70, fontSize: 12, height: 1.4),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),

        // 6 Dimensions Grid
        Expanded(
          child: GridView.builder(
            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: 2,
              childAspectRatio: 1.15,
              crossAxisSpacing: 12,
              mainAxisSpacing: 12,
            ),
            itemCount: PestelDimension.values.length,
            itemBuilder: (context, idx) {
              final dim = PestelDimension.values[idx];
              final dimSignals = signals.where((s) => s.dimension == dim).toList();

              return Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFF1E293B).withValues(alpha: 0.6),
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: dim.color.withValues(alpha: 0.4), width: 1.2),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Dimension Title & Add Button
                    Row(
                      children: [
                        Icon(dim.icon, color: dim.color, size: 16),
                        const SizedBox(width: 6),
                        Expanded(
                          child: Text(
                            dim.labelVi,
                            style: TextStyle(color: dim.color, fontSize: 12, fontWeight: FontWeight.bold),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        IconButton(
                          tooltip: 'Thêm tín hiệu ${dim.name}',
                          icon: Icon(Icons.add_circle_outline, color: dim.color, size: 18),
                          onPressed: () => _showAddSignalDialog(context, dim),
                          padding: EdgeInsets.zero,
                          constraints: const BoxConstraints(minWidth: 24, minHeight: 24),
                        ),
                      ],
                    ),
                    const Divider(color: Colors.white12, height: 12),

                    // Signals List
                    Expanded(
                      child: dimSignals.isEmpty
                          ? Center(
                              child: Text(
                                'Chưa có tín hiệu',
                                style: TextStyle(color: Colors.white.withValues(alpha: 0.3), fontSize: 11),
                              ),
                            )
                          : ListView.separated(
                              itemCount: dimSignals.length,
                              separatorBuilder: (_, _) => const SizedBox(height: 6),
                              itemBuilder: (context, sIdx) {
                                final sig = dimSignals[sIdx];
                                final hasHypo = sig.resultingHypothesisId != null;

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
                                        sig.signalTitle,
                                        style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w600),
                                        maxLines: 2,
                                        overflow: TextOverflow.ellipsis,
                                      ),
                                      if (sig.description.isNotEmpty) ...[
                                        const SizedBox(height: 2),
                                        Text(
                                          sig.description,
                                          style: const TextStyle(color: Colors.white60, fontSize: 10),
                                          maxLines: 2,
                                          overflow: TextOverflow.ellipsis,
                                        ),
                                      ],
                                      const SizedBox(height: 6),
                                      Row(
                                        children: [
                                          Container(
                                            padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
                                            decoration: BoxDecoration(
                                              color: dim.color.withValues(alpha: 0.15),
                                              borderRadius: BorderRadius.circular(4),
                                            ),
                                            child: Text(
                                              sig.impactLevel.toUpperCase(),
                                              style: TextStyle(color: dim.color, fontSize: 9, fontWeight: FontWeight.bold),
                                            ),
                                          ),
                                          const Spacer(),
                                          if (hasHypo)
                                            Container(
                                              padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
                                              decoration: BoxDecoration(
                                                color: const Color(0xFF10B981).withValues(alpha: 0.15),
                                                borderRadius: BorderRadius.circular(4),
                                              ),
                                              child: const Row(
                                                mainAxisSize: MainAxisSize.min,
                                                children: [
                                                  Icon(Icons.check_circle_outline, color: Color(0xFF10B981), size: 10),
                                                  SizedBox(width: 3),
                                                  Text('Đã Tạo Giả Định', style: TextStyle(color: Color(0xFF10B981), fontSize: 9, fontWeight: FontWeight.bold)),
                                                ],
                                              ),
                                            )
                                          else
                                            InkWell(
                                              onTap: () => onConvertToHypothesis(sig.id),
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
                                                    Icon(Icons.bolt, color: Color(0xFF38BDF8), size: 10),
                                                    SizedBox(width: 2),
                                                    Text('Sinh Giả Định', style: TextStyle(color: Color(0xFF38BDF8), fontSize: 9, fontWeight: FontWeight.bold)),
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
            },
          ),
        ),
      ],
    );
  }
}
