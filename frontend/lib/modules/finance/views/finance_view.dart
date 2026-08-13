import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/finance_controller.dart';
import 'tabs/finance_tabs.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/floating_app_bar.dart';

class FinanceView extends StatelessWidget {
  const FinanceView({super.key});

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<FinanceController>()) Get.put(FinanceController());
    final c = Get.find<FinanceController>();

    return DefaultTabController(
      length: 8,
      child: Padding(
        padding: const EdgeInsets.all(20.0),
        child: Column(
          children: [
            JavisFloatingAppBar(
              title: 'Quản lý Tài chính & Kế toán',
              subtitle: 'Theo dõi giao dịch, chứng từ, sổ sách và báo cáo tài chính doanh nghiệp.',
              icon: Icons.account_balance_rounded,
              actions: [
                Container(
                  decoration: const BoxDecoration(
                    color: AppTheme.primary,
                    shape: BoxShape.circle,
                  ),
                  child: IconButton(
                    tooltip: 'Tải lại',
                    icon: const Icon(Icons.refresh_rounded, color: Colors.white, size: 20),
                    onPressed: c.load,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            const TabBar(
              isScrollable: true,
              tabs: [
                Tab(text: 'Tổng quan'),
                Tab(text: 'Giao dịch'),
                Tab(text: 'Chứng từ'),
                Tab(text: 'Sổ sách'),
                Tab(text: 'Báo cáo'),
                Tab(text: 'Kỳ kế toán'),
                Tab(text: 'Ngoại lệ'),
                Tab(text: 'Cài đặt'),
              ],
            ),
            const SizedBox(height: 12),
            const Expanded(
              child: TabBarView(
                children: [
                  FinanceOverviewTab(),
                  FinanceListTab(kind: 'transactions'),
                  FinanceListTab(kind: 'documents'),
                  FinanceListTab(kind: 'books'),
                  FinanceListTab(kind: 'reports'),
                  FinanceListTab(kind: 'periods'),
                  FinanceListTab(kind: 'exceptions'),
                  FinanceProfileTab(),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

