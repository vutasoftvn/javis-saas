import 'package:flutter/material.dart';
import '../../../../data/models/evidence_model.dart';
import 'hypothesis_card.dart';

class AssumptionRiskMatrixWidget extends StatelessWidget {
  final AssumptionMatrixModel matrix;
  final Function(HypothesisModel)? onSelectHypothesis;
  final Function(HypothesisModel)? onAddEvidence;

  const AssumptionRiskMatrixWidget({
    super.key,
    required this.matrix,
    this.onSelectHypothesis,
    this.onAddEvidence,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Header info
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'MA TRẬN RỦI RO GIẢ ĐỊNH (2x2)',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 14,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 0.5,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  'Tương quan giữa Tầm Quan Trọng (Importance) và Độ Bất Định (Uncertainty)',
                  style: TextStyle(
                    color: Colors.white.withValues(alpha: 0.5),
                    fontSize: 11,
                  ),
                ),
              ],
            ),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(
                color: const Color(0xFFEF4444).withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: const Color(0xFFEF4444).withValues(alpha: 0.4)),
              ),
              child: Text(
                '${matrix.criticalCount} Giả Định Cần Test Ngay',
                style: const TextStyle(
                  color: Color(0xFFF87171),
                  fontSize: 11,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 14),

        // 4 Quadrants Grid
        Expanded(
          child: LayoutBuilder(
            builder: (context, constraints) {
              final isWide = constraints.maxWidth >= 600;
              if (!isWide) {
                return ListView(
                  children: [
                    _buildQuadrantBox(
                      title: '1. TEST TRƯỚC TIÊN (CRITICAL TEST FIRST)',
                      subtitle: 'Quan trọng cao + Bất định cao -> Cần làm thực nghiệm ngay',
                      color: const Color(0xFFEF4444),
                      items: matrix.criticalTestFirst,
                    ),
                    const SizedBox(height: 12),
                    _buildQuadrantBox(
                      title: '2. THEO DÕI (MONITOR)',
                      subtitle: 'Quan trọng thấp + Bất định cao',
                      color: const Color(0xFFF59E0B),
                      items: matrix.monitor,
                    ),
                    const SizedBox(height: 12),
                    _buildQuadrantBox(
                      title: '3. ĐÃ RÕ / RỦI RO THẤP (IMPORTANT LOW RISK)',
                      subtitle: 'Quan trọng cao + Bất định thấp -> Giữ nguyên thực thi',
                      color: const Color(0xFF10B981),
                      items: matrix.importantLowRisk,
                    ),
                    const SizedBox(height: 12),
                    _buildQuadrantBox(
                      title: '4. ƯU TIÊN THẤP (LOW PRIORITY)',
                      subtitle: 'Quan trọng thấp + Bất định thấp',
                      color: const Color(0xFF64748B),
                      items: matrix.lowPriority,
                    ),
                  ],
                );
              }

              return Row(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // Left Column: Monitor (Top) & Low Priority (Bottom)
                  Expanded(
                    child: Column(
                      children: [
                        Expanded(
                          child: _buildQuadrantBox(
                            title: 'THEO DÕI (MONITOR)',
                            subtitle: 'Quan trọng thấp • Bất định cao',
                            color: const Color(0xFFF59E0B),
                            items: matrix.monitor,
                          ),
                        ),
                        const SizedBox(height: 12),
                        Expanded(
                          child: _buildQuadrantBox(
                            title: 'ƯU TIÊN THẤP (LOW PRIORITY)',
                            subtitle: 'Quan trọng thấp • Bất định thấp',
                            color: const Color(0xFF64748B),
                            items: matrix.lowPriority,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 12),

                  // Right Column: Critical Test First (Top) & Important Low Risk (Bottom)
                  Expanded(
                    child: Column(
                      children: [
                        Expanded(
                          child: _buildQuadrantBox(
                            title: 'TEST TRƯỚC TIÊN (CRITICAL)',
                            subtitle: 'Quan trọng cao • Bất định cao',
                            color: const Color(0xFFEF4444),
                            items: matrix.criticalTestFirst,
                          ),
                        ),
                        const SizedBox(height: 12),
                        Expanded(
                          child: _buildQuadrantBox(
                            title: 'ĐÃ RÕ RÀNG (LOW RISK)',
                            subtitle: 'Quan trọng cao • Bất định thấp',
                            color: const Color(0xFF10B981),
                            items: matrix.importantLowRisk,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              );
            },
          ),
        ),
      ],
    );
  }

  Widget _buildQuadrantBox({
    required String title,
    required String subtitle,
    required Color color,
    required List<HypothesisModel> items,
  }) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withValues(alpha: 0.35), width: 1.2),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 8,
                height: 8,
                decoration: BoxDecoration(color: color, shape: BoxShape.circle),
              ),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  title,
                  style: TextStyle(
                    color: color,
                    fontWeight: FontWeight.bold,
                    fontSize: 11,
                    letterSpacing: 0.5,
                  ),
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  '${items.length}',
                  style: TextStyle(color: color, fontWeight: FontWeight.bold, fontSize: 10),
                ),
              ),
            ],
          ),
          const SizedBox(height: 2),
          Text(
            subtitle,
            style: TextStyle(color: Colors.white.withValues(alpha: 0.45), fontSize: 10),
          ),
          const SizedBox(height: 8),
          const Divider(color: Color(0xFF334155), height: 1),
          const SizedBox(height: 8),
          Expanded(
            child: items.isEmpty
                ? Center(
                    child: Text(
                      'Không có giả định nào',
                      style: TextStyle(color: Colors.white.withValues(alpha: 0.3), fontSize: 11),
                    ),
                  )
                : ListView.builder(
                    itemCount: items.length,
                    itemBuilder: (ctx, i) {
                      final h = items[i];
                      return HypothesisCard(
                        hypothesis: h,
                        onTap: onSelectHypothesis != null ? () => onSelectHypothesis!(h) : null,
                        onAddEvidence: onAddEvidence != null ? () => onAddEvidence!(h) : null,
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }
}
