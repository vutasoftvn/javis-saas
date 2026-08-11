import 'package:flutter/material.dart';
import '../../../../core/widgets/app_modal_dialog.dart';

class PestelFormDialog {
  static void show(
    BuildContext context, {
    dynamic item,
    String? initialFactor,
    required Function(Map<String, dynamic> data) onSubmit,
  }) {
    final isEdit = item != null;
    String factor = item?['factor']?.toString() ?? initialFactor ?? 'Political';
    final statementController = TextEditingController(text: item?['statement']?.toString() ?? '');
    String impact = item?['impact']?.toString() ?? 'Positive';

    final factorOptions = ['Political', 'Economic', 'Social', 'Technological', 'Environmental', 'Legal'];

    AppModalDialog.show(
      context: context,
      title: isEdit ? 'Chỉnh sửa Yếu tố PESTEL' : 'Thêm Yếu tố PESTEL',
      subtitle: 'Phân tích tác động của môi trường vĩ mô lên chiến lược doanh nghiệp.',
      icon: Icons.public_rounded,
      content: StatefulBuilder(
        builder: (context, setState) {
          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text('Yếu tố vĩ mô:', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.white70)),
              const SizedBox(height: 8),
              DropdownButtonFormField<String>(
                initialValue: factorOptions.contains(factor) ? factor : 'Political',
                dropdownColor: const Color(0xFF1E293B),
                style: const TextStyle(color: Colors.white),
                decoration: InputDecoration(
                  filled: true,
                  fillColor: Colors.white.withValues(alpha: 0.05),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                ),
                items: factorOptions.map((f) {
                  return DropdownMenuItem(value: f, child: Text(_getPestelFactorLabel(f)));
                }).toList(),
                onChanged: (val) {
                  if (val != null) setState(() => factor = val);
                },
              ),
              const SizedBox(height: 16),
              const Text('Nhận định / Phát biểu:', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.white70)),
              const SizedBox(height: 8),
              TextField(
                controller: statementController,
                maxLines: 3,
                style: const TextStyle(color: Colors.white),
                decoration: InputDecoration(
                  hintText: 'Nhập nội dung quan sát hoặc phân tích...',
                  hintStyle: const TextStyle(color: Colors.white38),
                  filled: true,
                  fillColor: Colors.white.withValues(alpha: 0.05),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                ),
              ),
              const SizedBox(height: 16),
              const Text('Mức độ tác động:', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.white70)),
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
                  DropdownMenuItem(value: 'Positive', child: Text('Tích cực')),
                  DropdownMenuItem(value: 'Neutral', child: Text('Trung tính')),
                  DropdownMenuItem(value: 'Negative', child: Text('Tiêu cực')),
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
              'factor': factor,
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

  static String _getPestelFactorLabel(String factor) {
    switch (factor.toUpperCase()) {
      case 'POLITICAL': return 'Chính trị (Political)';
      case 'ECONOMIC': return 'Kinh tế (Economic)';
      case 'SOCIAL': return 'Xã hội (Social)';
      case 'TECHNOLOGICAL': return 'Công nghệ (Technological)';
      case 'ENVIRONMENTAL': return 'Môi trường (Environmental)';
      case 'LEGAL': return 'Pháp lý (Legal)';
      default: return factor;
    }
  }
}
