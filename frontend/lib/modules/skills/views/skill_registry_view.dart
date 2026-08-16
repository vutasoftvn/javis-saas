import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/skill_registry_controller.dart';
import 'widgets/add_skill_candidate_dialog.dart';
import 'widgets/skill_detail_dialog.dart';

class SkillRegistryView extends StatelessWidget {
  const SkillRegistryView({super.key});

  @override
  Widget build(BuildContext context) {
    final controller = Get.put(SkillRegistryController());

    return Scaffold(
      backgroundColor: const Color(0xFF060A14),
      body: Column(
        children: [
          // ── Header Bar ──────────────────────────────────────────
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 18),
            decoration: BoxDecoration(
              color: const Color(0xFF090E1B),
              border: Border(
                bottom: BorderSide(
                  color: const Color(0xFF00E5FF).withValues(alpha: 0.15),
                ),
              ),
            ),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: const Color(0xFF00E5FF).withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(
                      color: const Color(0xFF00E5FF).withValues(alpha: 0.3),
                    ),
                  ),
                  child: const Icon(
                    Icons.psychology_outlined,
                    color: Color(0xFF00E5FF),
                    size: 22,
                  ),
                ),
                const SizedBox(width: 14),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Skill Registry & Vòng đời Kỹ năng AI (P5)',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 18,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      'Quản trị Kỹ năng: Candidate ➔ Evaluation ➔ Admin Approval ➔ Active (§61/§62)',
                      style: TextStyle(
                        color: Colors.white.withValues(alpha: 0.6),
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
                const Spacer(),
                // Add skill candidate button
                ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF00E5FF),
                    foregroundColor: Colors.black,
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  ),
                  icon: const Icon(Icons.add_task, size: 16),
                  label: const Text(
                    'Đăng ký Kỹ năng Mới',
                    style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700),
                  ),
                  onPressed: () => AddSkillCandidateDialog.show(context),
                ),
              ],
            ),
          ),

          // ── Lifecycle Metric Cards ──────────────────────────────
          Obx(() {
            final candidateCount = controller.countByStatus('candidate');
            final evalCount = controller.countByStatus('evaluation');
            final activeCount = controller.countByStatus('active');
            final deprecatedCount = controller.countByStatus('deprecated');
            final avgSuccess = (controller.averageSuccessRate * 100).toInt();

            return Container(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
              color: const Color(0xFF0B1222),
              child: Row(
                children: [
                  _buildStatusPill('Tất cả', '${controller.skills.length}', Colors.white, 'ALL', controller),
                  const SizedBox(width: 10),
                  _buildStatusPill('Candidate (Ứng viên)', '$candidateCount', const Color(0xFFF59E0B), 'candidate', controller),
                  const SizedBox(width: 10),
                  _buildStatusPill('Evaluation (Đang test)', '$evalCount', const Color(0xFF00E5FF), 'evaluation', controller),
                  const SizedBox(width: 10),
                  _buildStatusPill('Active (Chính thức)', '$activeCount', const Color(0xFF10B981), 'active', controller),
                  const SizedBox(width: 10),
                  _buildStatusPill('Deprecated (Đã ngưng)', '$deprecatedCount', const Color(0xFFEF4444), 'deprecated', controller),
                  const Spacer(),
                  // Avg Success Rate indicator
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    decoration: BoxDecoration(
                      color: const Color(0xFF10B981).withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: const Color(0xFF10B981).withValues(alpha: 0.3)),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.speed, size: 14, color: Color(0xFF34D399)),
                        const SizedBox(width: 6),
                        Text(
                          'Success Avg: $avgSuccess%',
                          style: const TextStyle(
                            color: Color(0xFF34D399),
                            fontSize: 11,
                            fontWeight: FontWeight.w700,
                            fontFamily: 'monospace',
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 12),
                  // Search box
                  SizedBox(
                    width: 220,
                    height: 36,
                    child: TextField(
                      style: const TextStyle(color: Colors.white, fontSize: 12),
                      decoration: InputDecoration(
                        hintText: 'Tìm kiếm kỹ năng, SOP...',
                        hintStyle: const TextStyle(color: Color(0xFF64748B), fontSize: 12),
                        prefixIcon: const Icon(Icons.search, size: 16, color: Color(0xFF64748B)),
                        filled: true,
                        fillColor: const Color(0xFF131B2E),
                        contentPadding: EdgeInsets.zero,
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(8),
                          borderSide: BorderSide(color: Colors.white.withValues(alpha: 0.1)),
                        ),
                      ),
                      onChanged: (val) => controller.searchQuery.value = val,
                    ),
                  ),
                ],
              ),
            );
          }),

          // ── Domain Filter Tabs ──────────────────────────────────
          Obx(() {
            return Container(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 8),
              color: const Color(0xFF090E1B),
              child: SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: controller.domains.map((dom) {
                    final isSelected = controller.selectedDomain.value == dom;
                    String label = dom.toUpperCase();
                    if (dom == 'ALL') label = 'TẤT CẢ LĨNH VỰC';
                    if (dom == 'sales') label = 'BÁN HÀNG & CRM';
                    if (dom == 'marketing') label = 'MARKETING & LEADS';
                    if (dom == 'finance') label = 'TÀI CHÍNH TT58';
                    if (dom == 'legal') label = 'PHÁP LÝ & HỢP ĐỒNG';
                    if (dom == 'operations') label = 'VẬN HÀNH';
                    if (dom == 'tech') label = 'KỸ THUẬT';

                    return Padding(
                      padding: const EdgeInsets.only(right: 8),
                      child: FilterChip(
                        label: Text(label),
                        labelStyle: TextStyle(
                          color: isSelected ? Colors.black : const Color(0xFF94A3B8),
                          fontSize: 10,
                          fontWeight: isSelected ? FontWeight.w800 : FontWeight.w500,
                        ),
                        selected: isSelected,
                        selectedColor: const Color(0xFF00E5FF),
                        backgroundColor: const Color(0xFF131B2E),
                        onSelected: (selected) {
                          controller.selectedDomain.value = dom;
                        },
                      ),
                    );
                  }).toList(),
                ),
              ),
            );
          }),

          // ── Skills Grid / List ──────────────────────────────────
          Expanded(
            child: Obx(() {
              if (controller.isLoading.value && controller.skills.isEmpty) {
                return const Center(
                  child: CircularProgressIndicator(color: Color(0xFF00E5FF)),
                );
              }

              final filtered = controller.filteredSkills;

              if (filtered.isEmpty) {
                return Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.psychology, size: 48, color: Colors.white.withValues(alpha: 0.15)),
                      const SizedBox(height: 12),
                      const Text(
                        'Không có kỹ năng nào trong danh mục này',
                        style: TextStyle(color: Color(0xFF64748B), fontSize: 13),
                      ),
                      const SizedBox(height: 12),
                      OutlinedButton(
                        onPressed: () => AddSkillCandidateDialog.show(context),
                        child: const Text('Đăng ký Kỹ năng Mới'),
                      ),
                    ],
                  ),
                );
              }

              return Padding(
                padding: const EdgeInsets.all(24),
                child: GridView.builder(
                  gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: 3,
                    childAspectRatio: 1.5,
                    crossAxisSpacing: 16,
                    mainAxisSpacing: 16,
                  ),
                  itemCount: filtered.length,
                  itemBuilder: (context, index) {
                    final skill = filtered[index];
                    return _buildSkillCard(context, skill, controller);
                  },
                ),
              );
            }),
          ),
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
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: isSelected ? color.withValues(alpha: 0.18) : const Color(0xFF131B2E),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: isSelected ? color : const Color(0xFF1E293B),
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 8,
              height: 8,
              decoration: BoxDecoration(color: color, shape: BoxShape.circle),
            ),
            const SizedBox(width: 8),
            Text(
              label,
              style: TextStyle(
                color: isSelected ? Colors.white : const Color(0xFF94A3B8),
                fontSize: 11,
                fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
              ),
            ),
            const SizedBox(width: 6),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
              decoration: BoxDecoration(
                color: color.withValues(alpha: 0.2),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Text(
                count,
                style: TextStyle(
                  color: color,
                  fontSize: 10,
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
  ) {
    final name = skill['name']?.toString() ?? 'Skill';
    final domain = (skill['domain']?.toString() ?? 'general').toUpperCase();
    final status = (skill['status']?.toString() ?? 'candidate').toLowerCase();
    final version = skill['version']?.toString() ?? 'v1.0.0';
    final description = skill['description']?.toString() ?? '';
    final successRate = ((skill['success_rate'] as num?)?.toDouble() ?? 0.0) * 100;
    final usageCount = (skill['usage_count'] as num?)?.toInt() ?? 0;
    final tools = (skill['tool_permissions'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [];

    Color statusColor = const Color(0xFF94A3B8);
    if (status == 'candidate') statusColor = const Color(0xFFF59E0B);
    if (status == 'evaluation') statusColor = const Color(0xFF00E5FF);
    if (status == 'active') statusColor = const Color(0xFF10B981);
    if (status == 'deprecated') statusColor = const Color(0xFFEF4444);

    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFF1E293B)),
      ),
      child: InkWell(
        onTap: () => SkillDetailDialog.show(context, skill),
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Top Row
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                    decoration: BoxDecoration(
                      color: const Color(0xFF38BDF8).withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      domain,
                      style: const TextStyle(
                        color: Color(0xFF38BDF8),
                        fontSize: 9,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                  const SizedBox(width: 6),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                    decoration: BoxDecoration(
                      color: const Color(0xFF1E293B),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      version,
                      style: const TextStyle(
                        color: Color(0xFF94A3B8),
                        fontSize: 9,
                        fontFamily: 'monospace',
                      ),
                    ),
                  ),
                  const Spacer(),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                    decoration: BoxDecoration(
                      color: statusColor.withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: statusColor.withValues(alpha: 0.3)),
                    ),
                    child: Text(
                      status.toUpperCase(),
                      style: TextStyle(
                        color: statusColor,
                        fontSize: 9,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),

              // Title
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
              const SizedBox(height: 4),

              // Description
              Expanded(
                child: Text(
                  description.isNotEmpty ? description : 'Chưa có mô tả chi tiết.',
                  style: TextStyle(
                    color: Colors.white.withValues(alpha: 0.65),
                    fontSize: 11,
                    height: 1.3,
                  ),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ),

              // Tools tag
              if (tools.isNotEmpty) ...[
                Row(
                  children: [
                    const Icon(Icons.build_outlined, size: 10, color: Color(0xFF64748B)),
                    const SizedBox(width: 4),
                    Expanded(
                      child: Text(
                        tools.join(', '),
                        style: const TextStyle(
                          color: Color(0xFF64748B),
                          fontSize: 10,
                          fontFamily: 'monospace',
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
              ],

              // Bottom Stats Row
              const Divider(color: Color(0xFF1E293B), height: 1),
              const SizedBox(height: 8),
              Row(
                children: [
                  const Icon(Icons.check_circle_outline, size: 12, color: Color(0xFF34D399)),
                  const SizedBox(width: 4),
                  Text(
                    'Success: ${successRate.toInt()}%',
                    style: const TextStyle(
                      color: Color(0xFF34D399),
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const Spacer(),
                  Text(
                    '$usageCount calls',
                    style: const TextStyle(
                      color: Color(0xFF64748B),
                      fontSize: 10,
                      fontFamily: 'monospace',
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
