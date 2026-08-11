import 'package:flutter/material.dart';
import '../../../../core/widgets/app_modal_dialog.dart';

class TowsFormDialog {
  static void show(
    BuildContext context, {
    dynamic option,
    String? initialQuadrant,
    required Function(Map<String, dynamic> data) onSubmit,
  }) {
    final isEdit = option != null;
    String quadrant = (option?['quadrant']?.toString() ?? initialQuadrant ?? 'SO').toUpperCase();
    final titleController = TextEditingController(text: option?['title']?.toString() ?? '');
    final tradeoffsController = TextEditingController(text: option?['tradeoffs']?.toString() ?? '');

    final quadrantOptions = ['SO', 'ST', 'WO', 'WT'];

    AppModalDialog.show(
      context: context,
      title: isEdit ? 'Chỉnh sửa Lựa chọn Chiến lược TOWS' : 'Thêm Lựa chọn Chiến lược TOWS',
      subtitle: 'Kết hợp các góc độ SWOT để hình thành chiến lược hành động cụ thể.',
      icon: Icons.alt_route_rounded,
      content: StatefulBuilder(
        builder: (context, setState) {
          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text('Góc độ chiến lược TOWS:', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.white70)),
              const SizedBox(height: 8),
              DropdownButtonFormField<String>(
                initialValue: quadrantOptions.contains(quadrant) ? quadrant : 'SO',
                dropdownColor: const Color(0xFF1E293B),
                style: const TextStyle(color: Colors.white),
                decoration: InputDecoration(
                  filled: true,
                  fillColor: Colors.white.withValues(alpha: 0.05),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                ),
                items: quadrantOptions.map((q) {
                  return DropdownMenuItem(value: q, child: Text(_getTowsLabel(q)));
                }).toList(),
                onChanged: (val) {
                  if (val != null) setState(() => quadrant = val);
                },
              ),
              const SizedBox(height: 16),
              const Text('Tên chiến lược / Định hướng:', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.white70)),
              const SizedBox(height: 8),
              TextField(
                controller: titleController,
                style: const TextStyle(color: Colors.white),
                decoration: InputDecoration(
                  hintText: 'VD: Mở rộng kênh phân phối tự động hóa qua AI...',
                  hintStyle: const TextStyle(color: Colors.white38),
                  filled: true,
                  fillColor: Colors.white.withValues(alpha: 0.05),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                ),
              ),
              const SizedBox(height: 16),
              const Text('Sự đánh đổi / Rủi ro đi kèm:', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.white70)),
              const SizedBox(height: 8),
              TextField(
                controller: tradeoffsController,
                maxLines: 2,
                style: const TextStyle(color: Colors.white),
                decoration: InputDecoration(
                  hintText: 'Nhập những tài nguyên cần hy sinh hoặc rủi ro chấp nhận...',
                  hintStyle: const TextStyle(color: Colors.white38),
                  filled: true,
                  fillColor: Colors.white.withValues(alpha: 0.05),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                ),
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
            if (titleController.text.trim().isEmpty) return;
            onSubmit({
              'quadrant': quadrant,
              'title': titleController.text.trim(),
              'tradeoffs': tradeoffsController.text.trim(),
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

  static String _getTowsLabel(String quadrant) {
    switch (quadrant.toUpperCase()) {
      case 'SO': return 'Chiến lược SO (Tận dụng cơ hội)';
      case 'ST': return 'Chiến lược ST (Vượt qua thách thức)';
      case 'WO': return 'Chiến lược WO (Khắc phục điểm yếu)';
      case 'WT': return 'Chiến lược WT (Tối thiểu hóa rủi ro)';
      default: return quadrant;
    }
  }
}
