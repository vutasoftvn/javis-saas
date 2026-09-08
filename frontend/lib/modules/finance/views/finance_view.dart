import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/finance_controller.dart';
import 'tabs/finance_tabs.dart';
import 'widgets/tt58_document_entry_dialog.dart';
import 'widgets/regime_transition_wizard_dialog.dart';
import '../../../core/localization/app_translations.dart';
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

  void _openTransitionWizard(BuildContext context, FinanceController controller) {
    final year = controller.selectedFiscalYear.value;
    final regime = controller.currentRegime['regulation_code'] ?? 'TT58_2026';
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (_) => RegimeTransitionWizardDialog(
        currentYear: year,
        currentRegime: regime,
        onCompleted: () => controller.loadRegimeData(),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<FinanceController>()) Get.put(FinanceController());
    final c = Get.find<FinanceController>();
    final isEn = Get.locale?.languageCode == 'en';

    return DefaultTabController(
      length: 8,
      child: Column(
        children: [
          CosaFloatingAppBar(
            title: L10nKey.financeTitle.tr,
            subtitle: L10nKey.financeSubtitle.tr,
            icon: Icons.account_balance_rounded,
            actions: [
              // Fiscal Year & Regime Indicator Switcher
              Obx(() {
                final year = c.selectedFiscalYear.value;
                final regCode = c.currentRegime['regulation_code'] ?? 'TT58';
                final isLocked = c.isYearLocked.value;
                final isTT199 = regCode.toString().contains('199');

                return Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: const Color(0xFF0F172A),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: const Color(0xFF1E293B)),
                  ),
                  child: Row(
                    children: [
                      Icon(
                        isLocked ? Icons.lock_outline : Icons.check_circle_outline,
                        size: 14,
                        color: isLocked ? Colors.amber : const Color(0xFF10B981),
                      ),
                      const SizedBox(width: 6),
                      Text(
                        '$year (${isTT199 ? "TT199 SME" : (isEn ? "TT58 Minimal" : "TT58 Tối giản")})',
                        style: TextStyle(
                          color: isLocked ? Colors.amber : Colors.white,
                          fontSize: 12,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ),
                );
              }),
              const SizedBox(width: 8),

              // Transition Button
              OutlinedButton.icon(
                onPressed: () => _openTransitionWizard(context, c),
                icon: const Icon(Icons.published_with_changes_rounded, size: 15, color: AppTheme.primary),
                label: Text(L10nKey.financeRegimeTransition.tr, style: const TextStyle(color: AppTheme.primary, fontSize: 12, fontWeight: FontWeight.bold)),
                style: OutlinedButton.styleFrom(
                  side: const BorderSide(color: AppTheme.primary),
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
              ),
              const SizedBox(width: 8),

              ElevatedButton.icon(
                onPressed: () => _openEntryDialog(context, c),
                icon: const Icon(Icons.add_rounded, size: 16, color: Colors.black),
                label: Text(L10nKey.financeRecordTransaction.tr, style: const TextStyle(color: Colors.black, fontSize: 12, fontWeight: FontWeight.bold)),
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
                  tooltip: L10nKey.commonRefresh.tr,
                  icon: const Icon(Icons.refresh_rounded, color: Colors.white, size: 20),
                  onPressed: () {
                    c.load();
                    c.loadRegimeData();
                  },
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Container(
            height: 38,
            padding: const EdgeInsets.all(3),
            decoration: BoxDecoration(
              color: AppTheme.surfaceDark,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: AppTheme.borderDark),
            ),
            child: TabBar(
              isScrollable: true,
              indicatorSize: TabBarIndicatorSize.tab,
              dividerColor: Colors.transparent,
              padding: EdgeInsets.zero,
              labelPadding: const EdgeInsets.symmetric(horizontal: 14),
              indicator: const BoxDecoration(
                borderRadius: BorderRadius.all(Radius.circular(7)),
                color: AppTheme.primary,
              ),
              labelColor: const Color(0xFF04070E),
              unselectedLabelColor: AppTheme.textMutedDark,
              labelStyle: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.bold),
              unselectedLabelStyle: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w500),
              tabs: [
                Tab(height: 32, text: isEn ? 'Overview' : 'Tổng quan'),
                Tab(height: 32, text: isEn ? 'Transactions' : 'Giao dịch'),
                Tab(height: 32, text: isEn ? 'Vouchers' : 'Chứng từ'),
                Tab(height: 32, text: isEn ? 'Ledgers' : 'Sổ sách'),
                Tab(height: 32, text: isEn ? 'Reports' : 'Báo cáo'),
                Tab(height: 32, text: isEn ? 'Fiscal Periods' : 'Kỳ kế toán'),
                Tab(height: 32, text: isEn ? 'Exceptions' : 'Ngoại lệ'),
                Tab(height: 32, text: isEn ? 'Settings' : 'Cài đặt'),
              ],
            ),
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

