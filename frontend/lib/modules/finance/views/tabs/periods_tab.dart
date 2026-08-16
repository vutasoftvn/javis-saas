import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../controllers/finance_controller.dart';

class FinancePeriodsTab extends GetView<FinanceController> {
  const FinancePeriodsTab({super.key});

  void _openCreatePeriodDialog(BuildContext context) {
    final startCtrl = TextEditingController(text: '2026-08-01');
    final endCtrl = TextEditingController(text: '2026-08-31');

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF0F172A),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: const Text('Mở Kỳ Kế Toán Mới', style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: startCtrl,
              style: const TextStyle(color: Colors.white, fontSize: 13),
              decoration: InputDecoration(
                labelText: 'Ngày bắt đầu (YYYY-MM-DD)',
                labelStyle: const TextStyle(color: Color(0xFF94A3B8), fontSize: 12),
                filled: true,
                fillColor: const Color(0xFF131D35),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: Color(0xFF1E293B))),
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: endCtrl,
              style: const TextStyle(color: Colors.white, fontSize: 13),
              decoration: InputDecoration(
                labelText: 'Ngày kết thúc (YYYY-MM-DD)',
                labelStyle: const TextStyle(color: Color(0xFF94A3B8), fontSize: 12),
                filled: true,
                fillColor: const Color(0xFF131D35),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: Color(0xFF1E293B))),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(), child: const Text('Hủy', style: TextStyle(color: Color(0xFF94A3B8)))),
          ElevatedButton(
            onPressed: () {
              controller.createAccountingPeriod(startCtrl.text.trim(), endCtrl.text.trim());
              Navigator.of(ctx).pop();
            },
            style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF00E5FF)),
            child: const Text('Tạo kỳ', style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) => Obx(() {
        final periods = controller.periods;

        return ListView(
          padding: const EdgeInsets.all(20),
          children: [
            // Header Bar
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: const Color(0xFF0F172A),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: const Color(0xFF1E293B)),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: const [
                        Text(
                          'QUẢN TRỊ KỲ KẾ TOÁN & KHÓA SỔ',
                          style: TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.bold, letterSpacing: 0.5),
                        ),
                        SizedBox(height: 4),
                        Text(
                          'Mở kỳ, theo dõi và khóa sổ kế toán định kỳ theo quy định',
                          style: TextStyle(color: Color(0xFF94A3B8), fontSize: 11),
                        ),
                      ],
                    ),
                  ),
                  ElevatedButton.icon(
                    onPressed: () => _openCreatePeriodDialog(context),
                    icon: const Icon(Icons.add_rounded, size: 14, color: Colors.black),
                    label: const Text('Mở kỳ mới', style: TextStyle(color: Colors.black, fontSize: 12, fontWeight: FontWeight.bold)),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF00E5FF),
                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // Content
            if (periods.isEmpty)
              Container(
                padding: const EdgeInsets.symmetric(vertical: 48, horizontal: 24),
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: const Color(0xFF0F172A),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: const Color(0xFF1E293B)),
                ),
                child: Column(
                  children: const [
                    Icon(Icons.date_range_rounded, size: 48, color: Color(0xFF475569)),
                    SizedBox(height: 14),
                    Text(
                      'Chưa có kỳ kế toán nào được thiết lập',
                      style: TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.w600),
                    ),
                    SizedBox(height: 6),
                    Text(
                      'Bấm "Mở kỳ mới" để thiết lập kỳ kế toán theo Tháng, Quý hoặc Năm.',
                      style: TextStyle(color: Color(0xFF64748B), fontSize: 12),
                    ),
                  ],
                ),
              )
            else
              ...periods.map((period) {
                final pMap = period is Map<String, dynamic> ? period : <String, dynamic>{};
                final id = pMap['id']?.toString() ?? '';
                final start = pMap['start_date']?.toString() ?? '';
                final end = pMap['end_date']?.toString() ?? '';
                final status = pMap['status']?.toString() ?? 'OPEN';
                final isOpen = status == 'OPEN';

                return Container(
                  margin: const EdgeInsets.only(bottom: 8),
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: const Color(0xFF0F172A),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: const Color(0xFF1E293B)),
                  ),
                  child: Row(
                    children: [
                      Icon(isOpen ? Icons.lock_open_rounded : Icons.lock_rounded, color: isOpen ? const Color(0xFF10B981) : const Color(0xFF64748B), size: 20),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text('Kỳ: $start đến $end', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13)),
                            const SizedBox(height: 2),
                            Text('Trạng thái: $status', style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 11)),
                          ],
                        ),
                      ),
                      ElevatedButton(
                        onPressed: () {
                          final newStatus = isOpen ? 'CLOSED' : 'OPEN';
                          controller.togglePeriodStatus(id, newStatus);
                        },
                        style: ElevatedButton.styleFrom(
                          backgroundColor: isOpen ? const Color(0xFFF59E0B) : const Color(0xFF10B981),
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                        ),
                        child: Text(isOpen ? 'Khóa sổ' : 'Mở lại kỳ', style: const TextStyle(color: Colors.black, fontSize: 11, fontWeight: FontWeight.bold)),
                      ),
                    ],
                  ),
                );
              }),
          ],
        );
      });
}
