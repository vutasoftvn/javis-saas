import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/theme/app_theme.dart';

class OverrideEditorDialog extends StatefulWidget {
  final String packId;
  final String assetId;
  final String assetType;
  final String title;
  final String currentBody;
  final String? currentNotes;
  final bool isCustomized;
  final Function(String body, String notes) onSave;
  final VoidCallback onResetToFactory;

  const OverrideEditorDialog({
    super.key,
    required this.packId,
    required this.assetId,
    required this.assetType,
    required this.title,
    required this.currentBody,
    this.currentNotes,
    required this.isCustomized,
    required this.onSave,
    required this.onResetToFactory,
  });

  @override
  State<OverrideEditorDialog> createState() => _OverrideEditorDialogState();
}

class _OverrideEditorDialogState extends State<OverrideEditorDialog> {
  late TextEditingController _bodyController;
  late TextEditingController _notesController;

  @override
  void initState() {
    super.initState();
    _bodyController = TextEditingController(text: widget.currentBody);
    _notesController = TextEditingController(text: widget.currentNotes ?? '');
  }

  @override
  void dispose() {
    _bodyController.dispose();
    _notesController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: const Color(0xFF0F172A),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Container(
        width: 850,
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
                        color: AppTheme.primary.withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: const Icon(Icons.tune_rounded, color: AppTheme.primary, size: 24),
                    ),
                    const SizedBox(width: 12),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Tùy Biến Doanh Nghiệp: ${widget.title}',
                          style: const TextStyle(color: Colors.white, fontSize: 17, fontWeight: FontWeight.bold),
                        ),
                        Text(
                          'Mã: ${widget.assetId} (${widget.assetType.toUpperCase()})',
                          style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 12),
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

            // Note on Overriding
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: const Color(0xFF1E293B).withValues(alpha: 0.5),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: const Color(0xFF334155)),
              ),
              child: Row(
                children: [
                  const Icon(Icons.info_outline, color: AppTheme.primary, size: 20),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      widget.isCustomized
                          ? 'Tài sản này hiện đang có tùy biến riêng của công ty. Bản Factory gốc vẫn được lưu trữ an toàn.'
                          : 'Bạn đang xem bản mẫu Factory gốc. Khi lưu, hệ thống sẽ tạo một bản tùy biến riêng cho Workspace của bạn.',
                      style: const TextStyle(color: Colors.white70, fontSize: 12),
                    ),
                  ),
                  if (widget.isCustomized) ...[
                    const SizedBox(width: 10),
                    OutlinedButton.icon(
                      onPressed: () {
                        Get.back();
                        widget.onResetToFactory();
                      },
                      icon: const Icon(Icons.restore, size: 14, color: AppTheme.warning),
                      label: const Text('Khôi phục Factory', style: TextStyle(color: AppTheme.warning, fontSize: 12)),
                      style: OutlinedButton.styleFrom(
                        side: const BorderSide(color: AppTheme.warning),
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                      ),
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(height: 16),

            // Body Editor
            const Text(
              'Nội dung Markdown (Body Override):',
              style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13),
            ),
            const SizedBox(height: 8),
            Expanded(
              child: Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFF090D16),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: const Color(0xFF1E293B)),
                ),
                child: TextField(
                  controller: _bodyController,
                  maxLines: null,
                  expands: true,
                  style: const TextStyle(color: Colors.white, fontFamily: 'monospace', fontSize: 13),
                  decoration: const InputDecoration(
                    border: InputBorder.none,
                    hintText: 'Nhập nội dung mẫu markdown...',
                    hintStyle: TextStyle(color: Colors.white30),
                  ),
                ),
              ),
            ),
            const SizedBox(height: 12),

            // Change Notes
            const Text(
              'Ghi chú lý do tùy biến (Auditing):',
              style: TextStyle(color: Colors.white, fontWeight: FontWeight.w600, fontSize: 12),
            ),
            const SizedBox(height: 6),
            TextField(
              controller: _notesController,
              style: const TextStyle(color: Colors.white, fontSize: 13),
              decoration: InputDecoration(
                filled: true,
                fillColor: const Color(0xFF090D16),
                hintText: 'Ví dụ: Điều chỉnh điều khoản bảo mật thời hạn 3 năm thay vì 2 năm theo yêu cầu BOD',
                hintStyle: const TextStyle(color: Colors.white30, fontSize: 12),
                contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                  borderSide: const BorderSide(color: Color(0xFF1E293B)),
                ),
              ),
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
                  child: const Text('Đóng'),
                ),
                const SizedBox(width: 12),
                ElevatedButton.icon(
                  onPressed: () {
                    Get.back();
                    widget.onSave(_bodyController.text, _notesController.text);
                  },
                  icon: const Icon(Icons.save_rounded, size: 16),
                  label: const Text('Lưu Tùy Biến'),
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
}
