import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/network/api_result.dart';
import '../controllers/organization_controller.dart';
import '../models/organization_api_models.dart';
import '../../../core/localization/app_translations.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/app_toast.dart';
import '../../../core/widgets/floating_app_bar.dart';

class OrganizationView extends GetView<OrganizationController> {
  const OrganizationView({super.key});

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<OrganizationController>()) {
      Get.put(OrganizationController());
    }
    final isEn = Get.locale?.languageCode == 'en';

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Header
        CosaFloatingAppBar(
              title: L10nKey.orgTitle.tr,
              subtitle: L10nKey.orgSubtitle.tr,
              icon: Icons.corporate_fare_rounded,
              actions: [
                ElevatedButton.icon(
                  onPressed: () => _showPlaceAiDialog(context),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.primary.withValues(alpha: 0.15),
                    foregroundColor: AppTheme.primary,
                    side: const BorderSide(color: AppTheme.primary),
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
                  ),
                  icon: const Icon(Icons.person_add_rounded, size: 18),
                  label: Text(L10nKey.orgHireAiButton.tr, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                ),
                const SizedBox(width: 10),
                Container(
                  decoration: const BoxDecoration(
                    color: AppTheme.primary,
                    shape: BoxShape.circle,
                  ),
                  child: IconButton(
                    tooltip: L10nKey.commonRefresh.tr,
                    icon: const Icon(Icons.refresh_rounded, color: Colors.white, size: 20),
                    onPressed: controller.loadOrganizationData,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),

            // Tab Bar
            Container(
              height: 38,
              padding: const EdgeInsets.all(3),
              decoration: BoxDecoration(
                color: AppTheme.surfaceDark,
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: AppTheme.borderDark),
              ),
              child: TabBar(
                controller: controller.tabController,
                indicatorSize: TabBarIndicatorSize.tab,
                dividerColor: Colors.transparent,
                padding: EdgeInsets.zero,
                labelPadding: EdgeInsets.zero,
                indicator: BoxDecoration(
                  borderRadius: BorderRadius.circular(7),
                  color: AppTheme.primary,
                ),
                labelColor: const Color(0xFF04070E),
                unselectedLabelColor: AppTheme.textMutedDark,
                tabs: [
                  Tab(
                    height: 32,
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(Icons.dashboard_customize_outlined, size: 15),
                        const SizedBox(width: 8),
                        Text(isEn ? 'Overview' : 'Tổng quan', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12.5)),
                      ],
                    ),
                  ),
                  Tab(
                    height: 32,
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(Icons.account_tree_outlined, size: 15),
                        const SizedBox(width: 8),
                        Text(isEn ? 'Org Chart & Workforce' : 'Sơ đồ Tổ chức & Nhân sự', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12.5)),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // Tab Views
            Expanded(
              child: Obx(() {
                if (controller.isLoading.value &&
                    controller.overview.value == null &&
                    controller.workforce.value == null) {
                  return const Center(child: CircularProgressIndicator());
                }

                return TabBarView(
                  controller: controller.tabController,
                  children: [
                    _buildOverviewTab(),
                    _buildWorkforceTab(),
                  ],
                );
              }),
            ),
          ],
        );
  }

  Widget _buildErrorBanner(ApiFailureDetail failure) {
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFFEF4444).withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0xFFEF4444).withValues(alpha: 0.4)),
      ),
      child: Row(
        children: [
          const Icon(Icons.error_outline, size: 18, color: Color(0xFFEF4444)),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              organizationFailureMessage(failure),
              key: const Key('organization-error-banner'),
              style: const TextStyle(fontSize: 12.5, color: Colors.white),
            ),
          ),
          TextButton(
            onPressed: controller.loadOrganizationData,
            child: const Text('Thử lại', style: TextStyle(color: AppTheme.primary)),
          ),
        ],
      ),
    );
  }

  Widget _buildOverviewTab() {
    final overview = controller.overview.value;
    final error = controller.overviewError.value;

    if (overview == null) {
      return Center(
        child: error != null
            ? _buildErrorBanner(error)
            : const Text('Chưa có dữ liệu tổ chức', style: TextStyle(color: AppTheme.textMutedDark)),
      );
    }

    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (error != null) _buildErrorBanner(error),
          Row(
            children: [
              Expanded(
                child: _buildMetricCard(
                  'Tổ chức',
                  overview.name,
                  'Giai đoạn ${overview.lifecycleStage}',
                  Icons.corporate_fare_rounded,
                  const Color(0xFF00F0FF),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _buildMetricCard(
                  'Tổng Lực lượng',
                  '${overview.humanMemberCount + overview.aiMemberCount} Thành viên',
                  '${overview.humanMemberCount} Con người · ${overview.aiMemberCount} AI Agents',
                  Icons.group,
                  const Color(0xFF10B981),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _buildMetricCard(
                  'Vai trò của bạn',
                  overview.viewerRole,
                  overview.canManageWorkforce ? 'Được quản lý nhân sự AI' : 'Chỉ xem',
                  Icons.verified_user_outlined,
                  const Color(0xFFF59E0B),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildMetricCard(String label, String value, String sub, IconData icon, Color color) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF0D172A),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFF1E293B)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(label, style: const TextStyle(fontSize: 12, color: AppTheme.textMutedDark, fontWeight: FontWeight.bold)),
              Icon(icon, size: 18, color: color),
            ],
          ),
          const SizedBox(height: 10),
          Text(value, style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800, color: color)),
          const SizedBox(height: 4),
          Text(sub, style: const TextStyle(fontSize: 11, color: AppTheme.textMutedDark)),
        ],
      ),
    );
  }

  Widget _buildWorkforceTab() {
    final workforce = controller.workforce.value;
    final error = controller.workforceError.value;

    if (workforce == null) {
      return Center(
        child: error != null
            ? _buildErrorBanner(error)
            : const Text('Chưa có dữ liệu nhân sự', style: TextStyle(color: AppTheme.textMutedDark)),
      );
    }

    final members = workforce.members;
    final titles = {for (final m in members) m.id: m.roleTitle};

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (error != null) _buildErrorBanner(error),
        Expanded(
          child: members.isEmpty
              ? const Center(
                  child: Text('Chưa có nhân sự trong tổ chức', style: TextStyle(fontSize: 12, color: AppTheme.textMutedDark)),
                )
              : ListView.builder(
                  itemCount: members.length,
                  itemBuilder: (context, index) => _buildMemberRow(members[index], titles),
                ),
        ),
      ],
    );
  }

  Widget _buildMemberRow(OrganizationWorkforceMember m, Map<String, String> titles) {
    final isAI = m.isAi;
    final reportsTo = m.managerMemberId != null ? titles[m.managerMemberId] : null;
    return Container(
      margin: const EdgeInsets.only(bottom: 6),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: const Color(0xFF070C18),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: isAI ? const Color(0xFF00F0FF).withValues(alpha: 0.2) : const Color(0xFF334155)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                isAI ? Icons.smart_toy : Icons.person,
                size: 14,
                color: isAI ? const Color(0xFF00F0FF) : const Color(0xFF10B981),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  m.roleTitle,
                  style: const TextStyle(fontSize: 12.5, color: Colors.white, fontWeight: FontWeight.w600),
                ),
              ),
              Text(
                isAI ? 'AI' : 'HUMAN',
                style: TextStyle(
                  fontSize: 9,
                  fontWeight: FontWeight.bold,
                  color: isAI ? const Color(0xFF00F0FF) : const Color(0xFF10B981),
                ),
              ),
            ],
          ),
          if (reportsTo != null) ...[
            const SizedBox(height: 4),
            Padding(
              padding: const EdgeInsets.only(left: 22),
              child: Text(
                'Báo cáo cho: $reportsTo',
                style: const TextStyle(fontSize: 10.5, color: AppTheme.textMutedDark, fontStyle: FontStyle.italic),
              ),
            ),
          ],
        ],
      ),
    );
  }

  /// Chỉ chọn trong danh sách workspace agent do server liệt kê; UI không
  /// gửi prompt/spec/capability (spec 2026-09-25 §7).
  void _showPlaceAiDialog(BuildContext context) {
    if (!controller.canManageWorkforce) {
      AppToast.error('Bạn không có quyền quản lý nhân sự AI trong tổ chức này.');
      return;
    }
    final agents = controller.placeableAgents;
    if (agents.isEmpty) {
      AppToast.error('Chưa có tác tử AI nào đã publish để xếp vào tổ chức.');
      return;
    }

    final roleCtrl = TextEditingController();
    String selectedAgentId = agents.first.workspaceAgentId!;

    Get.dialog(
      StatefulBuilder(
        builder: (context, setState) {
          return Dialog(
            backgroundColor: const Color(0xFF0D172A),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(14),
              side: const BorderSide(color: Color(0xFF1E293B)),
            ),
            child: Container(
              width: 450,
              padding: const EdgeInsets.all(20.0),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Xếp Tác tử AI vào tổ chức',
                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white),
                  ),
                  const SizedBox(height: 14),
                  const Text('Tác tử AI đã publish:', style: TextStyle(fontSize: 12, color: AppTheme.textMutedDark)),
                  const SizedBox(height: 6),
                  DropdownButtonFormField<String>(
                    initialValue: selectedAgentId,
                    dropdownColor: const Color(0xFF0D172A),
                    style: const TextStyle(color: Colors.white, fontSize: 13),
                    items: agents.map((a) {
                      return DropdownMenuItem<String>(
                        value: a.workspaceAgentId,
                        child: Text(a.roleTitle),
                      );
                    }).toList(),
                    onChanged: (val) {
                      if (val != null) {
                        setState(() => selectedAgentId = val);
                      }
                    },
                    decoration: const InputDecoration(border: OutlineInputBorder()),
                  ),
                  const SizedBox(height: 12),
                  const Text('Vị trí / Chức danh:', style: TextStyle(fontSize: 12, color: AppTheme.textMutedDark)),
                  const SizedBox(height: 6),
                  TextField(
                    controller: roleCtrl,
                    style: const TextStyle(color: Colors.white),
                    decoration: const InputDecoration(hintText: 'VD: Trưởng nhóm Tăng trưởng, Chuyên viên Pháp chế...', border: OutlineInputBorder()),
                  ),
                  const SizedBox(height: 18),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.end,
                    children: [
                      TextButton(
                        onPressed: () => Get.back(),
                        child: const Text('Hủy', style: TextStyle(color: AppTheme.textMutedDark)),
                      ),
                      const SizedBox(width: 8),
                      ElevatedButton(
                        onPressed: () async {
                          final role = roleCtrl.text.trim();
                          if (role.isEmpty) return;
                          final ok = await controller.placeAiWorkforce(
                            workspaceAgentId: selectedAgentId,
                            roleTitle: role,
                          );
                          if (ok) Get.back();
                        },
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF00F0FF),
                          foregroundColor: Colors.black,
                        ),
                        child: const Text('Xác nhận', style: TextStyle(fontWeight: FontWeight.bold)),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}
