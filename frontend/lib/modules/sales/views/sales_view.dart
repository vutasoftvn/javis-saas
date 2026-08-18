import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/sales_controller.dart';
import 'sales_today_view.dart';
import 'customer_view.dart';
import 'widgets/revenue_funnel_summary_card.dart';
import 'widgets/deal_kanban_board.dart';
import 'widgets/lead_scoring_list.dart';
import 'widgets/ai_outreach_composer_dialog.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/floating_app_bar.dart';

class SalesView extends StatelessWidget {
  const SalesView({super.key});

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<SalesController>()) {
      Get.put(SalesController());
    }
    final c = Get.find<SalesController>();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        JavisFloatingAppBar(
          title: 'Cỗ Máy Doanh Thu & CRM',
          subtitle: 'Vòng lặp khép kín: Khám phá lead, AI scoring, quản lý Pipeline và gửi thư tiếp cận.',
          icon: Icons.point_of_sale_rounded,
          actions: [
            Container(
              decoration: const BoxDecoration(
                color: AppTheme.primary,
                shape: BoxShape.circle,
              ),
              child: IconButton(
                tooltip: 'Tải lại toàn bộ',
                icon: const Icon(Icons.refresh_rounded, color: Colors.white, size: 20),
                onPressed: c.loadAll,
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        // Top Funnel Summary Card
        Obx(() {
          final p = c.pipeline.value;
          final summary = p?['summary'] as Map<String, dynamic>? ?? {};
          final totalVal = (summary['total_value'] as num?)?.toDouble() ?? 0.0;
          final weightedVal = (summary['weighted_value'] as num?)?.toDouble() ?? 0.0;
          final totalDeals = (summary['total_deals'] as num?)?.toInt() ?? 0;

          final qualifiedCount = c.leads.where((l) => l['qualification_status'] == 'QUALIFIED').length;

          return Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: RevenueFunnelSummaryCard(
              totalLeads: c.leads.length,
              qualifiedLeads: qualifiedCount,
              activeDeals: totalDeals,
              pipelineValue: totalVal,
              weightedValue: weightedVal,
            ),
          );
        }),
        const SizedBox(height: 12),
        // Standard Unified Tab Bar
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Container(
            height: 38,
            padding: const EdgeInsets.all(3),
            decoration: BoxDecoration(
              color: AppTheme.surfaceDark,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: AppTheme.borderDark),
            ),
            child: Obx(() {
              final activeTab = c.currentTab.value;
              final tabs = [
                {'index': 0, 'label': 'Pipeline Kanban', 'icon': Icons.view_kanban_outlined},
                {'index': 1, 'label': 'Smart Leads & AI Scoring', 'icon': Icons.auto_awesome_rounded},
                {'index': 2, 'label': 'Khách hàng & Tài khoản', 'icon': Icons.business_rounded},
                {'index': 3, 'label': 'Doanh số hôm nay', 'icon': Icons.today_rounded},
              ];

              return Row(
                children: tabs.map((t) {
                  final idx = t['index'] as int;
                  final isSelected = activeTab == idx;

                  return Expanded(
                    child: InkWell(
                      onTap: () => c.setTab(idx),
                      borderRadius: BorderRadius.circular(7),
                      child: Container(
                        height: 32,
                        alignment: Alignment.center,
                        decoration: BoxDecoration(
                          color: isSelected ? AppTheme.primary : Colors.transparent,
                          borderRadius: BorderRadius.circular(7),
                        ),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(
                              t['icon'] as IconData,
                              size: 14,
                              color: isSelected ? const Color(0xFF04070E) : AppTheme.textMutedDark,
                            ),
                            const SizedBox(width: 8),
                            Flexible(
                              child: Text(
                                t['label'] as String,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: TextStyle(
                                  fontSize: 12.5,
                                  fontWeight: isSelected ? FontWeight.bold : FontWeight.w500,
                                  color: isSelected ? const Color(0xFF04070E) : AppTheme.textMutedDark,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  );
                }).toList(),
              );
            }),
          ),
        ),
        const SizedBox(height: 12),
        Expanded(
          child: Obx(() {
            if (c.isLoading.value && c.pipeline.value == null) {
              return const Center(child: CircularProgressIndicator());
            }

            switch (c.currentTab.value) {
              case 0:
                final stages = c.pipeline.value?['stages'] as List<dynamic>? ?? [];
                return Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  child: DealKanbanBoard(
                    stages: stages,
                    onMoveStage: (dealId, newStage) => c.updateDealStage(dealId, newStage),
                  ),
                );
              case 1:
                return SingleChildScrollView(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  child: LeadScoringList(
                    leads: c.leads,
                    onScoreLead: (leadId) => c.scoreLead(leadId),
                    onConvertToDeal: (leadId, name, company) => c.convertLeadToOpportunity(leadId, name, company),
                    onComposeOutreach: (leadId, name, company) {
                      showDialog(
                        context: context,
                        builder: (ctx) => AiOutreachComposerDialog(
                          leadId: leadId,
                          leadName: name,
                          company: company,
                          onGenerateOutreach: c.generateOutreach,
                        ),
                      );
                    },
                  ),
                );
              case 2:
                return const CustomerView();
              case 3:
              default:
                return const SalesTodayView();
            }
          }),
        ),
      ],
    );
  }
}
