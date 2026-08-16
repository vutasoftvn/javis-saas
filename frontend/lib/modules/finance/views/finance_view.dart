import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/finance_controller.dart';
import 'tabs/finance_tabs.dart';
import 'widgets/tt58_document_entry_dialog.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/floating_app_bar.dart';

class FinanceView extends StatelessWidget {
  const FinanceView({super.key});

  void _openEntryDialog(BuildContext context, FinanceController controller) {
    showDialog(
      context: context,
      builder: (_) => TT58DocumentEntryDialog(
        onSubmit: ({
          required documentNo,
          required documentType,
          required amount,
          required direction,
          required description,
          category = 'DOANH_THU',
        }) =>
            controller.createAndPostDocument(
          documentNo: documentNo,
          documentType: documentType,
          amount: amount,
          direction: direction,
          description: description,
          category: category,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<FinanceController>()) Get.put(FinanceController());
    final c = Get.find<FinanceController>();

    return DefaultTabController(
      length: 8,
      child: Column(
        children: [
          JavisFloatingAppBar(
            title: 'Quản lý Tài chính & Kế toán',
            subtitle: 'Theo dõi giao dịch, chứng từ, sổ sách và báo cáo tài chính doanh nghiệp.',
            icon: Icons.account_balance_rounded,
            actions: [
              ElevatedButton.icon(
                onPressed: () => _openEntryDialog(context, c),
                icon: const Icon(Icons.add_rounded, size: 16, color: Colors.black),
                label: const Text('Lập chứng từ', style: TextStyle(color: Colors.black, fontSize: 12, fontWeight: FontWeight.bold)),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF00E5FF),
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
              ),
              const SizedBox(width: 8),
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
                FinanceTransactionsTab(),
                FinanceDocumentsTab(),
                FinanceBooksTab(),
                FinanceReportsTab(),
                FinancePeriodsTab(),
                FinanceExceptionsTab(),
                FinanceProfileSettingsTab(),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

