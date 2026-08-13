import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/ai_team_controller.dart';

class AiTeamView extends StatelessWidget {
  const AiTeamView({super.key});

  String _translateFunction(dynamic func) {
    if (func == null) return 'Chưa xác định';
    final str = func.toString().toUpperCase();
    switch (str) {
      case 'LEGAL':
        return 'Pháp lý';
      case 'MARKETING':
        return 'Marketing';
      case 'SALES':
        return 'Bán hàng';
      case 'TECH':
      case 'ENGINEERING':
        return 'Kỹ thuật';
      case 'FINANCE':
        return 'Tài chính';
      default:
        return func.toString();
    }
  }

  String _translateStatus(dynamic status) {
    if (status == null) return 'Không rõ';
    final str = status.toString().toUpperCase();
    switch (str) {
      case 'ACTIVE':
        return 'Hoạt động';
      case 'INACTIVE':
        return 'Tạm dừng';
      case 'IDLE':
        return 'Chờ';
      case 'OPEN':
        return 'Đang mở';
      default:
        return status.toString();
    }
  }

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
            return Card(
                child: Padding(
                    padding: const EdgeInsets.all(18),
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Row(children: [
                        Expanded(child: Text(_translateFunction(item['function']), style: Theme.of(context).textTheme.titleLarge)),
                        Chip(label: Text(_translateStatus(item['status'])))
                      ]),
                      const SizedBox(height: 12),
                      Text('Đang làm: ${item['current_work'] ?? 'Không có'}'),
                      Text('Kết quả mới nhất: ${item['latest_result'] ?? 'Chưa có'}'),
                      const Spacer(),
                      Text('Nhiệm vụ: ${item['task_count'] ?? 0} · Kết quả: ${item['outcome_count'] ?? 0}'),
                      if (item['needs_founder'] == true) const Text('Cần founder xử lý', style: TextStyle(color: Colors.orange, fontWeight: FontWeight.bold)),
                    ])));
          },
        ),
      );
    });
  }
}
