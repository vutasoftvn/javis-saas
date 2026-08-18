import 'package:flutter/material.dart';
import '../../../data/models/stage_model.dart';

class StagePolicyDialog extends StatelessWidget {
  final StagePolicyModel policy;

  const StagePolicyDialog({
    super.key,
    required this.policy,
  });

  static Future<void> show(BuildContext context, StagePolicyModel policy) {
    return showDialog(
      context: context,
      barrierDismissible: true,
      builder: (ctx) => StagePolicyDialog(policy: policy),
    );
  }

  @override
  Widget build(BuildContext context) {
    final stage = policy.stage;
    final primaryColor = stage.primaryColor;

    return Dialog(
      backgroundColor: const Color(0xFF0F172A),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(20),
        side: BorderSide(
          color: primaryColor.withValues(alpha: 0.4),
          width: 1.5,
        ),
      ),
      insetPadding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
      child: Container(
        constraints: const BoxConstraints(maxWidth: 680, maxHeight: 720),
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            // Header
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: primaryColor.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: primaryColor.withValues(alpha: 0.5)),
                  ),
                  child: Icon(stage.icon, color: primaryColor, size: 26),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Text(
                            policy.code,
                            style: TextStyle(
                              color: primaryColor,
                              fontWeight: FontWeight.bold,
                              fontSize: 16,
                            ),
                          ),
                          const SizedBox(width: 8),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                            decoration: BoxDecoration(
                              color: Colors.white.withValues(alpha: 0.08),
                              borderRadius: BorderRadius.circular(6),
                            ),
                            child: Text(
                              'Nhịp Review: ${policy.reviewCadence.toUpperCase()}',
                              style: TextStyle(
                                color: Colors.white.withValues(alpha: 0.7),
                                fontSize: 11,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Text(
                        policy.stageNameVi,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.close, color: Colors.white70),
                  onPressed: () => Navigator.of(context).pop(),
                ),
              ],
            ),
            const SizedBox(height: 16),
            const Divider(color: Color(0xFF334155)),
            const SizedBox(height: 12),

            // Scrollable Body
            Flexible(
              child: SingleChildScrollView(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Mục tiêu cốt lõi
                    _buildSectionHeader(Icons.flag_outlined, 'MỤC TIÊU CỐT LÕI (PRIMARY GOAL)', primaryColor),
                    const SizedBox(height: 6),
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: primaryColor.withValues(alpha: 0.08),
                        borderRadius: BorderRadius.circular(10),
                        border: Border.all(color: primaryColor.withValues(alpha: 0.2)),
                      ),
                      child: Text(
                        policy.primaryGoal,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 14,
                          height: 1.4,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ),
                    const SizedBox(height: 16),

                    // Câu hỏi trọng tâm
                    _buildSectionHeader(Icons.help_outline, 'CÂU HỎI SỐNG CÒN CẦN TRẢ LỜI', primaryColor),
                    const SizedBox(height: 6),
                    ...policy.primaryQuestions.map((q) => Padding(
                          padding: const EdgeInsets.only(bottom: 6),
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text('• ', style: TextStyle(color: primaryColor, fontSize: 14, fontWeight: FontWeight.bold)),
                              Expanded(
                                child: Text(
                                  q,
                                  style: const TextStyle(color: Colors.white70, fontSize: 13, height: 1.35),
                                ),
                              ),
                            ],
                          ),
                        )),
                    const SizedBox(height: 16),

                    // Khuyến nghị vs Chưa nên dùng
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // Recommended
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              _buildSectionHeader(Icons.check_circle_outline, 'PHƯƠNG PHÁP ƯU TIÊN', const Color(0xFF10B981)),
                              const SizedBox(height: 6),
                              Wrap(
                                spacing: 6,
                                runSpacing: 6,
                                children: policy.recommendedMethods.map((m) => Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                      decoration: BoxDecoration(
                                        color: const Color(0xFF10B981).withValues(alpha: 0.12),
                                        borderRadius: BorderRadius.circular(6),
                                        border: Border.all(color: const Color(0xFF10B981).withValues(alpha: 0.35)),
                                      ),
                                      child: Text(
                                        m.replaceAll('_', ' ').toUpperCase(),
                                        style: const TextStyle(color: Color(0xFF34D399), fontSize: 11, fontWeight: FontWeight.w600),
                                      ),
                                    )).toList(),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(width: 14),
                        // Deemphasized
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              _buildSectionHeader(Icons.block, 'TẠM TẮT / CHƯA CẦN', const Color(0xFF94A3B8)),
                              const SizedBox(height: 6),
                              policy.deemphasizedTools.isEmpty
                                  ? Text('Không có (Bật toàn bộ)', style: TextStyle(color: Colors.white.withValues(alpha: 0.4), fontSize: 12))
                                  : Wrap(
                                      spacing: 6,
                                      runSpacing: 6,
                                      children: policy.deemphasizedTools.map((d) => Container(
                                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                            decoration: BoxDecoration(
                                              color: Colors.white.withValues(alpha: 0.04),
                                              borderRadius: BorderRadius.circular(6),
                                              border: Border.all(color: Colors.white.withValues(alpha: 0.15)),
                                            ),
                                            child: Text(
                                              d.replaceAll('_', ' ').toUpperCase(),
                                              style: TextStyle(
                                                color: Colors.white.withValues(alpha: 0.5),
                                                fontSize: 11,
                                                decoration: TextDecoration.lineThrough,
                                                decorationColor: Colors.redAccent.withValues(alpha: 0.6),
                                              ),
                                            ),
                                          )).toList(),
                                    ),
                            ],
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),

                    // Metrics & Agents
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              _buildSectionHeader(Icons.insights, 'CHỈ SỐ THEO DÕI (METRICS)', primaryColor),
                              const SizedBox(height: 6),
                              ...policy.primaryMetrics.map((met) => Padding(
                                    padding: const EdgeInsets.only(bottom: 4),
                                    child: Text('• ${met.replaceAll('_', ' ')}', style: const TextStyle(color: Colors.white70, fontSize: 12)),
                                  )),
                            ],
                          ),
                        ),
                        const SizedBox(width: 14),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              _buildSectionHeader(Icons.smart_toy_outlined, 'AI AGENTS ƯU TIÊN', primaryColor),
                              const SizedBox(height: 6),
                              Wrap(
                                spacing: 6,
                                runSpacing: 6,
                                children: policy.priorityAgents.map((ag) => Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                      decoration: BoxDecoration(
                                        color: primaryColor.withValues(alpha: 0.12),
                                        borderRadius: BorderRadius.circular(6),
                                        border: Border.all(color: primaryColor.withValues(alpha: 0.3)),
                                      ),
                                      child: Text(
                                        ag,
                                        style: TextStyle(color: primaryColor, fontSize: 11, fontWeight: FontWeight.bold),
                                      ),
                                    )).toList(),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            const Divider(color: Color(0xFF334155)),
            const SizedBox(height: 8),

            // Footer
            Align(
              alignment: Alignment.centerRight,
              child: ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: primaryColor,
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                  padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                ),
                onPressed: () => Navigator.of(context).pop(),
                child: const Text('Đã Hiểu', style: TextStyle(fontWeight: FontWeight.bold)),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSectionHeader(IconData icon, String title, Color color) {
    return Row(
      children: [
        Icon(icon, size: 14, color: color),
        const SizedBox(width: 6),
        Text(
          title,
          style: TextStyle(
            color: color,
            fontSize: 11,
            fontWeight: FontWeight.bold,
            letterSpacing: 0.8,
          ),
        ),
      ],
    );
  }
}
