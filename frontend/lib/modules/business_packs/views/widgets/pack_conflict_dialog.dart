import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/theme/app_theme.dart';

class PackConflictDialog extends StatefulWidget {
  final String packId;
  final String assetId;
  final String oldContent;
  final String newContent;
  final String? diffText;
  final Function(String resolution, String? mergedBody) onResolve;

  const PackConflictDialog({
    super.key,
    required this.packId,
    required this.assetId,
    required this.oldContent,
    required this.newContent,
    this.diffText,
    required this.onResolve,
  });

  @override
  State<PackConflictDialog> createState() => _PackConflictDialogState();
}

class _PackConflictDialogState extends State<PackConflictDialog> {
  String _selectedStrategy = 'KEEP_COMPANY';
  late TextEditingController _mergedTextController;

  @override
  void initState() {
    super.initState();
    _mergedTextController = TextEditingController(text: widget.oldContent);
  }

  @override
  void dispose() {
    _mergedTextController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: const Color(0xFF0F172A),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Container(
        width: 900,
        height: 700,
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: Colors.amber.withValues(alpha: 0.2),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: const Icon(Icons.compare_arrows_rounded, color: Colors.amber, size: 24),
                    ),
                    const SizedBox(width: 12),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Xung Đột Phiên Bản Bản Mẫu Nghiệp Vụ',
                          style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
                        ),
                        Text(
                          'Tài sản: ${widget.assetId}',
                          style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 13),
                        ),
                      ],
                    ),
                  ],
                ),
                IconButton(
                  icon: const Icon(Icons.close, color: Colors.white70),
                  onPressed: () => Get.back(),
                ),
              ],
            ),
            const SizedBox(height: 16),
            const Divider(color: Color(0xFF1E293B)),
            const SizedBox(height: 12),

            // Resolution Strategy Selector
            const Text(
              'Chọn chiến lược xử lý xung đột:',
              style: TextStyle(color: Colors.white, fontWeight: FontWeight.w600, fontSize: 14),
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              children: [
                _buildStrategyChip('KEEP_COMPANY', 'Giữ tùy biến công ty', 'Không thay đổi nội dung tùy chỉnh hiện tại', Icons.bookmark_border),
                _buildStrategyChip('ACCEPT_FACTORY', 'Chấp nhận bản gốc mới', 'Ghi đè bằng bản nâng cấp từ Factory', Icons.system_update_alt),
                _buildStrategyChip('MERGE', 'Trộn nội dung thủ công', 'Tự điều chỉnh nội dung kết hợp cả 2', Icons.merge_type),
                _buildStrategyChip('RESET_FACTORY', 'Khôi phục mặc định gốc', 'Hủy toàn bộ tùy biến, về factory', Icons.restore),
              ],
            ),
            const SizedBox(height: 16),

            // Comparison View
            Expanded(
              child: _selectedStrategy == 'MERGE'
                  ? _buildMergeEditor()
                  : _buildDiffComparisonView(),
            ),

            const SizedBox(height: 16),
            // Actions
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                OutlinedButton(
                  onPressed: () => Get.back(),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: Colors.white70,
                    side: const BorderSide(color: Color(0xFF334155)),
                  ),
                  child: const Text('Huỷ bỏ'),
                ),
                const SizedBox(width: 12),
                ElevatedButton.icon(
                  onPressed: () {
                    Get.back();
                    widget.onResolve(
                      _selectedStrategy,
                      _selectedStrategy == 'MERGE' ? _mergedTextController.text : null,
                    );
                  },
                  icon: const Icon(Icons.check_rounded, size: 18),
                  label: const Text('Áp dụng Giải quyết'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.primary,
                    foregroundColor: AppTheme.backgroundDarker,
                    padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStrategyChip(String strategy, String label, String tooltip, IconData icon) {
    final isSelected = _selectedStrategy == strategy;
    return Tooltip(
      message: tooltip,
      child: ChoiceChip(
        avatar: Icon(icon, size: 16, color: isSelected ? Colors.black : Colors.white70),
        label: Text(label),
        selected: isSelected,
        selectedColor: AppTheme.primary,
        backgroundColor: const Color(0xFF1E293B),
        labelStyle: TextStyle(
          color: isSelected ? Colors.black : Colors.white70,
          fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
          fontSize: 12,
        ),
        onSelected: (selected) {
          if (selected) {
            setState(() {
              _selectedStrategy = strategy;
            });
          }
        },
      ),
    );
  }

  Widget _buildDiffComparisonView() {
    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF090D16),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFF1E293B)),
      ),
      child: Row(
        children: [
          // Left: Company Current
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  decoration: const BoxDecoration(
                    color: Color(0xFF1E293B),
                    borderRadius: BorderRadius.only(topLeft: Radius.circular(12)),
                  ),
                  child: const Row(
                    children: [
                      Icon(Icons.edit_note, size: 16, color: AppTheme.primary),
                      SizedBox(width: 8),
                      Text('Bản hiện tại (Doanh nghiệp)', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 12)),
                    ],
                  ),
                ),
                Expanded(
                  child: SingleChildScrollView(
                    padding: const EdgeInsets.all(12),
                    child: SelectableText(
                      widget.oldContent,
                      style: const TextStyle(color: Colors.white70, fontFamily: 'monospace', fontSize: 12),
                    ),
                  ),
                ),
              ],
            ),
          ),
          const VerticalDivider(width: 1, color: Color(0xFF1E293B)),
          // Right: Upstream Factory New
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  decoration: const BoxDecoration(
                    color: Color(0xFF1E293B),
                    borderRadius: BorderRadius.only(topRight: Radius.circular(12)),
                  ),
                  child: const Row(
                    children: [
                      Icon(Icons.cloud_download, size: 16, color: Color(0xFF10B981)),
                      SizedBox(width: 8),
                      Text('Bản cập nhật mới (Factory Pack)', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 12)),
                    ],
                  ),
                ),
                Expanded(
                  child: SingleChildScrollView(
                    padding: const EdgeInsets.all(12),
                    child: SelectableText(
                      widget.newContent,
                      style: const TextStyle(color: Colors.white70, fontFamily: 'monospace', fontSize: 12),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMergeEditor() {
    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF090D16),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFF1E293B)),
      ),
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Trình soạn thảo kết hợp (Merged Output):',
            style: TextStyle(color: AppTheme.primary, fontWeight: FontWeight.bold, fontSize: 13),
          ),
          const SizedBox(height: 8),
          Expanded(
            child: TextField(
              controller: _mergedTextController,
              maxLines: null,
              expands: true,
              style: const TextStyle(color: Colors.white, fontFamily: 'monospace', fontSize: 13),
              decoration: const InputDecoration(
                border: InputBorder.none,
                hintText: 'Nhập nội dung đã kết hợp...',
                hintStyle: TextStyle(color: Colors.white30),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
