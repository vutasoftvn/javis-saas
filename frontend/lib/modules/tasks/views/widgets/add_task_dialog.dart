import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/theme/app_theme.dart';
import '../../controllers/tasks_controller.dart';

class AddTaskDialog {
  static void show(BuildContext context, TasksController controller, String initialStatus) {
    final isEn = Get.locale?.languageCode == 'en';
    final textController = TextEditingController();
    Get.dialog(
      AlertDialog(
        backgroundColor: AppTheme.surfaceDark,
        title: Text(isEn ? 'New Task' : 'Công việc mới', style: const TextStyle(color: Colors.white)),
        content: TextField(
          controller: textController,
          autofocus: true,
          style: const TextStyle(color: Colors.white),
          decoration: InputDecoration(
            hintText: isEn ? 'What needs to be done?' : 'Cần làm những gì?',
            hintStyle: const TextStyle(color: AppTheme.textMutedDark),
          ),
          onSubmitted: (val) {
            controller.addTask(val, initialStatus);
            Get.back();
          },
        ),
        actions: [
          TextButton(
            onPressed: () => Get.back(),
            child: Text(isEn ? 'Cancel' : 'Hủy', style: const TextStyle(color: AppTheme.textMutedDark)),
          ),
          ElevatedButton(
            onPressed: () {
              controller.addTask(textController.text, initialStatus);
              Get.back();
            },
            style: ElevatedButton.styleFrom(backgroundColor: AppTheme.primary),
            child: Text(isEn ? 'Add' : 'Thêm', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );
  }
}
