import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/sales_controller.dart';
import 'sales_today_view.dart';
import 'funnel_view.dart';
import 'customer_view.dart';

class SalesView extends StatelessWidget {
  const SalesView({super.key});

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<SalesController>()) {
      Get.put(SalesController());
    }
    final c = Get.find<SalesController>();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Quản lý Bán hàng & Doanh thu'),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(48),
          child: Obx(() => SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: [
                    _buildTabButton(context, c, index: 0, label: 'Doanh số hôm nay'),
                    _buildTabButton(context, c, index: 1, label: 'Phễu bán hàng'),
                    _buildTabButton(context, c, index: 2, label: 'Khách hàng'),
                    _buildTabButton(context, c, index: 3, label: 'Manh mối & Tài khoản'),
                  ],
                ),
              )),
        ),
      ),
      body: Obx(() {
        switch (c.currentTab.value) {
          case 0:
            return const SalesTodayView();
          case 1:
            return const FunnelView();
          case 2:
            return const CustomerView();
          case 3:
          default:
            return _buildLeadsAndAccountsView(context, c);
        }
      }),
    );
  }

  Widget _buildTabButton(BuildContext context, SalesController c, {required int index, required String label}) {
    final isSelected = c.currentTab.value == index;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      child: ChoiceChip(
        label: Text(label),
        selected: isSelected,
        onSelected: (_) => c.setTab(index),
      ),
    );
  }

  Widget _buildLeadsAndAccountsView(BuildContext context, SalesController c) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text('Manh mối (${c.leads.length})', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
            IconButton(icon: const Icon(Icons.refresh), onPressed: c.loadAll),
          ],
        ),
        const SizedBox(height: 8),
        if (c.leads.isEmpty)
          const Padding(
            padding: EdgeInsets.all(16),
            child: Text('Không tìm thấy manh mối nào.'),
          )
        else
          ...c.leads.map((e) => Card(
                child: ListTile(
                  title: Text('${e['name']}', style: const TextStyle(fontWeight: FontWeight.bold)),
                  subtitle: Text('Giai đoạn: ${e['stage']} • Công ty: ${e['company'] ?? 'N/A'}'),
                  trailing: Text('\$${e['value'] ?? 0.0}'),
                ),
              )),
        const SizedBox(height: 20),
        Text('Tài khoản (${c.accounts.length})', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
        const SizedBox(height: 8),
        if (c.accounts.isEmpty)
          const Padding(
            padding: EdgeInsets.all(16),
            child: Text('Không tìm thấy tài khoản nào.'),
          )
        else
          ...c.accounts.map((acc) => Card(
                child: ListTile(
                  title: Text('${acc['name']}', style: const TextStyle(fontWeight: FontWeight.bold)),
                  subtitle: Text('Tên miền: ${acc['domain'] ?? 'N/A'} • Trạng thái: ${acc['lifecycle_status']}'),
                ),
              )),
      ],
    );
  }
}
