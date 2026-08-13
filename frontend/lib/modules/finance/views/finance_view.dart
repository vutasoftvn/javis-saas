import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/finance_controller.dart';
import 'tabs/finance_tabs.dart';

class FinanceView extends StatelessWidget {
  const FinanceView({super.key});
  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<FinanceController>()) Get.put(FinanceController());
    return const DefaultTabController(length: 8, child: Column(children: [
      TabBar(isScrollable: true, tabs: [Tab(text: 'Tổng quan'), Tab(text: 'Giao dịch'), Tab(text: 'Chứng từ'), Tab(text: 'Sổ sách'), Tab(text: 'Báo cáo'), Tab(text: 'Kỳ kế toán'), Tab(text: 'Ngoại lệ'), Tab(text: 'Cài đặt')]),
      Expanded(child: TabBarView(children: [FinanceOverviewTab(), FinanceListTab(kind: 'transactions'), FinanceListTab(kind: 'documents'), FinancePlaceholderTab(label: 'Sổ sách S1-DNSN'), FinancePlaceholderTab(label: 'Báo cáo'), FinanceListTab(kind: 'periods'), FinanceListTab(kind: 'exceptions'), FinancePlaceholderTab(label: 'Hồ sơ kế toán')]))
    ]));
  }
}
