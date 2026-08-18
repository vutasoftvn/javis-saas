import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../controllers/finance_controller.dart';
import '../widgets/finance_lite_summary_card.dart';
import '../widgets/tt58_financial_statement_card.dart';

class FinanceOverviewTab extends GetView<FinanceController> {
  const FinanceOverviewTab({super.key});

  @override
  Widget build(BuildContext context) => Obx(() {
        return ListView(
          padding: const EdgeInsets.all(20),
          children: [
            // 1. Founder Finance Lite Summary
            FinanceLiteSummaryCard(
              metrics: controller.founderLiteMetrics.value,
            ),
            const SizedBox(height: 20),
            // 2. Financial Statements B01 / B02 / B03 / F01 – ẩn banner cảnh báo
            TT58FinancialStatementCard(
              reportB01: controller.reportB01.value,
              reportB02: controller.reportB02.value,
              reportB03: controller.reportB03.value,
              reportF01: controller.reportF01.value,
              showBanner: false,
            ),
          ],
        );
      });
}
