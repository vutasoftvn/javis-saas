import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/ai_team_controller.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/floating_app_bar.dart';

class AiTeamView extends StatelessWidget {
  const AiTeamView({super.key});

  Color _getRiskColor(String? risk) {
    switch (risk?.toUpperCase()) {
      case 'CRITICAL':
        return AppTheme.error;
      case 'HIGH':
        return AppTheme.warning;
      default:
        return AppTheme.info;
    }
  }

  Color _getLivenessColor(String? health) {
    switch (health?.toUpperCase()) {
      case 'HEALTHY':
        return AppTheme.success;
      case 'DEGRADED':
        return AppTheme.warning;
      case 'STALLED':
      case 'OFFLINE':
        return AppTheme.error;
      default:
        return AppTheme.preview;
    }
  }

  String _translateDepartment(String? dept) {
    switch (dept?.toLowerCase()) {
      case 'executive':
        return 'Điều hành Chiến lược';
      case 'finance':
        return 'Tài chính & Kế toán';
      case 'growth':
      case 'marketing':
        return 'Marketing & Tăng trưởng';
      case 'sales':
        return 'Kinh doanh & Bán hàng';
      case 'tech':
      case 'engineering':
      case 'product':
        return 'Kỹ thuật & Công nghệ';
      case 'operations':
      case 'legal':
        return 'Vận hành & Pháp lý';
      default:
        return dept ?? 'Chung';
    }
  }

