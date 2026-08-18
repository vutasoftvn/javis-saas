import 'package:flutter/material.dart';
import '../../../data/models/validation_models.dart';

class ClaimConfirmationCard extends StatelessWidget {
  final ClusterSummaryModel summary;
  final List<StructuredClaimModel> claims;
  final VoidCallback onConfirm;
  final Function(StructuredClaimModel claim, String newValue) onEdit;
  final VoidCallback onContinue;
  final VoidCallback onMarkUncertain;

  const ClaimConfirmationCard({
    super.key,
    required this.summary,
    required this.claims,
    required this.onConfirm,
    required this.onEdit,
    required this.onContinue,
    required this.onMarkUncertain,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 12.0, horizontal: 8.0),
      padding: const EdgeInsets.all(16.0),
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF1E222D) : const Color(0xFFF4F6F9),
        borderRadius: BorderRadius.circular(12.0),
        border: Border.all(
          color: isDark ? const Color(0xFF2A3142) : const Color(0xFFE2E8F0),
          width: 1.5,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.05),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  const Icon(Icons.fact_check_rounded, color: Colors.blueAccent, size: 20),
                  const SizedBox(width: 8),
                  Text(
                    summary.title,
                    style: theme.textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                      letterSpacing: 0.5,
                    ),
                  ),
                ],
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: Colors.amber.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: Colors.amber.withValues(alpha: 0.4)),
                ),
                child: Text(
                  summary.status,
                  style: const TextStyle(
                    color: Colors.amber,
                    fontSize: 11,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          const Divider(height: 1),
          const SizedBox(height: 12),

          // Extracted Claims List
          ...summary.summaryItems.map(
            (item) => Padding(
              padding: const EdgeInsets.only(bottom: 8.0),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Icon(Icons.arrow_right_rounded, size: 18, color: Colors.blueAccent),
                  const SizedBox(width: 4),
                  Expanded(
                    child: Text(
                      item,
                      style: theme.textTheme.bodyMedium?.copyWith(height: 1.3),
                    ),
                  ),
                ],
              ),
            ),
          ),

          const SizedBox(height: 14),

          // Action Buttons Bar
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              // 1. Confirm Button
              ElevatedButton.icon(
                onPressed: onConfirm,
                icon: const Icon(Icons.check_circle_outline, size: 16),
                label: const Text('Xác nhận'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.green.shade700,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
              ),

              // 2. Edit Button
              OutlinedButton.icon(
                onPressed: () => _showEditDialog(context),
                icon: const Icon(Icons.edit_note, size: 16),
                label: const Text('Sửa'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: Colors.amber.shade600,
                  side: BorderSide(color: Colors.amber.shade600),
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
              ),

              // 3. Continue Discussing Button
              OutlinedButton.icon(
                onPressed: onContinue,
                icon: const Icon(Icons.chat_bubble_outline, size: 16),
                label: const Text('Tiếp tục trao đổi'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: Colors.blueAccent,
                  side: const BorderSide(color: Colors.blueAccent),
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
              ),

              // 4. Mark Uncertain Button
              TextButton.icon(
                onPressed: onMarkUncertain,
                icon: const Icon(Icons.help_outline, size: 16),
                label: const Text('Chưa rõ (UNKNOWN)'),
                style: TextButton.styleFrom(
                  foregroundColor: Colors.grey,
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  void _showEditDialog(BuildContext context) {
    if (claims.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Không có dữ kiện cụ thể nào để sửa.')),
      );
      return;
    }

    final claimToEdit = claims.first;
    final textController = TextEditingController(
      text: claimToEdit.value is Map
          ? (claimToEdit.value['raw']?.toString() ?? claimToEdit.value.toString())
          : claimToEdit.value.toString(),
    );

    showDialog(
      context: context,
      builder: (dialogCtx) {
        return AlertDialog(
          title: Text('Sửa dữ kiện: ${claimToEdit.subject}'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Thuộc tính: ${claimToEdit.predicate}',
                  style: const TextStyle(fontSize: 13, color: Colors.grey)),
              const SizedBox(height: 12),
              TextField(
                controller: textController,
                decoration: const InputDecoration(
                  labelText: 'Giá trị chính xác',
                  border: OutlineInputBorder(),
                ),
                maxLines: 3,
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogCtx).pop(),
              child: const Text('Hủy'),
            ),
            ElevatedButton(
              onPressed: () {
                final newVal = textController.text.trim();
                if (newVal.isNotEmpty) {
                  onEdit(claimToEdit, newVal);
                }
                Navigator.of(dialogCtx).pop();
              },
              child: const Text('Lưu & Cập nhật'),
            ),
          ],
        );
      },
    );
  }
}
