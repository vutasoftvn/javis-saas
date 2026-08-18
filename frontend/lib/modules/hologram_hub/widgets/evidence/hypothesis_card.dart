import 'package:flutter/material.dart';
import '../../../../data/models/evidence_model.dart';

class HypothesisCard extends StatelessWidget {
  final HypothesisModel hypothesis;
  final VoidCallback? onAddEvidence;
  final VoidCallback? onTap;

  const HypothesisCard({
    super.key,
    required this.hypothesis,
    this.onAddEvidence,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final statusColor = hypothesis.status.color;
    final isCritical = hypothesis.importance >= 0.7 && hypothesis.uncertainty >= 0.6;

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B).withValues(alpha: 0.65),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: isCritical
              ? const Color(0xFFEF4444).withValues(alpha: 0.5)
              : const Color(0xFF334155),
          width: isCritical ? 1.4 : 1.0,
        ),
        boxShadow: isCritical
            ? [
                BoxShadow(
                  color: const Color(0xFFEF4444).withValues(alpha: 0.1),
                  blurRadius: 8,
                  offset: const Offset(0, 2),
                ),
              ]
            : null,
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(14),
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Category + Status + Risk Badge
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: Colors.white.withValues(alpha: 0.08),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        hypothesis.category.toUpperCase(),
                        style: const TextStyle(
                          color: Color(0xFF38BDF8),
                          fontSize: 10,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                    const SizedBox(width: 6),
                    if (isCritical) ...[
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: const Color(0xFFEF4444).withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(color: const Color(0xFFEF4444).withValues(alpha: 0.4)),
                        ),
                        child: const Text(
                          'RỦI RO SỐNG CÒN',
                          style: TextStyle(
                            color: Color(0xFFF87171),
                            fontSize: 9,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                      const SizedBox(width: 6),
                    ],
                    const Spacer(),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: statusColor.withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(color: statusColor.withValues(alpha: 0.4)),
                      ),
                      child: Text(
                        hypothesis.status.displayNameVi,
                        style: TextStyle(
                          color: statusColor,
                          fontSize: 10,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 10),

                // Statement
                Text(
                  hypothesis.statement,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                    height: 1.35,
                  ),
                ),
                const SizedBox(height: 12),

                // Meters: Evidence Score & Risk Score
                Row(
                  children: [
                    // Evidence Score Bar
                    Expanded(
                      flex: 3,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Text(
                                'Điểm Bằng Chứng',
                                style: TextStyle(
                                  color: Colors.white.withValues(alpha: 0.6),
                                  fontSize: 11,
                                ),
                              ),
                              Text(
                                '${(hypothesis.evidenceScore * 100).toInt()}%',
                                style: TextStyle(
                                  color: statusColor,
                                  fontWeight: FontWeight.bold,
                                  fontSize: 11,
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 4),
                          ClipRRect(
                            borderRadius: BorderRadius.circular(4),
                            child: LinearProgressIndicator(
                              value: hypothesis.evidenceScore,
                              minHeight: 5,
                              backgroundColor: Colors.white.withValues(alpha: 0.08),
                              valueColor: AlwaysStoppedAnimation<Color>(statusColor),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 14),

                    // Risk Score
                    Expanded(
                      flex: 2,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Text(
                                'Rủi Ro',
                                style: TextStyle(
                                  color: Colors.white.withValues(alpha: 0.6),
                                  fontSize: 11,
                                ),
                              ),
                              Text(
                                '${(hypothesis.riskScore * 100).toInt()}%',
                                style: TextStyle(
                                  color: isCritical ? const Color(0xFFEF4444) : const Color(0xFFF59E0B),
                                  fontWeight: FontWeight.bold,
                                  fontSize: 11,
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 4),
                          ClipRRect(
                            borderRadius: BorderRadius.circular(4),
                            child: LinearProgressIndicator(
                              value: hypothesis.riskScore,
                              minHeight: 5,
                              backgroundColor: Colors.white.withValues(alpha: 0.08),
                              valueColor: AlwaysStoppedAnimation<Color>(
                                isCritical ? const Color(0xFFEF4444) : const Color(0xFFF59E0B),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),

                // Next Action preview & Add Evidence Button
                const SizedBox(height: 10),
                const Divider(color: Color(0xFF334155), height: 1),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Icon(Icons.inventory_2_outlined, size: 13, color: Colors.white.withValues(alpha: 0.5)),
                    const SizedBox(width: 4),
                    Text(
                      '${hypothesis.evidenceRefs.length} bằng chứng',
                      style: TextStyle(
                        color: Colors.white.withValues(alpha: 0.6),
                        fontSize: 11,
                      ),
                    ),
                    const Spacer(),
                    if (onAddEvidence != null)
                      TextButton.icon(
                        style: TextButton.styleFrom(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                          minimumSize: Size.zero,
                          tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                        ),
                        icon: const Icon(Icons.add_link, size: 14, color: Color(0xFF38BDF8)),
                        label: const Text(
                          '+ Bằng Chứng',
                          style: TextStyle(color: Color(0xFF38BDF8), fontSize: 11, fontWeight: FontWeight.bold),
                        ),
                        onPressed: onAddEvidence,
                      ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
