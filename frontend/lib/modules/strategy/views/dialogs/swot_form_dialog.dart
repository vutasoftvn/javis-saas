import 'package:flutter/material.dart';
import '../../../../core/widgets/app_modal_dialog.dart';

class SwotFormDialog {
  static void show(
    BuildContext context, {
    dynamic item,
    String? initialCategory,
    required Function(Map<String, dynamic> data) onSubmit,
  }) {
    final isEdit = item != null;
    String category = item?['category']?.toString() ?? initialCategory ?? 'Strength';
    final statementController = TextEditingController(text: item?['statement']?.toString() ?? '');
    String impact = item?['impact']?.toString() ?? 'High';

    final categoryOptions = ['Strength', 'Weakness', 'Opportunity', 'Threat'];

    AppModalDialog.show(
      context: context,
      title: isEdit ? 'Chỉnh sửa Mục SWOT' : 'Thêm Mục SWOT',
      subtitle: 'Đánh giá điểm mạnh, điểm yếu nội bộ và cơ hội, thách thức bên ngoài.',
      icon: Icons.grid_view_rounded,
      content: StatefulBuilder(
        builder: (context, setState) {
          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text('Phân loại SWOT:', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.white70)),
              const SizedBox(height: 8),
              DropdownButtonFormField<String>(
                initialValue: categoryOptions.contains(category) ? category : 'Strength',
                dropdownColor: const Color(0xFF1E293B),
                style: const TextStyle(color: Colors.white),
                decoration: InputDecoration(
                  filled: true,
                  fillColor: Colors.white.withValues(alpha: 0.05),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                ),
                items: categoryOptions.map((c) {
                  return DropdownMenuItem(value: c, child: Text(_getSwotCategoryLabel(c)));
                }).toList(),
                onChanged: (val) {
                  if (val != null) setState(() => category = val);
                },
              ),
              const SizedBox(height: 16),
              const Text('Nội dung nhận định:', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.white70)),
              const SizedBox(height: 8),
              TextField(
                controller: statementController,
                maxLines: 3,
                style: const TextStyle(color: Colors.white),
                decoration: InputDecoration(
                  hintText: 'Mô tả chi tiết điểm mạnh/yếu hoặc cơ hội/thách thức...',
                  hintStyle: const TextStyle(color: Colors.white38),
                  filled: true,
                  fillColor: Colors.white.withValues(alpha: 0.05),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                ),
              ),
              const SizedBox(height: 16),
              const Text('Mức độ ảnh hưởng:', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.white70)),
              const SizedBox(height: 8),
              DropdownButtonFormField<String>(
                initialValue: impact,
                dropdownColor: const Color(0xFF1E293B),
                style: const TextStyle(color: Colors.white),
                decoration: InputDecoration(
                  filled: true,
                  fillColor: Colors.white.withValues(alpha: 0.05),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                ),
                items: const [
                  DropdownMenuItem(value: 'High', child: Text('Cao')),
                  DropdownMenuItem(value: 'Medium', child: Text('Trung bình')),
                  DropdownMenuItem(value: 'Low', child: Text('Thấp')),
                ],
                onChanged: (val) {
                  if (val != null) setState(() => impact = val);
                },
              ),
            ],
          );
        },
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Hủy', style: TextStyle(color: Colors.white60)),
        ),
        ElevatedButton(
          onPressed: () {
            if (statementController.text.trim().isEmpty) return;
            onSubmit({
              'category': category,
              'statement': statementController.text.trim(),
              'impact': impact,
            });
            Navigator.of(context).pop();
          },
          style: ElevatedButton.styleFrom(
            backgroundColor: const Color(0xFF4F46E5),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
          ),
          child: Text(isEdit ? 'Lưu' : 'Thêm mới'),
        ),
      ],
    );
  }

  static String _getSwotCategoryLabel(String category) {
    switch (category.toUpperCase()) {
      case 'STRENGTH': return 'Điểm mạnh (Strength)';
      case 'WEAKNESS': return 'Điểm yếu (Weakness)';
      case 'OPPORTUNITY': return 'Cơ hội (Opportunity)';
      case 'THREAT': return 'Thách thức (Threat)';
      default: return category;
    }
  }
}
