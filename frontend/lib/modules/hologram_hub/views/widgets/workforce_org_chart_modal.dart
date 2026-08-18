import 'package:flutter/material.dart';
import '../../presentation/widgets/glass_card.dart';

class WorkforceOrgChartModal extends StatelessWidget {
  final List<Map<String, dynamic>> agents;
  final Map<String, dynamic>? orgChart;
  final VoidCallback onClose;

  // Phase 6: Stage Roster context
  final String? currentStageCode;
  final List<Map<String, dynamic>>? stageRoster;
  final Map<String, dynamic>? stageRosterMeta;

  const WorkforceOrgChartModal({
    super.key,
    required this.agents,
    this.orgChart,
    required this.onClose,
    this.currentStageCode,
    this.stageRoster,
    this.stageRosterMeta,
  });

  static void show(BuildContext context, {
    required List<Map<String, dynamic>> agents,
    Map<String, dynamic>? orgChart,
    // Phase 6 params
    String? currentStageCode,
    List<Map<String, dynamic>>? stageRoster,
    Map<String, dynamic>? stageRosterMeta,
  }) {
    showDialog(
      context: context,
      barrierColor: Colors.black.withValues(alpha: 0.75),
      builder: (ctx) => Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1000, maxHeight: 720),
          child: WorkforceOrgChartModal(
            agents: agents,
            orgChart: orgChart,
            onClose: () => Navigator.of(ctx).pop(),
            currentStageCode: currentStageCode,
            stageRoster: stageRoster,
            stageRosterMeta: stageRosterMeta,
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    // Group agents by department
    final Map<String, List<Map<String, dynamic>>> grouped = {};
    for (final agent in agents) {
      final dept = (agent['department'] as String?) ?? 'Khác';
      grouped.putIfAbsent(dept, () => []).add(agent);
    }

    final totalAgents = agents.length;
    final activeCount = agents.where((a) => a['status'] == 'active' || a['status'] == 'busy' || a['enabled'] == true).length;

    return Material(
      color: Colors.transparent,
      child: GlassCard(
        borderRadius: 20,
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Header Bar
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: const Color(0xFF14B8A6).withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(
                      color: const Color(0xFF14B8A6).withValues(alpha: 0.4),
                    ),
                  ),
                  child: const Icon(
                    Icons.account_tree_outlined,
                    color: Color(0xFF14B8A6),
                    size: 24,
                  ),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Đội Ngũ AI Agent & Sơ Đồ Tổ Chức (Workforce Control Plane)',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                          letterSpacing: 0.5,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'Tổng số: $totalAgents Agents • Đang hoạt động: $activeCount • 6 Phòng ban chuyên môn',
                        style: const TextStyle(
                          color: Color(0xFF94A3B8),
                          fontSize: 13,
                        ),
                      ),
                    ],
                  ),
                ),
                IconButton(
                  onPressed: onClose,
                  icon: const Icon(Icons.close, color: Color(0xFF94A3B8)),
                  tooltip: 'Đóng',
                ),
              ],
            ),
            const SizedBox(height: 20),
            const Divider(color: Color(0xFF1E293B), height: 1),
            const SizedBox(height: 16),

            // Main Content: Department Sections
            Expanded(
              child: grouped.isEmpty
                  ? const Center(
                      child: Text(
                        'Chưa có dữ liệu Agent. Đang tải...',
                        style: TextStyle(color: Color(0xFF64748B)),
                      ),
                    )
                  : ListView(
                      children: grouped.entries.map((entry) {
                        return _buildDepartmentSection(context, entry.key, entry.value);
                      }).toList(),
                    ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDepartmentSection(
    BuildContext context,
    String department,
    List<Map<String, dynamic>> deptAgents,
  ) {
    Color deptColor = const Color(0xFF14B8A6);
    IconData deptIcon = Icons.business_center_outlined;

    switch (department.toLowerCase()) {
      case 'strategy':
      case 'chiến lược':
        deptColor = const Color(0xFFA855F7);
        deptIcon = Icons.military_tech_outlined;
        break;
      case 'finance':
      case 'tài chính':
        deptColor = const Color(0xFF10B981);
        deptIcon = Icons.account_balance_wallet_outlined;
        break;
      case 'product':
      case 'sản phẩm':
        deptColor = const Color(0xFF38BDF8);
        deptIcon = Icons.widgets_outlined;
        break;
      case 'tech':
      case 'công nghệ':
        deptColor = const Color(0xFF6366F1);
        deptIcon = Icons.terminal_outlined;
        break;
      case 'operations':
      case 'vận hành':
        deptColor = const Color(0xFFF59E0B);
        deptIcon = Icons.settings_suggest_outlined;
        break;
      case 'marketing':
      case 'tiếp thị':
        deptColor = const Color(0xFFEC4899);
        deptIcon = Icons.campaign_outlined;
        break;
    }

    return Padding(
      padding: const EdgeInsets.only(bottom: 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Department Title Badge
          Row(
            children: [
              Icon(deptIcon, size: 18, color: deptColor),
              const SizedBox(width: 8),
              Text(
                department.toUpperCase(),
                style: TextStyle(
                  color: deptColor,
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                  letterSpacing: 1.2,
                ),
              ),
              const SizedBox(width: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(
                  color: deptColor.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Text(
                  '${deptAgents.length} Agents',
                  style: TextStyle(color: deptColor, fontSize: 11, fontWeight: FontWeight.w600),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),

          // Agents Grid in this Department
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: deptAgents.map((agent) => _buildAgentCard(context, agent, deptColor)).toList(),
          ),
        ],
      ),
    );
  }

  Widget _buildAgentCard(BuildContext context, Map<String, dynamic> agent, Color accentColor) {
    final name = (agent['name'] as String?) ?? 'Unnamed Agent';
    final role = (agent['role_title'] as String?) ?? (agent['key'] as String?) ?? 'Specialist';
    final isEnabled = agent['enabled'] == true;
    final status = (agent['status'] as String?) ?? 'idle';
    final riskLevel = (agent['risk_level'] as num?)?.toInt() ?? 1;
    final modelProfile = (agent['default_model_profile'] as String?) ?? 'reasoning';

    return Container(
      width: 290,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A).withValues(alpha: 0.7),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: accentColor.withValues(alpha: 0.25),
          width: 1,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.3),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              CircleAvatar(
                radius: 18,
                backgroundColor: accentColor.withValues(alpha: 0.2),
                child: Text(
                  name.isNotEmpty ? name.substring(0, 1).toUpperCase() : 'A',
                  style: TextStyle(color: accentColor, fontWeight: FontWeight.bold, fontSize: 14),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      name,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    Text(
                      role,
                      style: const TextStyle(
                        color: Color(0xFF94A3B8),
                        fontSize: 11,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ),
              ),
              // Status dot
              Container(
                width: 8,
                height: 8,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: isEnabled
                      ? (status == 'busy' ? const Color(0xFFF59E0B) : const Color(0xFF10B981))
                      : const Color(0xFF64748B),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          const Divider(color: Color(0xFF1E293B), height: 1),
          const SizedBox(height: 10),

          // Metadata badges
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              _buildBadge('Model: $modelProfile', const Color(0xFF38BDF8)),
              _buildBadge('Risk: R$riskLevel', riskLevel >= 3 ? const Color(0xFFEF4444) : const Color(0xFF10B981)),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildBadge(String text, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Text(
        text,
        style: TextStyle(color: color, fontSize: 10, fontWeight: FontWeight.w600),
      ),
    );
  }
}
