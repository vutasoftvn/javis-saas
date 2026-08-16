import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../controllers/finance_controller.dart';
import '../widgets/tt58_financial_statement_card.dart';

class FinanceReportsTab extends GetView<FinanceController> {
  const FinanceReportsTab({super.key});

  @override
  Widget build(BuildContext context) => Obx(() {
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
                          'BÁO CÁO TÀI CHÍNH THEO THÔNG TƯ 58/2026/TT-BTC',
                          style: TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.bold, letterSpacing: 0.5),
                        ),
                        SizedBox(height: 4),
                        Text(
                          'Hệ thống báo cáo tài chính chuẩn mực tự động đồng bộ theo từng chứng từ phát sinh',
                          style: TextStyle(color: Color(0xFF94A3B8), fontSize: 11),
                        ),
                      ],
                    ),
                  ),
                  ElevatedButton.icon(
                    onPressed: controller.loadTT58Data,
                    icon: const Icon(Icons.refresh_rounded, size: 14, color: Colors.black),
                    label: const Text('Cập nhật', style: TextStyle(color: Colors.black, fontSize: 12, fontWeight: FontWeight.bold)),
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

            // Financial Statements & Compliance Card
            TT58FinancialStatementCard(
              reportB01: controller.reportB01.value,
              reportB02: controller.reportB02.value,
              reportB03: controller.reportB03.value,
              reportF01: controller.reportF01.value,
            ),
          ],
        );
      });
}
