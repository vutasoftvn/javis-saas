import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../controllers/finance_controller.dart';

class FinanceExceptionsTab extends GetView<FinanceController> {
  const FinanceExceptionsTab({super.key});

  @override
  Widget build(BuildContext context) => Obx(() {
        final exceptions = controller.exceptions;

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
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: const [
                  Text(
                    'GIÁM SÁT SAI LỆCH & NGOẠI LỆ KẾ TOÁN',
                    style: TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.bold, letterSpacing: 0.5),
                  ),
                  SizedBox(height: 4),
                  Text(
                    'Tự động phát hiện chênh lệch số dư, chứng từ mâu thuẫn hoặc vi phạm quy tắc kế toán',
                    style: TextStyle(color: Color(0xFF94A3B8), fontSize: 11),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // Content
            if (exceptions.isEmpty)
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
                    Icon(Icons.verified_user_rounded, size: 48, color: Color(0xFF10B981)),
                    SizedBox(height: 14),
                    Text(
                      'Không phát hiện ngoại lệ hoặc sai lệch',
                      style: TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.w600),
                    ),
                    SizedBox(height: 6),
                    Text(
                      'Hệ thống sổ sách, chứng từ và số dư hiện tại hoàn toàn hợp lệ và cân đối 100%.',
                      style: TextStyle(color: Color(0xFF64748B), fontSize: 12),
                    ),
                  ],
                ),
              )
            else
              ...exceptions.map((ex) {
                final exMap = ex is Map<String, dynamic> ? ex : <String, dynamic>{};
                final title = exMap['title']?.toString() ?? 'Ngoại lệ kế toán';
                final desc = exMap['description']?.toString() ?? '$ex';

                return Container(
                  margin: const EdgeInsets.only(bottom: 8),
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: const Color(0xFF0F172A),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: const Color(0xFFEF4444).withValues(alpha: 0.3)),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.warning_amber_rounded, color: Color(0xFFEF4444), size: 20),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(title, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13)),
                            const SizedBox(height: 2),
                            Text(desc, style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 11)),
                          ],
                        ),
                      ),
                    ],
                  ),
                );
              }),
          ],
        );
      });
}
