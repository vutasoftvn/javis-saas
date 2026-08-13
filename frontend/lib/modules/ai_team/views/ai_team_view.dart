import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/ai_team_controller.dart';

class AiTeamView extends StatelessWidget {
  const AiTeamView({super.key});

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<AiTeamController>()) Get.put(AiTeamController());
    final controller = Get.find<AiTeamController>();
    return Obx(() {
      if (controller.loading.value && controller.functions.isEmpty) return const Center(child: CircularProgressIndicator());
      return RefreshIndicator(
        onRefresh: controller.load,
        child: GridView.builder(
          padding: const EdgeInsets.all(20),
          gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(maxCrossAxisExtent: 380, childAspectRatio: 1.35, crossAxisSpacing: 16, mainAxisSpacing: 16),
          itemCount: controller.functions.length,
          itemBuilder: (_, index) {
            final item = controller.functions[index];
            return Card(child: Padding(padding: const EdgeInsets.all(18), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [Expanded(child: Text('${item['function']}', style: Theme.of(context).textTheme.titleLarge)), Chip(label: Text('${item['status']}'))]),
              const SizedBox(height: 12), Text('Đang làm: ${item['current_work'] ?? 'Không có'}'),
              Text('Kết quả mới nhất: ${item['latest_result'] ?? 'Chưa có'}'),
              const Spacer(), Text('Tasks ${item['task_count'] ?? 0} · Outcomes ${item['outcome_count'] ?? 0}'),
              if (item['needs_founder'] == true) const Text('Cần founder xử lý', style: TextStyle(color: Colors.orange, fontWeight: FontWeight.bold)),
            ])));
          },
        ),
      );
    });
  }
}
