// Task 7 (PHẠM VI MỞ RỘNG 2026-09-14) — UI publish Objective tối giản, đủ để
// mở route `strategy` thật và cho `showOkrWeeklyGeneratorDialog` (Task 7
// Step 2, đã commit ở c6f2df18) một nơi thật để gọi sau khi publish thành
// công. Đây KHÔNG phải thiết kế UI hoàn chỉnh — chỉ ListView Objective với
// title/status/nút Publish, đủ để chứng minh luồng thật.
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/app_toast.dart';
import '../controllers/strategy_controller.dart';
import '../models/mvp_strategy_models.dart';
import '../widgets/okr_weekly_generator_dialog.dart';

class StrategyView extends GetView<StrategyController> {
  const StrategyView({super.key});

  bool _isDraft(MvpObjective objective) => objective.status.toLowerCase() == 'draft';

  Future<void> _handlePublish(BuildContext context, MvpObjective objective) async {
    try {
      await controller.publish(objective.id);
      if (!context.mounted) return;
      await showOkrWeeklyGeneratorDialog(context, objectiveId: objective.id);
    } catch (e) {
      AppToast.error('Không publish được Objective: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Obx(() {
      if (controller.isLoading.value && controller.objectives.isEmpty) {
        return const Center(child: CircularProgressIndicator());
      }
      final error = controller.errorMessage.value;
      if (error != null && controller.objectives.isEmpty) {
        return Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(error),
              const SizedBox(height: 12),
              TextButton(
                onPressed: controller.loadObjectives,
                child: const Text('Thử lại'),
              ),
            ],
          ),
        );
      }
      final objectives = controller.objectives;
      if (objectives.isEmpty) {
        return const Center(child: Text('Chưa có Objective nào.'));
      }
      return RefreshIndicator(
        onRefresh: controller.loadObjectives,
        child: ListView.builder(
          padding: const EdgeInsets.all(16),
          itemCount: objectives.length,
          itemBuilder: (context, index) {
            final objective = objectives[index];
            return Card(
              margin: const EdgeInsets.only(bottom: 12),
              child: ListTile(
                title: Text(objective.title),
                subtitle: Text(objective.status),
                trailing: _isDraft(objective)
                    ? ElevatedButton(
                        style: ElevatedButton.styleFrom(backgroundColor: AppTheme.primary),
                        onPressed: () => _handlePublish(context, objective),
                        child: const Text('Publish'),
                      )
                    : null,
              ),
            );
          },
        ),
      );
    });
  }
}
