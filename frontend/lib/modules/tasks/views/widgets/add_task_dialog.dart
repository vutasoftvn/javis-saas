import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/theme/app_theme.dart';
import '../../controllers/tasks_controller.dart';

class AddTaskDialog {
  static void show(BuildContext context, TasksController controller, String initialStatus) {
    final textController = TextEditingController();
    Get.dialog(
      AlertDialog(
        backgroundColor: AppTheme.surfaceDark,
        title: const Text('Công việc mới', style: TextStyle(color: Colors.white)),
        content: TextField(
          controller: textController,
          autofocus: true,
          style: const TextStyle(color: Colors.white),
          decoration: const InputDecoration(
            hintText: 'Cần làm những gì?',
            hintStyle: TextStyle(color: AppTheme.textMutedDark),
          ),
          onSubmitted: (val) {
            controller.addTask(val, initialStatus);
            Get.back();
          },
        ),
        actions: [
          TextButton(
            onPressed: () => Get.back(),
            child: const Text('Hủy', style: TextStyle(color: AppTheme.textMutedDark)),
          ),
          ElevatedButton(
            onPressed: () {
              controller.addTask(textController.text, initialStatus);
              Get.back();
            },
            style: ElevatedButton.styleFrom(backgroundColor: AppTheme.primary),
            child: const Text('Thêm', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );
  }
}