  IconData _getDepartmentIcon(String? dept) {
    switch (dept?.toLowerCase()) {
      case 'executive':
        return Icons.military_tech_rounded;
      case 'finance':
        return Icons.account_balance_wallet_rounded;
      case 'growth':
      case 'marketing':
        return Icons.campaign_rounded;
      case 'sales':
        return Icons.point_of_sale_rounded;
      case 'tech':
      case 'engineering':
      case 'product':
        return Icons.code_rounded;
      case 'operations':
      case 'legal':
        return Icons.gavel_rounded;
      default:
        return Icons.smart_toy_rounded;
    }
  }

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<AiTeamController>()) Get.put(AiTeamController());
    final controller = Get.find<AiTeamController>();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        JavisFloatingAppBar(
          title: 'Tổng quan Đội ngũ AI (Workforce Control Plane)',
          subtitle: 'Giám sát 12 AI Agents, phê duyệt rủi ro, kiểm soát chi phí & sản phẩm bàn giao',
          icon: Icons.groups_rounded,
          actions: [
            Obx(() => IconButton(
              icon: controller.loading.value
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2, color: AppTheme.primary),
                    )
                  : const Icon(Icons.refresh, color: AppTheme.primary),
              tooltip: 'Làm mới toàn bộ dữ liệu',
              onPressed: controller.loading.value ? null : controller.load,
            )),
          ],
        ),
        const SizedBox(height: 14),
        Expanded(
          child: Obx(() {
            if (controller.loading.value && controller.dashboardSummary.value == null) {
              return const Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    CircularProgressIndicator(color: AppTheme.primary),
                    SizedBox(height: 16),
                    Text('Đang đồng bộ Control Plane...', style: TextStyle(color: AppTheme.textMutedDark)),
                  ],
                ),
              );
            }

            final summary = controller.dashboardSummary.value ?? {};
            final financials = summary['financials'] as Map<String, dynamic>? ?? {};
            final governance = summary['governance'] as Map<String, dynamic>? ?? {};
            final workforce = summary['workforce'] as Map<String, dynamic>? ?? {};
            final health = workforce['health_status'] as Map<String, dynamic>? ?? {};

            return RefreshIndicator(
              onRefresh: controller.load,
              color: AppTheme.primary,
              backgroundColor: AppTheme.surfaceDark,
              child: SingleChildScrollView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.only(bottom: 32),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    // 1. KPI Stats Row
                    _buildKpiRow(context, workforce, health, financials, governance),
                    const SizedBox(height: 18),

                    // 2. Pending Approval Banner (If any)
                    if (controller.pendingApprovals.isNotEmpty) ...[
                      _buildApprovalBanner(context, controller),
                      const SizedBox(height: 18),
                    ],

                    // 3. Department Filters
                    _buildDepartmentFilterBar(controller),
                    const SizedBox(height: 14),

                    // 4. Workforce Agents Grid (12 Agents)
                    _buildAgentsGrid(context, controller),
                    const SizedBox(height: 24),

                    // 5. Work Products Section
                    if (controller.workProducts.isNotEmpty)
                      _buildWorkProductsSection(context, controller),
                  ],
                ),
              ),
            );
          }),
        ),
      ],
    );
  }

  Widget _buildKpiRow(
    BuildContext context,
    Map<String, dynamic> workforce,
    Map<String, dynamic> health,
    Map<String, dynamic> financials,
    Map<String, dynamic> governance,
  ) {
    final totalAgents = workforce['total_agents'] ?? 12;
    final healthyAgents = health['HEALTHY'] ?? totalAgents;
    final totalUsd = (financials['total_cost_usd'] ?? 0.0).toStringAsFixed(4);
    final totalVnd = (financials['total_cost_vnd'] ?? 0.0);
    final budgetLimit = financials['total_budget_limit_usd'] ?? 100.0;
    final budgetSpent = financials['total_budget_spent_usd'] ?? 0.0;
    final budgetPct = (financials['budget_consumption_pct'] ?? (budgetLimit > 0 ? (budgetSpent / budgetLimit * 100) : 0.0)).toStringAsFixed(1);
    final pendingCount = governance['pending_approvals_total'] ?? 0;
    final criticalCount = governance['critical_risk_count'] ?? 0;

    return LayoutBuilder(
      builder: (context, constraints) {
        final crossAxisCount = constraints.maxWidth > 1100 ? 4 : (constraints.maxWidth > 650 ? 2 : 1);
        return GridView.count(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          crossAxisCount: crossAxisCount,
          childAspectRatio: constraints.maxWidth > 1100 ? 2.2 : 2.5,
          crossAxisSpacing: 14,
          mainAxisSpacing: 14,
          children: [
            _buildStatCard(
              title: 'Lực lượng AI (Workforce)',
              value: '$totalAgents Nhân sự AI',
              subtitle: '🟢 $healthyAgents Sẵn sàng · ${health['STALLED'] ?? 0} Bị nghẽn',
              icon: Icons.badge_rounded,
              accentColor: AppTheme.primary,
            ),
            _buildStatCard(
              title: 'Chi phí Token (Cost Ledger)',
              value: '\$$totalUsd',
              subtitle: '≈ ${(totalVnd as num).toStringAsFixed(0)} ₫ (Tỷ giá 25,400)',
              icon: Icons.payments_rounded,
              accentColor: const Color(0xFF38BDF8),
            ),
            _buildStatCard(
              title: 'Hạn mức Ngân sách 12-Tuần',
              value: '$budgetPct%',
              subtitle: 'Đã chi: \$$budgetSpent / \$$budgetLimit',
              icon: Icons.account_balance_wallet_rounded,
              accentColor: (budgetSpent / (budgetLimit > 0 ? budgetLimit : 1.0) > 0.8) ? AppTheme.warning : AppTheme.success,
            ),
            _buildStatCard(
              title: 'Phiếu Phê duyệt (Approval Inbox)',
              value: '$pendingCount Cần duyệt',
              subtitle: criticalCount > 0 ? '🔴 $criticalCount Rủi ro Nghiêm trọng' : 'Tất cả tác vụ trong tầm kiểm soát',
              icon: Icons.fact_check_rounded,
              accentColor: criticalCount > 0 ? AppTheme.error : (pendingCount > 0 ? AppTheme.warning : AppTheme.success),
            ),
          ],
        );
      },
    );
  }

  Widget _buildStatCard({
    required String title,
    required String value,
    required String subtitle,
    required IconData icon,
    required Color accentColor,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDark,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppTheme.borderDark),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.2),
            blurRadius: 8,
            offset: const Offset(0, 3),
          ),
        ],
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: accentColor.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: accentColor.withValues(alpha: 0.25)),
            ),
            child: Icon(icon, color: accentColor, size: 24),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  title,
                  style: const TextStyle(fontSize: 12, color: AppTheme.textMutedDark, fontWeight: FontWeight.w500),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 4),
                Text(
                  value,
                  style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppTheme.textDark),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 2),
                Text(
                  subtitle,
                  style: TextStyle(fontSize: 11, color: accentColor, fontWeight: FontWeight.w500),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildApprovalBanner(BuildContext context, AiTeamController controller) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDark,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppTheme.warning.withValues(alpha: 0.6), width: 1.5),
        boxShadow: [
          BoxShadow(
            color: AppTheme.warning.withValues(alpha: 0.1),
            blurRadius: 16,
            spreadRadius: 1,
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.gavel_rounded, color: AppTheme.warning, size: 20),
              const SizedBox(width: 8),
              const Text(
                'Yêu cầu Phê duyệt từ Human Lead / Founder',
                style: TextStyle(fontWeight: FontWeight.bold, color: AppTheme.textDark, fontSize: 15),
              ),
              const Spacer(),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: AppTheme.warning.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  '${controller.pendingApprovals.length} phiếu chờ',
                  style: const TextStyle(fontSize: 12, color: AppTheme.warning, fontWeight: FontWeight.bold),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          ListView.separated(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: controller.pendingApprovals.length,
            separatorBuilder: (context, index) => const Divider(color: AppTheme.borderDark, height: 16),
            itemBuilder: (context, index) {
              final item = controller.pendingApprovals[index];
              final approvalId = item['id'] as int? ?? 0;
              final risk = item['risk_level']?.toString() ?? 'HIGH';
              final action = item['action']?.toString() ?? 'Tác vụ rủi ro cao';
              final reason = item['reason']?.toString() ?? 'Cần Founder xác nhận quyền thực thi';

              return Row(
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
                    decoration: BoxDecoration(
                      color: _getRiskColor(risk).withValues(alpha: 0.2),
                      borderRadius: BorderRadius.circular(4),
                      border: Border.all(color: _getRiskColor(risk)),
                    ),
                    child: Text(
                      risk,
                      style: TextStyle(color: _getRiskColor(risk), fontSize: 10, fontWeight: FontWeight.bold),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(action, style: const TextStyle(fontWeight: FontWeight.w600, color: AppTheme.textDark, fontSize: 13)),
                        Text(reason, style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 11)),
                      ],
                    ),
                  ),
                  const SizedBox(width: 8),
                  OutlinedButton.icon(
                    style: OutlinedButton.styleFrom(
                      foregroundColor: AppTheme.error,
                      side: const BorderSide(color: AppTheme.error),
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                      minimumSize: Size.zero,
                    ),
                    onPressed: () => controller.rejectRequest(approvalId),
                    icon: const Icon(Icons.close, size: 14),
                    label: const Text('Từ chối', style: TextStyle(fontSize: 12)),
                  ),
                  const SizedBox(width: 8),
                  ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppTheme.success,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                      minimumSize: Size.zero,
                    ),
                    onPressed: () => controller.approveRequest(approvalId),
                    icon: const Icon(Icons.check, size: 14),
                    label: const Text('Phê duyệt', style: TextStyle(fontSize: 12)),
                  ),
                ],
              );
            },
          ),
        ],
      ),
    );
  }

  Widget _buildDepartmentFilterBar(AiTeamController controller) {
    final depts = [
      {'key': 'ALL', 'label': 'Tất cả 12 Agents'},
      {'key': 'EXECUTIVE', 'label': 'Điều hành'},
      {'key': 'FINANCE', 'label': 'Tài chính'},
      {'key': 'GROWTH', 'label': 'Marketing & Growth'},
      {'key': 'SALES', 'label': 'Sales & CRM'},
      {'key': 'TECH', 'label': 'Kỹ thuật & Code'},
      {'key': 'OPERATIONS', 'label': 'Pháp lý & Vận hành'},
    ];

    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        children: depts.map((d) {
          final isSelected = controller.selectedDepartment.value == d['key'];
          return Padding(
            padding: const EdgeInsets.only(right: 8),
            child: ChoiceChip(
              label: Text(d['label']!),
              selected: isSelected,
              onSelected: (_) => controller.selectedDepartment.value = d['key']!,
              selectedColor: AppTheme.primary.withValues(alpha: 0.2),
              backgroundColor: AppTheme.surfaceDark,
              labelStyle: TextStyle(
                color: isSelected ? AppTheme.primary : AppTheme.textMutedDark,
                fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                fontSize: 12,
              ),
              side: BorderSide(color: isSelected ? AppTheme.primary : AppTheme.borderDark),
            ),
          );
        }).toList(),
      ),
    );
  }

  Widget _buildAgentsGrid(BuildContext context, AiTeamController controller) {
    final agentsList = controller.filteredAgents;

    if (agentsList.isEmpty) {
      return Container(
        padding: const EdgeInsets.all(32),
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: AppTheme.surfaceDark,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: AppTheme.borderDark),
        ),
        child: const Text('Không có Agent nào thuộc phòng ban này.', style: TextStyle(color: AppTheme.textMutedDark)),
      );
    }

    return LayoutBuilder(
      builder: (context, constraints) {
        final crossAxisCount = constraints.maxWidth > 1200 ? 3 : (constraints.maxWidth > 750 ? 2 : 1);

        return GridView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: crossAxisCount,
            childAspectRatio: 1.65,
            crossAxisSpacing: 14,
            mainAxisSpacing: 14,
          ),
          itemCount: agentsList.length,
          itemBuilder: (context, index) {
            final agent = agentsList[index];
            final name = agent['name'] ?? agent['key'] ?? 'AI Agent';
            final role = agent['role'] ?? 'Specialist';
            final dept = agent['department'] ?? 'general';
            final level = agent['level'] ?? 'SPECIALIST';
            final provider = agent['runtime_provider'] ?? 'gemini';
            final model = agent['model_name'] ?? 'default-model';
            final skills = agent['skills'] as List? ?? [];
            final health = agent['health_status']?.toString() ?? 'HEALTHY';

            return Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppTheme.surfaceDark,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: AppTheme.borderDark),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: 0.15),
                    blurRadius: 6,
                    offset: const Offset(0, 2),
                  ),
                ],
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Agent Header
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(8),
                        decoration: BoxDecoration(
                          color: AppTheme.primary.withValues(alpha: 0.1),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Icon(_getDepartmentIcon(dept), color: AppTheme.primary, size: 20),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              name,
                              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: AppTheme.textDark),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                            Text(
                              role,
                              style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 11),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ],
                        ),
                      ),
                      // Level chip
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: level == 'LEAD' ? const Color(0xFF8B5CF6).withValues(alpha: 0.2) : AppTheme.surfaceDarkElevated,
                          borderRadius: BorderRadius.circular(4),
                          border: Border.all(
                            color: level == 'LEAD' ? const Color(0xFF8B5CF6) : AppTheme.borderDark,
                          ),
                        ),
                        child: Text(
                          level,
                          style: TextStyle(
                            fontSize: 9,
                            fontWeight: FontWeight.bold,
                            color: level == 'LEAD' ? const Color(0xFFA78BFA) : AppTheme.textMutedDark,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),

                  // Department & Heartbeat Liveness
                  Row(
                    children: [
                      Text(
                        _translateDepartment(dept),
                        style: const TextStyle(color: AppTheme.textDimDark, fontSize: 11, fontWeight: FontWeight.w500),
                      ),
                      const Spacer(),
                      Container(
                        width: 7,
                        height: 7,
                        decoration: BoxDecoration(
                          color: _getLivenessColor(health),
                          shape: BoxShape.circle,
                        ),
                      ),
                      const SizedBox(width: 4),
                      Text(
                        health,
                        style: TextStyle(fontSize: 10, color: _getLivenessColor(health), fontWeight: FontWeight.bold),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),

                  // Runtime engine chip
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: AppTheme.surfaceDarkLighter,
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: AppTheme.borderDark),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(Icons.bolt_rounded, size: 13, color: AppTheme.primary),
                        const SizedBox(width: 4),
                        Text(
                          '$provider · $model',
                          style: const TextStyle(fontSize: 11, color: AppTheme.textMutedDark),
                        ),
                      ],
                    ),
                  ),
                  const Spacer(),

                  // Skills & status bottom row
                  Row(
                    children: [
                      const Icon(Icons.psychology_outlined, size: 14, color: AppTheme.textDimDark),
                      const SizedBox(width: 4),
                      Text(
                        '${skills.length} Kỹ năng cấu hình',
                        style: const TextStyle(fontSize: 11, color: AppTheme.textMutedDark),
                      ),
                      const Spacer(),
                      const Text(
                        'Sẵn sàng',
                        style: TextStyle(fontSize: 11, color: AppTheme.success, fontWeight: FontWeight.w600),
                      ),
                    ],
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }

  Widget _buildWorkProductsSection(BuildContext context, AiTeamController controller) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDark,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppTheme.borderDark),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.inventory_2_rounded, color: AppTheme.primary, size: 20),
              const SizedBox(width: 8),
              const Text(
                'Sản Phẩm Bàn Giao Gần Đây (Work Products)',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15, color: AppTheme.textDark),
              ),
              const Spacer(),
              Text(
                '${controller.workProducts.length} sản phẩm',
                style: const TextStyle(fontSize: 12, color: AppTheme.textMutedDark),
              ),
            ],
          ),
          const SizedBox(height: 12),
          ListView.separated(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: controller.workProducts.take(5).length,
            separatorBuilder: (context, index) => const Divider(color: AppTheme.borderDark, height: 16),
            itemBuilder: (context, index) {
              final wp = controller.workProducts[index];
              final wpId = wp['id'] as int? ?? 0;
              final title = wp['title'] ?? 'Sản phẩm bàn giao';
              final type = wp['product_type'] ?? 'DOCUMENT';
              final status = wp['status'] ?? 'DRAFT';
              final summary = wp['executive_summary'] ?? 'Không có tóm tắt.';
              final isDraft = status == 'DRAFT';

              return Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: AppTheme.surfaceDarkLighter,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: const Icon(Icons.description_outlined, size: 18, color: AppTheme.primary),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Text(
                              title,
                              style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13, color: AppTheme.textDark),
                            ),
                            const SizedBox(width: 8),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                              decoration: BoxDecoration(
                                color: isDraft ? AppTheme.warning.withValues(alpha: 0.15) : AppTheme.success.withValues(alpha: 0.15),
                                borderRadius: BorderRadius.circular(4),
                              ),
                              child: Text(
                                status,
                                style: TextStyle(
                                  fontSize: 10,
                                  fontWeight: FontWeight.bold,
                                  color: isDraft ? AppTheme.warning : AppTheme.success,
                                ),
                              ),
                            ),
                          ],
                        ),
                        Text(
                          'Loại: $type · $summary',
                          style: const TextStyle(fontSize: 11, color: AppTheme.textMutedDark),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ],
                    ),
                  ),
                  if (isDraft) ...[
                    const SizedBox(width: 8),
                    ElevatedButton.icon(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppTheme.primary,
                        foregroundColor: Colors.black,
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                        minimumSize: Size.zero,
                      ),
                      onPressed: () => controller.acceptProduct(wpId),
                      icon: const Icon(Icons.check_circle_outline, size: 14),
                      label: const Text('Nghiệm thu', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold)),
                    ),
                  ],
                ],
              );
            },
          ),
        ],
      ),
    );
  }
}
