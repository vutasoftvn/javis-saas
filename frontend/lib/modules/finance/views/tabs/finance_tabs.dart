import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../controllers/finance_controller.dart';

class FinanceOverviewTab extends GetView<FinanceController> {
  const FinanceOverviewTab({super.key});

  String _translateKey(String key) {
    switch (key) {
      case 'snapshot': return 'Ảnh chụp tổng quan tài chính';
      case 'as_of': return 'Thời điểm cập nhật';
      case 'cash': return 'Tiền mặt & Tiền gửi';
      case 'burn': return 'Tốc độ đốt tiền (Burn rate)';
      case 'runway_months': return 'Số tháng Runway còn lại';
      case 'revenue': return 'Doanh thu';
      case 'expenses': return 'Chi phí';
      default:
        return key.replaceAll('_', ' ');
    }
  }

  @override
  Widget build(BuildContext context) => Obx(() {
        final entries = controller.overview.entries.toList();
        if (entries.isEmpty) {
          return const Center(child: Text('Chưa có dữ liệu tổng quan tài chính'));
        }
        return ListView(
          padding: const EdgeInsets.all(20),
          children: entries.map((entry) {
            if (entry.value is Map) {
              final subMap = entry.value as Map<String, dynamic>;
              return Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(_translateKey(entry.key), style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                      const SizedBox(height: 12),
                      ...subMap.entries.map((sub) => Padding(
                            padding: const EdgeInsets.symmetric(vertical: 4),
                            child: Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Text(_translateKey(sub.key)),
                                Text('${sub.value ?? 'N/A'}', style: const TextStyle(fontWeight: FontWeight.w600)),
                              ],
                            ),
                          )),
                    ],
                  ),
                ),
              );
            }
            return ListTile(
              title: Text(_translateKey(entry.key)),
              trailing: Text('${entry.value}'),
            );
          }).toList(),
        );
      });
}

class FinanceListTab extends GetView<FinanceController> {
  const FinanceListTab({super.key, required this.kind}); final String kind;
  @override Widget build(BuildContext context) => Obx(() { final rows = switch(kind) {'transactions' => controller.transactions, 'documents' => controller.documents, 'books' => controller.books, 'reports' => controller.reports, 'periods' => controller.periods, _ => controller.exceptions}; return rows.isEmpty ? const Center(child: Text('Chưa có dữ liệu')) : ListView.builder(itemCount: rows.length, itemBuilder: (_, i) => ListTile(title: Text('${rows[i]}'))); });
}

class FinanceProfileTab extends GetView<FinanceController> {
  const FinanceProfileTab({super.key});
  @override Widget build(BuildContext context) => Obx(() => controller.profile.isEmpty
      ? const Center(child: Text('Chưa có hồ sơ kế toán'))
      : ListView(children: controller.profile.entries.map((entry) => ListTile(title: Text(entry.key), trailing: Text('${entry.value}'))).toList()));
}
