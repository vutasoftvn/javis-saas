import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../controllers/finance_controller.dart';

class FinanceOverviewTab extends GetView<FinanceController> {
  const FinanceOverviewTab({super.key});
  @override
  Widget build(BuildContext context) => Obx(() => ListView(
    padding: const EdgeInsets.all(20),
    children: controller.overview.entries
        .map((entry) => ListTile(title: Text(entry.key), trailing: Text('${entry.value}')))
        .toList(),
  ));
}

class FinanceListTab extends GetView<FinanceController> {
  const FinanceListTab({super.key, required this.kind}); final String kind;
  @override Widget build(BuildContext context) => Obx(() { final rows = switch(kind) {'transactions' => controller.transactions, 'documents' => controller.documents, 'periods' => controller.periods, _ => controller.exceptions}; return ListView.builder(itemCount: rows.length, itemBuilder: (_, i) => ListTile(title: Text('${rows[i]}'))); });
}

class FinancePlaceholderTab extends StatelessWidget {
  const FinancePlaceholderTab({super.key, required this.label}); final String label;
  @override Widget build(BuildContext context) => Center(child: Text(label));
}
