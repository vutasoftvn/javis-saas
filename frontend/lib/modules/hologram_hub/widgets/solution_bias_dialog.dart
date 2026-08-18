import 'package:flutter/material.dart';

enum SolutionBiasAction {
  buildPrototype,
  validateProblem,
  proceedAnyway,
}

class SolutionBiasDialog extends StatelessWidget {
  final String projectName;
  final String solutionMaturity;
  final String problemEvidenceMaturity;
  final List<String> counterQuestions;
  final ValueChanged<SolutionBiasAction> onActionSelected;

  const SolutionBiasDialog({
    super.key,
    required this.projectName,
    this.solutionMaturity = 'VALIDATED / DETAILED',
    this.problemEvidenceMaturity = 'ASSUMPTION / LOW',
    required this.counterQuestions,
    required this.onActionSelected,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return Dialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      backgroundColor: isDark ? const Color(0xFF1E222D) : Colors.white,
      child: Container(
        padding: const EdgeInsets.all(24),
        constraints: const BoxConstraints(maxWidth: 520),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Title & Warning Icon
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: Colors.amber.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: const Icon(Icons.warning_amber_rounded, color: Colors.amber, size: 28),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'SOLUTION BIAS GUARDRAIL',
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.bold,
                          letterSpacing: 0.8,
                          color: Colors.amber,
                        ),
                      ),
                      Text(
                        'Cảnh Báo: Giải Pháp Đi Tìm Vấn Đề',
                        style: TextStyle(
                          fontSize: 17,
                          fontWeight: FontWeight.bold,
                          color: isDark ? Colors.white : Colors.black87,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),

            const SizedBox(height: 16),
            const Divider(),
            const SizedBox(height: 12),

            // Discrepancy details
            Text(
              'Dự án $projectName đang chuẩn bị phát triển Solution ($solutionMaturity), '
              'trong khi bằng chứng về Problem ($problemEvidenceMaturity) chưa đạt mức khuyến nghị.',
              style: TextStyle(
                fontSize: 13,
                height: 1.4,
                color: isDark ? Colors.grey.shade300 : Colors.black87,
              ),
            ),

            const SizedBox(height: 16),

            // Counter Questions Callout
            if (counterQuestions.isNotEmpty) ...[
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.blueAccent.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.blueAccent.withValues(alpha: 0.25)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Row(
                      children: [
                        Icon(Icons.psychology_outlined, size: 16, color: Colors.blueAccent),
                        SizedBox(width: 6),
                        Text(
                          'Câu hỏi phản biện từ AI:',
                          style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.blueAccent),
                        ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    Text(
                      '• ${counterQuestions.first}',
                      style: const TextStyle(fontSize: 12, fontStyle: FontStyle.italic),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 20),
            ],

            // Action Buttons
            Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                ElevatedButton.icon(
                  onPressed: () {
                    Navigator.of(context).pop();
                    onActionSelected(SolutionBiasAction.buildPrototype);
                  },
                  icon: const Icon(Icons.science_outlined, size: 18),
                  label: const Text('Build Prototype Tối Thiểu để Kiểm Chứng (Khuyến Nghị)'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.blueAccent,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 12),
                  ),
                ),
                const SizedBox(height: 8),
                OutlinedButton.icon(
                  onPressed: () {
                    Navigator.of(context).pop();
                    onActionSelected(SolutionBiasAction.validateProblem);
                  },
                  icon: const Icon(Icons.record_voice_over_outlined, size: 18),
                  label: const Text('Tạm Dừng: Phỏng Vấn Khách Hàng Thêm'),
                  style: OutlinedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 12),
                  ),
                ),
                const SizedBox(height: 8),
                TextButton.icon(
                  onPressed: () {
                    Navigator.of(context).pop();
                    onActionSelected(SolutionBiasAction.proceedAnyway);
                  },
                  icon: const Icon(Icons.lock_open_outlined, size: 16, color: Colors.grey),
                  label: const Text('Proceed Anyway (Quyền Quyết Định Của Founder)', style: TextStyle(color: Colors.grey, fontSize: 12)),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
