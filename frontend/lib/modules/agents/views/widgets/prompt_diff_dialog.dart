import 'package:flutter/material.dart';

class PromptDiffDialog extends StatelessWidget {
  final String promptKey;
  final Map<String, dynamic> diffData;
  final VoidCallback onRestoreDefault;

  const PromptDiffDialog({
    super.key,
    required this.promptKey,
    required this.diffData,
    required this.onRestoreDefault,
  });

  @override
  Widget build(BuildContext context) {
    final diffText = diffData['diff_text']?.toString() ?? 'No differences found.';
    final isModified = diffData['is_modified_from_default'] == true;
    final currentVersion = diffData['current_version'] ?? 1;

    final diffLines = diffText.split('\n');

    return Dialog(
      backgroundColor: const Color(0xFF0F172A),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Container(
        width: 820,
        height: 600,
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: Colors.indigoAccent.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: const Icon(Icons.difference_outlined, color: Colors.indigoAccent, size: 22),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'So sánh Prompt Diff: $promptKey',
                        style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: Colors.white),
                      ),
                      Text(
                        'Phiên bản hiện tại: v$currentVersion | ${isModified ? "Đã qua chỉnh sửa tùy biến" : "Giống 100% Factory Default"}',
                        style: TextStyle(
                          fontSize: 12,
                          color: isModified ? Colors.amber.shade400 : Colors.green.shade400,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                ),
                IconButton(
                  onPressed: () => Navigator.of(context).pop(),
                  icon: const Icon(Icons.close_rounded, color: Colors.grey),
                ),
              ],
            ),

            const SizedBox(height: 16),

            // Diff Legend
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
              decoration: BoxDecoration(
                color: const Color(0xFF1E293B),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: const Color(0xFF334155)),
              ),
              child: Row(
                children: [
                  _buildLegendItem(const Color(0xFF10B981), '+ Dòng thêm mới (Added)'),
                  const SizedBox(width: 20),
                  _buildLegendItem(const Color(0xFFEF4444), '- Dòng bị xóa/sửa (Removed)'),
                  const SizedBox(width: 20),
                  _buildLegendItem(Colors.grey, '  Dòng gốc không đổi (Unmodified)'),
                ],
              ),
            ),

            const SizedBox(height: 14),

            // Diff Content Viewer
            Expanded(
              child: Container(
                width: double.infinity,
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: const Color(0xFF020617),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: const Color(0xFF1E293B)),
                ),
                child: ListView.builder(
                  itemCount: diffLines.length,
                  itemBuilder: (ctx, i) {
                    final line = diffLines[i];
                    Color textColor = const Color(0xFF94A3B8);
                    Color bgColor = Colors.transparent;

                    if (line.startsWith('+') && !line.startsWith('+++')) {
                      textColor = const Color(0xFF34D399);
                      bgColor = const Color(0xFF10B981).withValues(alpha: 0.12);
                    } else if (line.startsWith('-') && !line.startsWith('---')) {
                      textColor = const Color(0xFFF87171);
                      bgColor = const Color(0xFFEF4444).withValues(alpha: 0.12);
                    } else if (line.startsWith('@@')) {
                      textColor = Colors.indigoAccent.shade100;
                      bgColor = Colors.indigoAccent.withValues(alpha: 0.15);
                    }

                    return Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      color: bgColor,
                      child: Text(
                        line,
                        style: TextStyle(
                          color: textColor,
                          fontFamily: 'monospace',
                          fontSize: 12.5,
                          height: 1.4,
                        ),
                      ),
                    );
                  },
                ),
              ),
            ),

            const SizedBox(height: 16),

            // Actions Footer
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                if (isModified)
                  OutlinedButton.icon(
                    onPressed: () {
                      Navigator.of(context).pop();
                      onRestoreDefault();
                    },
                    icon: const Icon(Icons.restore_page_rounded, color: Colors.amber, size: 18),
                    label: const Text('Khôi phục Factory Default', style: TextStyle(color: Colors.amber, fontWeight: FontWeight.w700)),
                    style: OutlinedButton.styleFrom(
                      side: const BorderSide(color: Colors.amber),
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                    ),
                  )
                else
                  const SizedBox.shrink(),
                ElevatedButton(
                  onPressed: () => Navigator.of(context).pop(),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF334155),
                    padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  ),
                  child: const Text('Đóng', style: TextStyle(color: Colors.white)),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildLegendItem(Color color, String label) {
    return Row(
      children: [
        Container(
          width: 10,
          height: 10,
          decoration: BoxDecoration(color: color, shape: BoxShape.circle),
        ),
        const SizedBox(width: 6),
        Text(label, style: const TextStyle(color: Colors.white70, fontSize: 11.5)),
      ],
    );
  }
}
