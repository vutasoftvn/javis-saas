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
      TabBar(isScrollable: true, tabs: [Tab(text: 'Overview'), Tab(text: 'Transactions'), Tab(text: 'Documents'), Tab(text: 'Books'), Tab(text: 'Reports'), Tab(text: 'Periods'), Tab(text: 'Exceptions'), Tab(text: 'Settings')]),
      Expanded(child: TabBarView(children: [FinanceOverviewTab(), FinanceListTab(kind: 'transactions'), FinanceListTab(kind: 'documents'), FinancePlaceholderTab(label: 'S1-DNSN Books'), FinancePlaceholderTab(label: 'Reports'), FinanceListTab(kind: 'periods'), FinanceListTab(kind: 'exceptions'), FinancePlaceholderTab(label: 'Accounting Profile')]))
    ]));
  }
}
