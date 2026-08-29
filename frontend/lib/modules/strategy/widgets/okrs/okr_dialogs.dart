import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../controllers/strategy_controller.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/widgets/app_modal_dialog.dart';

class OkrDialogs {
  static void showCreateObjectiveDialog(BuildContext context, StrategyController controller) {
    final titleController = TextEditingController();

    AppModalDialog.show(
      context: context,
      title: 'Tạo Mục Tiêu (Objective)',
      subtitle: 'Xác định mục tiêu định tính, truyền cảm hứng và rõ ràng cho tổ chức',
      icon: Icons.flag_rounded,
      maxWidth: 600,
      content: TextField(
        controller: titleController,
        decoration: const InputDecoration(
          labelText: 'Tiêu đề Mục tiêu',
          hintText: 'Ví dụ: Tăng trưởng doanh thu định kỳ MRR vượt mốc 50,000 USD',
          prefixIcon: Icon(Icons.title_rounded, size: 20),
        ),
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
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(100)),
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
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(100)),
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
            final val = double.tryParse(valController.text.trim());
            if (val != null) {
              controller.checkinKeyResult(kr['id'].toString(), val);
            }
            Get.back();
          },
          style: ElevatedButton.styleFrom(backgroundColor: AppTheme.primary, foregroundColor: const Color(0xFF04070E)),
          child: const Text('Lưu Check-in'),
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
          style: ElevatedButton.styleFrom(backgroundColor: AppTheme.primary, foregroundColor: const Color(0xFF04070E)),
          child: const Text('Tạo Chu kỳ'),
        ),
      ],
    );
  }

  static void showCreateCommitmentDialog(BuildContext context, StrategyController controller, String planId) {
    final titleController = TextEditingController();

    AppModalDialog.show(
      context: context,
      title: 'Thêm Cam Kết Tuần (Weekly Commitment)',
      subtitle: 'Hành động cụ thể cam kết hoàn thành để đạt trọng tâm tuần',
      icon: Icons.add_task_rounded,
      maxWidth: 560,
      content: TextField(
        controller: titleController,
        decoration: const InputDecoration(
          labelText: 'Nội dung cam kết',
          hintText: 'Ví dụ: Đóng gói và phát hành bản dựng macOS mới',
          prefixIcon: Icon(Icons.check_circle_outline_rounded, size: 20),
        ),
      ),
      actions: [
        TextButton(onPressed: () => Get.back(), child: const Text('Huỷ', style: TextStyle(color: Colors.white60))),
        const SizedBox(width: 12),
        ElevatedButton(
          onPressed: () {
            final title = titleController.text.trim();
            if (title.isEmpty) return;
            controller.createWeeklyCommitment(planId, title);
            Get.back();
          },
          style: ElevatedButton.styleFrom(backgroundColor: AppTheme.accent),
          child: const Text('Thêm Cam kết'),
        ),
      ],
    );
  }
}
