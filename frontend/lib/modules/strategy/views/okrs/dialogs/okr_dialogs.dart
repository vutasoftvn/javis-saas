import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../../core/theme/app_theme.dart';
import '../../../../../core/widgets/app_modal_dialog.dart';
import '../../../controllers/strategy_controller.dart';

class OkrDialogs {
  static void showCreateObjectiveDialog(BuildContext context, StrategyController controller) {
    final titleController = TextEditingController();

    AppModalDialog.show(
      context: context,
      title: 'Tạo Mục Tiêu (Objective)',
      subtitle: 'Xác định mục tiêu định tính, truyền cảm hứng và rõ ràng cho tổ chức',
      icon: Icons.flag_rounded,
      maxWidth: 600,
      content: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          TextField(
            controller: titleController,
            decoration: const InputDecoration(
              labelText: 'Tiêu đề Mục tiêu',
              hintText: 'Ví dụ: Tăng trưởng doanh thu định kỳ MRR vượt mốc 50,000 USD',
              prefixIcon: Icon(Icons.title_rounded, size: 20),
            ),
          ),
        ],
      ),
      actions: [
        TextButton(onPressed: () => Get.back(), child: const Text('Huỷ', style: TextStyle(color: Colors.white60))),
        const SizedBox(width: 12),
        ElevatedButton(
          onPressed: () {
            final title = titleController.text.trim();
            if (title.isEmpty) return;
            controller.createObjective(title);
            Get.back();
          },
          style: ElevatedButton.styleFrom(
            backgroundColor: AppTheme.primary,
            foregroundColor: const Color(0xFF04070E),
          ),
          child: const Text('Tạo Mục tiêu'),
        ),
      ],
    );
  }

  static void showCreateKeyResultDialog(BuildContext context, StrategyController controller, String objectiveId) {
    final titleController = TextEditingController();
    final currentController = TextEditingController(text: '0');
    final targetController = TextEditingController(text: '100');
    final unitController = TextEditingController(text: '%');

    AppModalDialog.show(
      context: context,
      title: 'Thêm Kết Quả Then Chốt (Key Result)',
      subtitle: 'Xác định phát biểu kết quả đầu ra kèm theo các con số đo lường định lượng',
      icon: Icons.add_chart_rounded,
      maxWidth: 620,
      content: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          TextField(
            controller: titleController,
            decoration: const InputDecoration(
              labelText: 'Phát biểu Kết quả (Key Result Statement)',
              hintText: 'Ví dụ: Tự động hóa 70% các tác vụ vận hành nghiệp vụ',
              prefixIcon: Icon(Icons.check_circle_outline_rounded, size: 20),
            ),
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: currentController,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(labelText: 'Hiện tại'),
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: TextField(
                  controller: targetController,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(labelText: 'Giá trị mục tiêu'),
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: TextField(
                  controller: unitController,
                  decoration: const InputDecoration(labelText: 'Đơn vị', hintText: '%, USD, user...'),
                ),
              ),
            ],
          ),
        ],
      ),
      actions: [
        TextButton(onPressed: () => Get.back(), child: const Text('Huỷ', style: TextStyle(color: Colors.white60))),
        const SizedBox(width: 12),
        ElevatedButton(
          onPressed: () {
            final title = titleController.text.trim();
            final curr = double.tryParse(currentController.text.trim()) ?? 0.0;
            final target = double.tryParse(targetController.text.trim()) ?? 100.0;
            final unit = unitController.text.trim();
            controller.createKeyResult(
              objectiveId: objectiveId,
              title: title.isNotEmpty ? title : 'Đạt $target ${unit.isNotEmpty ? unit : '%'}',
              baselineValue: 0.0,
              currentValue: curr,
              targetValue: target,
              unit: unit.isNotEmpty ? unit : '%',
            );
            Get.back();
          },
          style: ElevatedButton.styleFrom(
            backgroundColor: AppTheme.primary,
            foregroundColor: const Color(0xFF04070E),
          ),
          child: const Text('Thêm Key Result'),
        ),
      ],
    );
  }

  static void showCheckinKeyResultDialog(BuildContext context, StrategyController controller, dynamic kr) {
    final currentVal = (kr['current_value'] as num?)?.toDouble() ?? 0.0;
    final valController = TextEditingController(text: currentVal.toString());

    AppModalDialog.show(
      context: context,
      title: 'Check-in Tiến Độ Key Result',
      subtitle: 'Cập nhật giá trị đo lường thực tế mới nhất',
      icon: Icons.edit_calendar_rounded,
      maxWidth: 520,
      content: TextField(
        controller: valController,
        keyboardType: TextInputType.number,
        decoration: InputDecoration(
          labelText: 'Giá trị hiện tại (${kr['unit'] ?? '%'})',
          prefixIcon: const Icon(Icons.speed_rounded, size: 20),
        ),
      ),
      actions: [
        TextButton(onPressed: () => Get.back(), child: const Text('Huỷ', style: TextStyle(color: Colors.white60))),
        const SizedBox(width: 12),
        ElevatedButton(
          onPressed: () {
            final newVal = double.tryParse(valController.text.trim());
            if (newVal != null) {
              controller.updateKeyResult(kr['id'], currentValue: newVal);
            }
            Get.back();
          },
          style: ElevatedButton.styleFrom(
            backgroundColor: AppTheme.secondary,
            foregroundColor: const Color(0xFF04070E),
          ),
          child: const Text('Cập nhật'),
        ),
      ],
    );
  }

  static void showCreateCycleDialog(BuildContext context, StrategyController controller) {
    final nameController = TextEditingController(text: 'Chu kỳ Thực thi 12 Tuần (Đợt ${DateTime.now().month ~/ 3 + 1})');

    AppModalDialog.show(
      context: context,
      title: 'Thiết Lập Chu Kỳ OKR 12 Tuần',
      subtitle: 'Đặt tên cho khung thời gian thực thi 12 tuần của doanh nghiệp (Mô hình 12-Week Year)',
      icon: Icons.cached_rounded,
      maxWidth: 560,
      content: TextField(
        controller: nameController,
        decoration: const InputDecoration(
          labelText: 'Tên chu kỳ thực thi 12 tuần',
          prefixIcon: Icon(Icons.label_outline_rounded, size: 20),
        ),
      ),
      actions: [
        TextButton(onPressed: () => Get.back(), child: const Text('Huỷ', style: TextStyle(color: Colors.white60))),
        const SizedBox(width: 12),
        ElevatedButton(
          onPressed: () {
            final name = nameController.text.trim();
            if (name.isEmpty) return;
            controller.createOkrCycle(name);
            Get.back();
          },
          style: ElevatedButton.styleFrom(
            backgroundColor: AppTheme.primary,
            foregroundColor: const Color(0xFF04070E),
          ),
          child: const Text('Tạo Chu kỳ'),
        ),
      ],
    );
  }

  static void showAiOkrModal(BuildContext context, StrategyController controller) {
    int objectivesCount = 2;
    int krsPerObjectiveCount = 4;
    String? selectedCycleId;

    if (controller.okrCycles.isNotEmpty) {
      selectedCycleId = controller.okrCycles.first['id']?.toString();
    }

    AppModalDialog.show(
      context: context,
      title: 'Tạo tự động OKRs bằng AI',
      subtitle: 'Phân tích Nền tảng Doanh nghiệp và Chu kỳ để đề xuất các Mục tiêu & Kết quả Then chốt đo lường được.',
      icon: Icons.auto_awesome_rounded,
      maxWidth: 620,
      content: StatefulBuilder(
        builder: (context, setState) {
          final cyclesList = controller.okrCycles;

          return SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Số lượng Mục tiêu (Objectives) cần sinh:',
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.white),
                ),
                const SizedBox(height: 6),
                DropdownButtonFormField<int>(
                  initialValue: objectivesCount,
                  dropdownColor: AppTheme.surfaceDark,
                  decoration: const InputDecoration(
                    prefixIcon: Icon(Icons.format_list_numbered_rounded, size: 18),
                  ),
                  items: const [
                    DropdownMenuItem(value: 1, child: Text('1 Mục tiêu (Tập trung trọng điểm)')),
                    DropdownMenuItem(value: 2, child: Text('2 Mục tiêu (Cân bằng & Tối ưu - Mặc định)')),
                    DropdownMenuItem(value: 3, child: Text('3 Mục tiêu (Chi tiết toàn diện các chiều)')),
                  ],
                  onChanged: (v) {
                    if (v != null) setState(() => objectivesCount = v);
                  },
                ),
                const SizedBox(height: 16),

                const Text(
                  'Số lượng Kết quả Then chốt (Key Results) / Mục tiêu:',
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.white),
                ),
                const SizedBox(height: 6),
                DropdownButtonFormField<int>(
                  initialValue: krsPerObjectiveCount,
                  dropdownColor: AppTheme.surfaceDark,
                  decoration: const InputDecoration(
                    prefixIcon: Icon(Icons.checklist_rounded, size: 18),
                  ),
                  items: const [
                    DropdownMenuItem(value: 2, child: Text('2 Key Results / Mục tiêu (Tinh gọn)')),
                    DropdownMenuItem(value: 3, child: Text('3 Key Results / Mục tiêu (Chuẩn OKRs - Mặc định)')),
                    DropdownMenuItem(value: 4, child: Text('4 Key Results / Mục tiêu (Nâng cao)')),
                    DropdownMenuItem(value: 5, child: Text('5 Key Results / Mục tiêu (Tối đa)')),
                  ],
                  onChanged: (v) {
                    if (v != null) setState(() => krsPerObjectiveCount = v);
                  },
                ),
                const SizedBox(height: 16),

                if (cyclesList.isNotEmpty) ...[
                  const Text(
                    'Chu kỳ OKR áp dụng:',
                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.white),
                  ),
                  const SizedBox(height: 6),
                  DropdownButtonFormField<String?>(
                    initialValue: selectedCycleId,
                    dropdownColor: AppTheme.surfaceDark,
                    decoration: const InputDecoration(
                      prefixIcon: Icon(Icons.cached_rounded, size: 18),
                    ),
                    items: cyclesList.map(
                      (c) => DropdownMenuItem<String?>(
                        value: c['id'].toString(),
                        child: Text('${c['name']} (${c['status'] ?? 'active'})'),
                      ),
                    ).toList(),
                    onChanged: (v) => setState(() => selectedCycleId = v),
                  ),
                  const SizedBox(height: 16),
                ],

                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AppTheme.primary.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: AppTheme.primary.withValues(alpha: 0.3)),
                  ),
                  child: const Row(
                    children: [
                      Icon(Icons.lightbulb_outline_rounded, size: 16, color: AppTheme.primary),
                      SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          'Mỗi Mục tiêu sinh ra sẽ tự động kèm theo từ 2 đến 5 Kết quả Then chốt (Key Results) có chỉ số đo lường cụ thể.',
                          style: TextStyle(fontSize: 12, color: Colors.white70),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          );
        },
      ),
      actions: [
        TextButton(
          onPressed: () => Get.back(),
          child: const Text('Huỷ', style: TextStyle(color: Colors.white60)),
        ),
        const SizedBox(width: 12),
        ElevatedButton.icon(
          onPressed: () {
            Get.back();
            controller.generateAiOkrs(
              objectivesCount: objectivesCount,
              krsPerObjectiveCount: krsPerObjectiveCount,
              cycleId: selectedCycleId,
            );
          },
          icon: const Icon(Icons.auto_awesome_rounded, size: 16),
          label: const Text('Bắt đầu Sinh OKRs bằng AI'),
          style: ElevatedButton.styleFrom(
            backgroundColor: AppTheme.primary,
            foregroundColor: const Color(0xFF04070E),
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
          ),
        ),
      ],
    );
  }
}
