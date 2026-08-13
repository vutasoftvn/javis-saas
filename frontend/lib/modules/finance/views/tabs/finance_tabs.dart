import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../controllers/finance_controller.dart';

class FinanceOverviewTab extends GetView<FinanceController> {
  const FinanceOverviewTab({super.key});

  String _translateKey(String key) {
    switch (key) {
      case 'snapshot':
        return 'Ảnh chụp tổng quan tài chính';
      case 'as_of':
        return 'Thời điểm cập nhật';
      case 'cash':
        return 'Tiền mặt & Tiền gửi';
      case 'burn':
        return 'Tốc độ đốt tiền (Burn rate)';
      case 'runway_months':
        return 'Số tháng Runway còn lại';
      case 'revenue':
        return 'Doanh thu';
      case 'expenses':
        return 'Chi phí';
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
                  Text(
                    _translateKey(entry.key),
                    style: const TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 16,
                    ),
                  ),
                  const SizedBox(height: 12),
                  ...subMap.entries.map(
                    (sub) => Padding(
                      padding: const EdgeInsets.symmetric(vertical: 4),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(_translateKey(sub.key)),
                          Text(
                            '${sub.value ?? 'N/A'}',
                            style: const TextStyle(fontWeight: FontWeight.w600),
                          ),
                        ],
                      ),
                    ),
                  ),
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
  const FinanceListTab({super.key, required this.kind});
  final String kind;
  @override
  Widget build(BuildContext context) => Obx(() {
    final rows = switch (kind) {
      'transactions' => controller.transactions,
      'documents' => controller.documents,
      'books' => controller.books,
      'reports' => controller.reports,
      'periods' => controller.periods,
      _ => controller.exceptions,
    };
    return rows.isEmpty
        ? const Center(child: Text('Chưa có dữ liệu'))
        : ListView.builder(
            itemCount: rows.length,
            itemBuilder: (_, i) => ListTile(title: Text('${rows[i]}')),
          );
  });
}

class FinanceProfileTab extends GetView<FinanceController> {
  const FinanceProfileTab({super.key});
  @override
  Widget build(BuildContext context) => Obx(() {
    if (controller.profile.isEmpty) {
      return Center(
        child: FilledButton.icon(
          onPressed: () async {
            final ok = await controller.createProfile();
            Get.snackbar(
              ok ? 'Đã tạo hồ sơ' : 'Không thể tạo hồ sơ',
              ok
                  ? 'Hãy xác nhận để kích hoạt sổ kế toán.'
                  : 'Vui lòng thử lại.',
            );
          },
          icon: const Icon(Icons.add),
          label: const Text('Khởi tạo hồ sơ kế toán TT58 Mode 1'),
        ),
      );
    }
    final pending = controller.profile['status'] == 'PENDING_CONFIRMATION';
    return ListView(
      children: [
        ...controller.profile.entries.map(
          (entry) => ListTile(
            title: Text(entry.key),
            trailing: Text('${entry.value}'),
          ),
        ),
        if (pending)
          Padding(
            padding: const EdgeInsets.all(16),
            child: FilledButton(
              onPressed: () => Get.dialog(
                AlertDialog(
                  title: const Text('Xác nhận kích hoạt'),
                  content: const Text(
                    'Bạn xác nhận áp dụng hồ sơ kế toán này? Hành động được ghi nhận để phục vụ kiểm toán.',
                  ),
                  actions: [
                    TextButton(onPressed: Get.back, child: const Text('Hủy')),
                    FilledButton(
                      onPressed: () async {
                        final ok = await controller.activateProfile();
                        Get.back();
                        Get.snackbar(
                          ok ? 'Đã kích hoạt' : 'Không thể kích hoạt',
                          ok
                              ? 'Hồ sơ kế toán đã sẵn sàng.'
                              : 'Vui lòng thử lại.',
                        );
                      },
                      child: const Text('Xác nhận'),
                    ),
                  ],
                ),
              ),
              child: const Text('Xác nhận kích hoạt'),
            ),
          ),
      ],
    );
  });
}
