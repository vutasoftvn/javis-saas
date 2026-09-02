import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../../core/theme/app_theme.dart';
import '../../../core/ui/app_copy.dart';
import '../../../core/ui/layout_breakpoints.dart';
import '../controllers/skill_registry_controller.dart';
import 'widgets/add_skill_candidate_dialog.dart';
import 'widgets/skill_detail_sidebar.dart';

const List<Map<String, Object>> _kSkillDomains = [
  {'key': 'ALL', 'label': 'TẤT CẢ LĨNH VỰC', 'icon': Icons.apps_rounded},
  {'key': 'sales', 'label': 'BÁN HÀNG & CRM', 'icon': Icons.point_of_sale_rounded},
  {'key': 'marketing', 'label': 'MARKETING & LEADS', 'icon': Icons.campaign_rounded},
  {'key': 'finance', 'label': 'TÀI CHÍNH TT68', 'icon': Icons.account_balance_wallet_rounded},
  {'key': 'legal', 'label': 'PHÁP LÝ & HỢP ĐỒNG', 'icon': Icons.gavel_rounded},
  {'key': 'operations', 'label': 'VẬN HÀNH', 'icon': Icons.precision_manufacturing_rounded},
  {'key': 'tech', 'label': 'KỸ THUẬT', 'icon': Icons.terminal_rounded},
];

class SkillRegistryView extends StatelessWidget {
  const SkillRegistryView({super.key});

  @override
  Widget build(BuildContext context) {
    final controller = Get.put(SkillRegistryController());

    return Scaffold(
      backgroundColor: const Color(0xFF060A14),
      body: LayoutBuilder(
        builder: (context, constraints) {
          // Task 10 — trước đây view này không hề đọc breakpoint nào: filter
          // theo domain + trạng thái luôn nằm ngang trên MỘT Row, giả định
          // ngầm màn hình desktop rộng. Ở compact (điện thoại dọc), Row đó
          // tràn ra ngoài viewport lặng lẽ. Nay dùng `layoutForWidth` — bậc
          // compact gom toàn bộ filter vào MỘT nút "Bộ lọc" mở sheet dọc,
          // bậc medium/expanded vẫn hiển thị filter ngang (trong scroll
          // ngang, không còn cố định width cứng gây tràn ở màn hình vừa).
          final layout = layoutForWidth(constraints.maxWidth);
          final isCompact = layout == AppLayout.compact;

          return Column(
            children: [
              _buildHeader(context, controller, isCompact),
              if (!isCompact) _buildLifecycleMetrics(controller),
              if (!isCompact) _buildDomainFilterRow(controller),
              _buildContent(context, controller),
            ],
          );
        },
      ),
    );
  }

