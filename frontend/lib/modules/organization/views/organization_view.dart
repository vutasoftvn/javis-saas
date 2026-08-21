import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/organization_controller.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/floating_app_bar.dart';

class OrganizationView extends GetView<OrganizationController> {
  const OrganizationView({super.key});

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<OrganizationController>()) {
      Get.put(OrganizationController());
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Header
        JavisFloatingAppBar(
              title: 'Tổ chức & Nhân sự Hỗn hợp (Hybrid Workforce)',
              subtitle: 'Trung tâm Điều hành CEO (Command Center) & Quản trị Lực lượng Nhân sự AI kết hợp Con người.',
              icon: Icons.corporate_fare_rounded,
              actions: [
                ElevatedButton.icon(
                  onPressed: () => _showHireAIDialog(context),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.primary.withValues(alpha: 0.15),
                    foregroundColor: AppTheme.primary,
                    side: const BorderSide(color: AppTheme.primary),
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
                  ),
                  icon: const Icon(Icons.person_add_rounded, size: 18),
                  label: const Text('Tuyển dụng AI', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                ),
                const SizedBox(width: 10),
                Container(
                  decoration: const BoxDecoration(
                    color: AppTheme.primary,
                    shape: BoxShape.circle,
                  ),
                  child: IconButton(
                    tooltip: 'Tải lại',
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
                tabs: const [
                  Tab(
                    height: 32,
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.dashboard_customize_outlined, size: 15),
                        SizedBox(width: 8),
                        Text('CEO Command Center', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12.5)),
                      ],
                    ),
                  ),
                  Tab(
                    height: 32,
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.account_tree_outlined, size: 15),
                        SizedBox(width: 8),
                        Text('Sơ đồ Tổ chức & Nhân sự', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12.5)),
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
                if (controller.isLoading.value) {
                  return const Center(child: CircularProgressIndicator());
                }

                return TabBarView(
                  controller: controller.tabController,
                  children: [
                    _buildCommandCenterTab(),
                    _buildOrgChartTab(),
                  ],
                );
              }),
            ),
          ],
        );
  }

  Widget _buildCommandCenterTab() {
    final cc = controller.commandCenterData.value;
    final briefing = controller.dailyBriefingData.value;

    if (cc == null) {
      return const Center(
        child: Text('Không thể tải dữ liệu Command Center', style: TextStyle(color: AppTheme.textMutedDark)),
      );
    }

    final wf = cc['workforce_metrics'] as Map<String, dynamic>? ?? {};
    final gov = cc['governance_metrics'] as Map<String, dynamic>? ?? {};

    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // KPI Metric Strip
          Row(
            children: [
              Expanded(
                child: _buildMetricCard(
                  'Tổng Lực lượng',
                  '${wf['total_members'] ?? 0} Thành viên',
                  '${wf['humans'] ?? 0} Con người · ${wf['ai_agents'] ?? 0} AI Agents',
                  Icons.group,
                  const Color(0xFF00F0FF),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _buildMetricCard(
                  'Tỷ lệ Ứng dụng AI',
                  '${wf['ai_adoption_rate'] ?? 0}%',
                  'Mức độ tự động hóa quy trình',
                  Icons.auto_awesome,
                  const Color(0xFF10B981),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _buildMetricCard(
                  'Mục tiêu OKRs',
                  '${gov['active_okrs'] ?? 0} Active',
                  'Chiến lược đang theo dõi',
                  Icons.flag,
                  const Color(0xFFF59E0B),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _buildMetricCard(
                  'Chờ Phê duyệt',
                  '${gov['pending_approvals'] ?? 0} Yêu cầu',
                  'Cần quyết định từ Founder',
                  Icons.fact_check,
                  const Color(0xFFEC4899),
                ),
              ),
            ],
          ),
          const SizedBox(height: 20),

          // Daily Briefing Card
          if (briefing != null) ...[
            Container(
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(
                color: const Color(0xFF0D172A),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: const Color(0xFF00F0FF).withValues(alpha: 0.3)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      const Icon(Icons.bolt, color: Color(0xFF00F0FF), size: 20),
                      const SizedBox(width: 8),
                      Text(
                        briefing['title'] as String? ?? 'Bản tin Điều hành Hằng ngày',
                        style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: Colors.white),
                      ),
                      const Spacer(),
                      Text(
                        briefing['date'] as String? ?? '',
                        style: const TextStyle(fontSize: 12, color: AppTheme.textMutedDark),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Text(
                    briefing['summary'] as String? ?? '',
                    style: const TextStyle(fontSize: 13.5, color: Color(0xFFCBD5E1), height: 1.5),
                  ),
                  const SizedBox(height: 12),
                  const Divider(color: Color(0xFF1E293B)),
                  const SizedBox(height: 8),
                  const Text('Điểm tin cốt lõi:', style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.bold, color: Color(0xFF00F0FF))),
                  const SizedBox(height: 6),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: ((briefing['key_highlights'] as List<dynamic>?) ?? []).map((h) {
                      return Padding(
                        padding: const EdgeInsets.only(bottom: 4),
                        child: Row(
                          children: [
                            const Icon(Icons.check_circle_outline, size: 14, color: Color(0xFF10B981)),
                            const SizedBox(width: 8),
                            Text(h.toString(), style: const TextStyle(fontSize: 13, color: Colors.white)),
                          ],
                        ),
                      );
                    }).toList(),
                  ),
                ],
              ),
            ),
          ],
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

  Widget _buildOrgChartTab() {
    final chart = controller.orgChartData.value;
    if (chart == null) {
      return const Center(
        child: Text('Không thể tải sơ đồ tổ chức', style: TextStyle(color: AppTheme.textMutedDark)),
      );
    }

    final depts = (chart['departments'] as List<dynamic>?) ?? [];

    return GridView.builder(
      gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
        maxCrossAxisExtent: 380,
        crossAxisSpacing: 16,
        mainAxisSpacing: 16,
        childAspectRatio: 1.1,
      ),
      itemCount: depts.length,
      itemBuilder: (context, index) {
        final d = depts[index] as Map<String, dynamic>;
        final deptName = d['name'] as String? ?? 'Phòng ban';
        final members = (d['members'] as List<dynamic>?) ?? [];

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
                  Expanded(
                    child: Text(
                      deptName,
                      style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: Colors.white),
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
                    decoration: BoxDecoration(
                      color: const Color(0xFF00F0FF).withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      '${members.length} nhân sự',
                      style: const TextStyle(fontSize: 11, color: Color(0xFF00F0FF), fontWeight: FontWeight.bold),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              const Divider(color: Color(0xFF1E293B)),
              const SizedBox(height: 8),

              Expanded(
                child: members.isEmpty
                    ? const Center(
                        child: Text('Chưa có nhân sự trực thuộc', style: TextStyle(fontSize: 12, color: AppTheme.textMutedDark)),
                      )
                    : ListView.builder(
                        itemCount: members.length,
                        itemBuilder: (context, mIdx) {
                          final m = members[mIdx] as Map<String, dynamic>;
                          final role = m['role_title'] as String? ?? 'Nhân sự';
                          final isAI = m['member_type'] == 'AI_AGENT';
                          final reportsTo = m['reports_to_role_title'] as String?;

                          return Container(
                            margin: const EdgeInsets.only(bottom: 6),
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                            decoration: BoxDecoration(
                              color: const Color(0xFF070C18),
                              borderRadius: BorderRadius.circular(6),
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
                                        role,
                                        style: const TextStyle(fontSize: 12, color: Colors.white, fontWeight: FontWeight.w600),
                                      ),
                                    ),
                                    Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                                      decoration: BoxDecoration(
                                        color: isAI ? const Color(0xFF00F0FF).withValues(alpha: 0.15) : const Color(0xFF10B981).withValues(alpha: 0.15),
                                        borderRadius: BorderRadius.circular(3),
                                      ),
                                      child: Text(
                                        isAI ? 'AI' : 'HUMAN',
                                        style: TextStyle(
                                          fontSize: 9,
                                          fontWeight: FontWeight.bold,
                                          color: isAI ? const Color(0xFF00F0FF) : const Color(0xFF10B981),
                                        ),
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
                        },
                      ),
              ),
            ],
          ),
        );
      },
    );
  }

  void _showHireAIDialog(BuildContext context) {
    final chart = controller.orgChartData.value;
    final depts = (chart?['departments'] as List<dynamic>?) ?? [];
    if (depts.isEmpty) {
      Get.snackbar('Lỗi', 'Không tìm thấy phòng ban để tuyển dụng');
      return;
    }

    final nameCtrl = TextEditingController();
    final roleCtrl = TextEditingController();
    final promptCtrl = TextEditingController();
    String selectedDeptId = depts.first['department_id'] as String;

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
                    'Tuyển dụng Tác tử AI (Hire AI Employee)',
                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white),
                  ),
                  const SizedBox(height: 14),

                  const Text('Phòng ban trực thuộc:', style: TextStyle(fontSize: 12, color: AppTheme.textMutedDark)),
                  const SizedBox(height: 6),
                  DropdownButtonFormField<String>(
                    initialValue: selectedDeptId,
                    dropdownColor: const Color(0xFF0D172A),
                    style: const TextStyle(color: Colors.white, fontSize: 13),
                    items: depts.map((d) {
                      return DropdownMenuItem<String>(
                        value: d['department_id'] as String,
                        child: Text(d['name'] as String),
                      );
                    }).toList(),
                    onChanged: (val) {
                      if (val != null) {
                        setState(() => selectedDeptId = val);
                      }
                    },
                    decoration: const InputDecoration(border: OutlineInputBorder()),
                  ),
                  const SizedBox(height: 12),

                  const Text('Tên Tác tử AI:', style: TextStyle(fontSize: 12, color: AppTheme.textMutedDark)),
                  const SizedBox(height: 6),
                  TextField(
                    controller: nameCtrl,
                    style: const TextStyle(color: Colors.white),
                    decoration: const InputDecoration(hintText: 'VD: Alex AI, Maya Legal...', border: OutlineInputBorder()),
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
                        onPressed: () {
                          if (nameCtrl.text.trim().isEmpty || roleCtrl.text.trim().isEmpty) return;
                          controller.hireAIEmployee(
                            name: nameCtrl.text.trim(),
                            roleTitle: roleCtrl.text.trim(),
                            departmentId: selectedDeptId,
                            systemPrompt: promptCtrl.text.trim().isNotEmpty ? promptCtrl.text.trim() : null,
                          );
                          Get.back();
                        },
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF00F0FF),
                          foregroundColor: Colors.black,
                        ),
                        child: const Text('Tuyển dụng', style: TextStyle(fontWeight: FontWeight.bold)),
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