  // ── Header Bar ──────────────────────────────────────────────────────────
  Widget _buildHeader(BuildContext context, SkillRegistryController controller, bool isCompact) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDark,
        border: Border(
          bottom: BorderSide(
            color: AppTheme.borderDark,
          ),
        ),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: AppTheme.primary.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(
                color: AppTheme.primary.withValues(alpha: 0.3),
              ),
            ),
            child: const Icon(
              Icons.psychology_outlined,
              color: AppTheme.primaryLight,
              size: 22,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  isCompact ? 'Skill Registry' : 'Skill Registry & Vòng đời Kỹ năng AI (P5)',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 17.5,
                    fontWeight: FontWeight.w700,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                if (!isCompact) ...[
                  const SizedBox(height: 2),
                  Text(
                    'Quản trị Kỹ năng: Candidate ➔ Evaluation ➔ Admin Approval ➔ Active (§61/§62)',
                    style: TextStyle(
                      color: Colors.white.withValues(alpha: 0.6),
                      fontSize: 13,
                    ),
                  ),
                ],
              ],
            ),
          ),
          if (isCompact)
            IconButton(
              tooltip: AppCopy.skillRegistryFilterTooltip,
              onPressed: () => _openFilterSheet(context, controller),
              icon: const Icon(Icons.filter_alt_outlined, color: AppTheme.primaryLight),
            )
          else ...[
            // Sync built-in skills button
            OutlinedButton.icon(
              style: OutlinedButton.styleFrom(
                foregroundColor: AppTheme.primaryLight,
                side: BorderSide(color: AppTheme.primaryLight.withValues(alpha: 0.5)),
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
              ),
              icon: const Icon(Icons.sync_rounded, size: 16),
              label: const Text(
                'Đồng bộ Kỹ năng Mẫu',
                style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
              ),
              onPressed: () => controller.syncBuiltInSkills(),
            ),
            const SizedBox(width: 8),
          ],
          // Add skill candidate button — luôn hiện, kể cả compact (hành động
          // chính của màn hình, không được giấu vào sheet).
          if (isCompact)
            IconButton(
              tooltip: 'Đăng ký Kỹ năng Mới',
              onPressed: () => AddSkillCandidateDialog.show(context),
              icon: const Icon(Icons.add_task, color: AppTheme.primaryLight),
            )
          else
            ElevatedButton.icon(
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.primary,
                foregroundColor: const Color(0xFF04070E),
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
              ),
              icon: const Icon(Icons.add_task, size: 16),
              label: const Text(
                'Đăng ký Kỹ năng Mới',
                style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700),
              ),
              onPressed: () => AddSkillCandidateDialog.show(context),
            ),
        ],
      ),
    );
  }

  // ── Lifecycle Metric Cards (medium/expanded) ─────────────────────────────
  Widget _buildLifecycleMetrics(SkillRegistryController controller) {
    return Obx(() {
      final candidateCount = controller.countByStatus('candidate');
      final evalCount = controller.countByStatus('evaluation');
      final activeCount = controller.countByStatus('active');
      final deprecatedCount = controller.countByStatus('deprecated');
      final avgSuccess = (controller.averageSuccessRate * 100).toInt();

      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
        color: const Color(0xFF080D1A),
        child: SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: Row(
            children: [
              _buildStatusPill('Tất cả', '${controller.skills.length}', Colors.white, 'ALL', controller),
              const SizedBox(width: 8),
              _buildStatusPill(
                  'Candidate (Ứng viên)', '$candidateCount', const Color(0xFFF59E0B), 'candidate', controller),
              const SizedBox(width: 8),
              _buildStatusPill(
                  'Evaluation (Đang test)', '$evalCount', const Color(0xFF00E5FF), 'evaluation', controller),
              const SizedBox(width: 8),
              _buildStatusPill(
                  'Active (Chính thức)', '$activeCount', const Color(0xFF10B981), 'active', controller),
              const SizedBox(width: 8),
              _buildStatusPill(
                  'Deprecated (Đã ngưng)', '$deprecatedCount', const Color(0xFFEF4444), 'deprecated', controller),
              const SizedBox(width: 12),
              // Avg Success Rate indicator
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                decoration: BoxDecoration(
                  color: const Color(0xFF10B981).withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: const Color(0xFF10B981).withValues(alpha: 0.3)),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.speed, size: 15, color: Color(0xFF34D399)),
                    const SizedBox(width: 6),
                    Text(
                      'Success Avg: $avgSuccess%',
                      style: const TextStyle(
                        color: Color(0xFF34D399),
                        fontSize: 12.5,
                        fontWeight: FontWeight.w700,
                        fontFamily: 'monospace',
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 10),
              // Search box
              SizedBox(
                width: 210,
                height: 36,
                child: TextField(
                  style: const TextStyle(color: Colors.white, fontSize: 13),
                  decoration: InputDecoration(
                    hintText: 'Tìm kỹ năng, SOP...',
                    hintStyle: const TextStyle(color: Color(0xFF64748B), fontSize: 12.5),
                    prefixIcon: const Icon(Icons.search, size: 16, color: Color(0xFF64748B)),
                    filled: true,
                    fillColor: const Color(0xFF131B2E),
                    contentPadding: EdgeInsets.zero,
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8),
                      borderSide: const BorderSide(color: Color(0xFF1E293B)),
                    ),
                    enabledBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8),
                      borderSide: const BorderSide(color: Color(0xFF1E293B)),
                    ),
                    focusedBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8),
                      borderSide: const BorderSide(color: AppTheme.primaryLight),
                    ),
                  ),
                  onChanged: (val) => controller.searchQuery.value = val,
                ),
              ),
            ],
          ),
        ),
      );
    });
  }

  // ── Domain Filter Buttons (medium/expanded) ──────────────────────────────
  Widget _buildDomainFilterRow(SkillRegistryController controller) {
    return Obx(() {
      final activeDomain = controller.selectedDomain.value;

      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
        decoration: const BoxDecoration(
          border: Border(
            bottom: BorderSide(color: Color(0xFF131B2E)),
          ),
        ),
        child: SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: Row(
            children: _kSkillDomains.map((d) {
              final isSelected = activeDomain == d['key'];
              return Padding(
                padding: const EdgeInsets.only(right: 6),
                child: InkWell(
                  onTap: () => controller.selectedDomain.value = d['key'] as String,
                  borderRadius: BorderRadius.circular(7),
                  child: Container(
                    height: 34,
                    padding: const EdgeInsets.symmetric(horizontal: 11),
                    alignment: Alignment.center,
                    decoration: BoxDecoration(
                      color: isSelected ? AppTheme.primary : const Color(0xFF131B2E),
                      borderRadius: BorderRadius.circular(7),
                      border: Border.all(
                        color: isSelected ? AppTheme.primary : const Color(0xFF1E293B),
                      ),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          d['icon'] as IconData,
                          size: 14,
                          color: isSelected ? const Color(0xFF04070E) : const Color(0xFF94A3B8),
                        ),
                        const SizedBox(width: 6),
                        Text(
                          d['label'] as String,
                          style: TextStyle(
                            color: isSelected ? const Color(0xFF04070E) : const Color(0xFF94A3B8),
                            fontSize: 12.5,
                            fontWeight: isSelected ? FontWeight.bold : FontWeight.w500,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              );
            }).toList(),
          ),
        ),
      );
    });
  }

  /// Task 10 — compact layout: gom TOÀN BỘ filter (trạng thái vòng đời +
  /// lĩnh vực + ô tìm kiếm) vào một sheet dọc thay vì hàng ngang tràn màn
  /// hình. Đây là "vertical filter sheet" mà test golden compact đòi hỏi.
  void _openFilterSheet(BuildContext context, SkillRegistryController controller) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: const Color(0xFF0F172A),
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) {
        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Icon(Icons.filter_alt_outlined, color: AppTheme.primaryLight),
                    const SizedBox(width: 10),
                    const Text(
                      AppCopy.skillRegistryFilterSheetTitle,
                      style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w700),
                    ),
                    const Spacer(),
                    TextButton(
                      onPressed: () => Navigator.pop(ctx),
                      child: const Text(AppCopy.skillRegistryFilterCloseButton),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                TextField(
                  style: const TextStyle(color: Colors.white, fontSize: 13),
                  decoration: InputDecoration(
                    hintText: 'Tìm kỹ năng, SOP...',
                    hintStyle: const TextStyle(color: Color(0xFF64748B), fontSize: 12.5),
                    prefixIcon: const Icon(Icons.search, size: 16, color: Color(0xFF64748B)),
                    filled: true,
                    fillColor: const Color(0xFF131B2E),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8),
                      borderSide: BorderSide.none,
                    ),
                  ),
                  onChanged: (val) => controller.searchQuery.value = val,
                ),
                const SizedBox(height: 16),
                Text(
                  AppCopy.skillRegistryFilterStatusSection,
                  style: TextStyle(color: Colors.white.withValues(alpha: 0.6), fontSize: 12, fontWeight: FontWeight.w600),
                ),
                const SizedBox(height: 8),
                Obx(() => Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        _buildStatusPill('Tất cả', '${controller.skills.length}', Colors.white, 'ALL', controller),
                        _buildStatusPill('Candidate', '${controller.countByStatus('candidate')}',
                            const Color(0xFFF59E0B), 'candidate', controller),
                        _buildStatusPill('Evaluation', '${controller.countByStatus('evaluation')}',
                            const Color(0xFF00E5FF), 'evaluation', controller),
                        _buildStatusPill('Active', '${controller.countByStatus('active')}',
                            const Color(0xFF10B981), 'active', controller),
                        _buildStatusPill('Deprecated', '${controller.countByStatus('deprecated')}',
                            const Color(0xFFEF4444), 'deprecated', controller),
                      ],
                    )),
                const SizedBox(height: 16),
                Text(
                  AppCopy.skillRegistryFilterDomainSection,
                  style: TextStyle(color: Colors.white.withValues(alpha: 0.6), fontSize: 12, fontWeight: FontWeight.w600),
                ),
                const SizedBox(height: 8),
                Obx(() => Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: _kSkillDomains.map((d) {
                        final isSelected = controller.selectedDomain.value == d['key'];
                        return Padding(
                          padding: const EdgeInsets.only(bottom: 6),
                          child: InkWell(
                            onTap: () => controller.selectedDomain.value = d['key'] as String,
                            borderRadius: BorderRadius.circular(8),
                            child: Container(
                              width: double.infinity,
                              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                              decoration: BoxDecoration(
                                color: isSelected ? AppTheme.primary : const Color(0xFF131B2E),
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: Row(
                                children: [
                                  Icon(
                                    d['icon'] as IconData,
                                    size: 16,
                                    color: isSelected ? const Color(0xFF04070E) : const Color(0xFF94A3B8),
                                  ),
                                  const SizedBox(width: 8),
                                  Text(
                                    d['label'] as String,
                                    style: TextStyle(
                                      color: isSelected ? const Color(0xFF04070E) : const Color(0xFF94A3B8),
                                      fontSize: 13,
                                      fontWeight: isSelected ? FontWeight.bold : FontWeight.w500,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        );
                      }).toList(),
                    )),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildContent(BuildContext context, SkillRegistryController controller) {
    return
          Expanded(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // 1. Grid of Skills
                Expanded(
                  child: Obx(() {
                    if (controller.isLoading.value && controller.skills.isEmpty) {
                      return const Center(
                        child: CircularProgressIndicator(color: AppTheme.primaryLight),
                      );
                    }

                    final filtered = controller.filteredSkills;
                    final selected = controller.selectedSkill.value;

                    if (filtered.isEmpty) {
                      return Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.psychology, size: 48, color: Colors.white.withValues(alpha: 0.15)),
                            const SizedBox(height: 12),
                            const Text(
                              'Không có kỹ năng nào trong danh mục này',
                              style: TextStyle(color: Color(0xFF64748B), fontSize: 14),
                            ),
                            const SizedBox(height: 16),
                            Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                ElevatedButton.icon(
                                  style: ElevatedButton.styleFrom(
                                    backgroundColor: AppTheme.primary,
                                    foregroundColor: const Color(0xFF04070E),
                                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                                  ),
                                  icon: const Icon(Icons.sync_rounded, size: 16),
                                  label: const Text(
                                    'Đồng bộ Kỹ năng Mẫu',
                                    style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700),
                                  ),
                                  onPressed: () => controller.syncBuiltInSkills(),
                                ),
                                const SizedBox(width: 10),
                                OutlinedButton.icon(
                                  style: OutlinedButton.styleFrom(
                                    foregroundColor: Colors.white70,
                                    side: const BorderSide(color: Color(0xFF334155)),
                                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                                  ),
                                  icon: const Icon(Icons.add, size: 16),
                                  label: const Text(
                                    'Đăng ký Kỹ năng Mới',
                                    style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
                                  ),
                                  onPressed: () => AddSkillCandidateDialog.show(context),
                                ),
                              ],
                            ),
                          ],
                        ),
                      );
                    }

                    return Padding(
                      padding: const EdgeInsets.all(14),
                      child: GridView.builder(
                        gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                          maxCrossAxisExtent: 380,
                          mainAxisExtent: 146,
                          crossAxisSpacing: 10,
                          mainAxisSpacing: 10,
                        ),
                        itemCount: filtered.length,
                        itemBuilder: (context, index) {
                          final skill = filtered[index];
                          final isSelected = selected != null && skill['id']?.toString() == selected['id']?.toString();
                          return _buildSkillCard(context, skill, controller, isSelected);
                        },
                      ),
                    );
                  }),
                ),

                // 2. Right Detail Sidebar
                Obx(() {
                  final sel = controller.selectedSkill.value;
                  if (sel != null) {
                    return SkillDetailSidebar(
                      skill: sel,
                      onClose: () => controller.selectedSkill.value = null,
                    );
                  }
                  return const SizedBox.shrink();
                }),
              ],
            ),
          );
  }

  Widget _buildStatusPill(
    String label,
    String count,
    Color color,
    String statusKey,
    SkillRegistryController controller,
  ) {
    final isSelected = controller.selectedStatus.value == statusKey;
    return InkWell(
      onTap: () => controller.selectedStatus.value = statusKey,
      borderRadius: BorderRadius.circular(20),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
        decoration: BoxDecoration(
          color: isSelected ? color.withValues(alpha: 0.15) : const Color(0xFF131B2E),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: isSelected ? color : const Color(0xFF1E293B),
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 7,
              height: 7,
              decoration: BoxDecoration(color: color, shape: BoxShape.circle),
            ),
            const SizedBox(width: 6),
            Text(
              label,
              style: TextStyle(
                color: isSelected ? Colors.white : const Color(0xFF94A3B8),
                fontSize: 12.5,
                fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
              ),
            ),
            const SizedBox(width: 5),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
              decoration: BoxDecoration(
                color: color.withValues(alpha: 0.2),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                count,
                style: TextStyle(
                  color: color,
                  fontSize: 11.5,
                  fontWeight: FontWeight.w800,
                  fontFamily: 'monospace',
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSkillCard(
    BuildContext context,
    Map<String, dynamic> skill,
    SkillRegistryController controller,
    bool isSelected,
  ) {
    final name = skill['name']?.toString() ?? 'Skill';
    final domain = (skill['domain']?.toString() ?? 'general').toLowerCase();
    final status = (skill['status']?.toString() ?? 'candidate').toLowerCase();
    final version = skill['version']?.toString() ?? '1.0.0';
    final description = skill['description']?.toString() ?? '';
    final successRate = ((skill['success_rate'] as num?)?.toDouble() ?? 1.0) * 100;
    final tools = (skill['tool_permissions'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [];

    IconData domainIcon;
    Color domainColor;
    String domainLabel;

    switch (domain) {
      case 'sales':
        domainIcon = Icons.point_of_sale_rounded;
        domainColor = Colors.blueAccent;
        domainLabel = 'BÁN HÀNG';
        break;
      case 'marketing':
        domainIcon = Icons.campaign_rounded;
        domainColor = Colors.purpleAccent;
        domainLabel = 'MARKETING';
        break;
      case 'finance':
        domainIcon = Icons.account_balance_wallet_rounded;
        domainColor = Colors.amberAccent;
        domainLabel = 'TÀI CHÍNH';
        break;
      case 'legal':
        domainIcon = Icons.gavel_rounded;
        domainColor = Colors.pinkAccent;
        domainLabel = 'PHÁP LÝ';
        break;
      case 'operations':
        domainIcon = Icons.precision_manufacturing_rounded;
        domainColor = const Color(0xFF10B981);
        domainLabel = 'VẬN HÀNH';
        break;
      case 'tech':
        domainIcon = Icons.terminal_rounded;
        domainColor = const Color(0xFF00E5FF);
        domainLabel = 'KỸ THUẬT';
        break;
      default:
        domainIcon = Icons.psychology_rounded;
        domainColor = Colors.tealAccent;
        domainLabel = domain.toUpperCase();
    }

    Color statusColor = const Color(0xFF94A3B8);
    String statusLabel = 'ỨNG VIÊN';
    if (status == 'candidate') {
      statusColor = const Color(0xFFF59E0B);
      statusLabel = 'CANDIDATE';
    } else if (status == 'evaluation') {
      statusColor = const Color(0xFF00E5FF);
      statusLabel = 'EVALUATION';
    } else if (status == 'active') {
      statusColor = const Color(0xFF10B981);
      statusLabel = 'CHÍNH THỨC';
    } else if (status == 'deprecated') {
      statusColor = const Color(0xFFEF4444);
      statusLabel = 'ĐÃ NGƯNG';
    }

    return Container(
      decoration: BoxDecoration(
        color: isSelected ? AppTheme.primary.withValues(alpha: 0.08) : AppTheme.surfaceDark,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: isSelected
              ? AppTheme.primary
              : (status == 'active' ? AppTheme.borderDark : statusColor.withValues(alpha: 0.3)),
          width: isSelected ? 1.5 : 1.0,
        ),
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: () {
            controller.selectedSkill.value = skill;
          },
          borderRadius: BorderRadius.circular(10),
          hoverColor: Colors.white.withValues(alpha: 0.03),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Top Header Row
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(3.5),
                      decoration: BoxDecoration(
                        color: domainColor.withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(5),
                      ),
                      child: Icon(domainIcon, size: 13.5, color: domainColor),
                    ),
                    const SizedBox(width: 6),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1.5),
                      decoration: BoxDecoration(
                        color: domainColor.withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text(
                        domainLabel,
                        style: TextStyle(
                          color: domainColor,
                          fontSize: 10,
                          fontWeight: FontWeight.w700,
                          letterSpacing: 0.3,
                        ),
                      ),
                    ),
                    const SizedBox(width: 4),
                    Text(
                      'v$version',
                      style: const TextStyle(
                        color: AppTheme.textMutedDark,
                        fontSize: 10.5,
                        fontFamily: 'monospace',
                      ),
                    ),
                    const Spacer(),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1.5),
                      decoration: BoxDecoration(
                        color: statusColor.withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(4),
                        border: Border.all(color: statusColor.withValues(alpha: 0.3)),
                      ),
                      child: Text(
                        statusLabel,
                        style: TextStyle(
                          color: statusColor,
                          fontSize: 9.5,
                          fontWeight: FontWeight.w800,
                          letterSpacing: 0.3,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 6),

                // Name
                Text(
                  name,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 14,
                    fontWeight: FontWeight.w700,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 3),

                // Description
                Expanded(
                  child: Text(
                    description.isNotEmpty ? description : 'Kịch bản SOP tự động hóa quy trình chuyên biệt.',
                    style: const TextStyle(
                      color: AppTheme.textMutedDark,
                      fontSize: 12,
                      height: 1.3,
                    ),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                const SizedBox(height: 4),

                // Bottom Footer
                Container(
                  padding: const EdgeInsets.only(top: 4),
                  decoration: BoxDecoration(
                    border: Border(
                      top: BorderSide(color: Colors.white.withValues(alpha: 0.05)),
                    ),
                  ),
                  child: Row(
                    children: [
                      Icon(Icons.check_circle_rounded, size: 12, color: statusColor),
                      const SizedBox(width: 3.5),
                      Text(
                        'Độ tin cậy: ${successRate.toInt()}%',
                        style: TextStyle(
                          color: statusColor,
                          fontSize: 11.5,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      const Spacer(),
                      if (tools.isNotEmpty) ...[
                        const Icon(Icons.extension_outlined, size: 11, color: AppTheme.textMutedDark),
                        const SizedBox(width: 3),
                        Text(
                          '${tools.length} tools',
                          style: const TextStyle(fontSize: 11, color: AppTheme.textMutedDark),
                        ),
                        const SizedBox(width: 4),
                      ],
                      Icon(
                        isSelected ? Icons.arrow_back_ios_new_rounded : Icons.arrow_forward_ios_rounded,
                        size: 10,
                        color: isSelected ? AppTheme.primaryLight : AppTheme.textMutedDark,
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
