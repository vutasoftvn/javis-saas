import 'package:flutter/material.dart';

class AgentOrgChartWidget extends StatelessWidget {
  final Map<String, dynamic> orgChartData;
  final Function(String agentKey)? onSelectAgent;

  const AgentOrgChartWidget({
    super.key,
    required this.orgChartData,
    this.onSelectAgent,
  });

  @override
  Widget build(BuildContext context) {
    final founder = orgChartData['founder'] ?? {
      'name': 'Founder / CEO',
      'role': 'Chief Executive Officer',
      'key': 'founder',
    };

    final chiefOfStaff = orgChartData['chief_of_staff'] ?? {
      'name': 'Founder Copilot',
      'role': 'Chief of Staff',
      'key': 'founder_copilot',
    };

    final List<dynamic> departmentLeads = orgChartData['department_leads'] ?? [
      {'name': 'CFO Agent', 'role': 'Finance & Cashflow Lead', 'department': 'Finance', 'key': 'cfo_agent'},
      {'name': 'CMO Agent', 'role': 'Marketing & Growth Lead', 'department': 'Marketing', 'key': 'cmo_agent'},
      {'name': 'Sales Lead Agent', 'role': 'Sales & Pipeline Closer', 'department': 'Sales', 'key': 'sales_agent'},
      {'name': 'Tech Lead Agent', 'role': 'Architecture & Engineering Lead', 'department': 'Engineering', 'key': 'tech_lead_agent'},
      {'name': 'Legal Officer Agent', 'role': 'Compliance & Contracts Lead', 'department': 'Legal', 'key': 'legal_agent'},
      {'name': 'HR Lead Agent', 'role': 'People & Culture Lead', 'department': 'HR', 'key': 'hr_agent'},
    ];

    return InteractiveViewer(
      constrained: false,
      boundaryMargin: const EdgeInsets.all(100),
      minScale: 0.4,
      maxScale: 2.0,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 40, horizontal: 60),
        child: Column(
          children: [
            // Level 0: Founder Node
            _buildNode(
              title: founder['name'] ?? 'Founder',
              subtitle: founder['role'] ?? 'Founder & CEO',
              icon: Icons.person_pin_rounded,
              color: const Color(0xFF8B5CF6),
              isRoot: true,
              agentKey: founder['key'] ?? 'founder',
            ),

            _buildVerticalLine(height: 36),

            // Level 1: Chief of Staff / Executive Assistant Node
            _buildNode(
              title: chiefOfStaff['name'] ?? 'Founder Copilot',
              subtitle: chiefOfStaff['role'] ?? 'Executive Assistant',
              icon: Icons.stars_rounded,
              color: const Color(0xFF6366F1),
              agentKey: chiefOfStaff['key'] ?? 'founder_copilot',
            ),

            _buildVerticalLine(height: 36),

            // Level 2: Horizontal Bar & Department Leads Grid
            Container(
              decoration: BoxDecoration(
                border: Border(
                  top: BorderSide(color: Colors.blueAccent.withValues(alpha: 0.6), width: 2),
                ),
              ),
              padding: const EdgeInsets.only(top: 24),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: departmentLeads.map((lead) {
                  return Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    child: Column(
                      children: [
                        _buildNode(
                          title: lead['name'] ?? 'Lead Agent',
                          subtitle: lead['role'] ?? 'Lead',
                          tag: lead['department'],
                          icon: _getDeptIcon(lead['department']),
                          color: _getDeptColor(lead['department']),
                          agentKey: lead['key'] ?? '',
                        ),
                      ],
                    ),
                  );
                }).toList(),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildNode({
    required String title,
    required String subtitle,
    String? tag,
    required IconData icon,
    required Color color,
    bool isRoot = false,
    required String agentKey,
  }) {
    return InkWell(
      onTap: () {
        if (onSelectAgent != null && agentKey.isNotEmpty) {
          onSelectAgent!(agentKey);
        }
      },
      borderRadius: BorderRadius.circular(14),
      child: Container(
        width: 220,
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: const Color(0xFF1E293B),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: color.withValues(alpha: isRoot ? 0.8 : 0.4),
            width: isRoot ? 2 : 1.2,
          ),
          boxShadow: [
            BoxShadow(
              color: color.withValues(alpha: isRoot ? 0.2 : 0.1),
              blurRadius: isRoot ? 14 : 8,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: color.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Icon(icon, color: color, size: 20),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        title,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 13.5,
                          fontWeight: FontWeight.w700,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      Text(
                        subtitle,
                        style: TextStyle(
                          color: Colors.grey.shade400,
                          fontSize: 11,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ),
                ),
              ],
            ),
            if (tag != null) ...[
              const SizedBox(height: 10),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  tag,
                  style: TextStyle(fontSize: 10, color: color, fontWeight: FontWeight.w600),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildVerticalLine({double height = 30}) {
    return Container(
      width: 2,
      height: height,
      color: Colors.blueAccent.withValues(alpha: 0.5),
    );
  }

  IconData _getDeptIcon(String? dept) {
    switch ((dept ?? '').toLowerCase()) {
      case 'finance':
        return Icons.account_balance_wallet_outlined;
      case 'marketing':
        return Icons.campaign_outlined;
      case 'sales':
        return Icons.trending_up;
      case 'engineering':
      case 'tech':
        return Icons.code_rounded;
      case 'legal':
        return Icons.gavel_rounded;
      default:
        return Icons.groups_outlined;
    }
  }

  Color _getDeptColor(String? dept) {
    switch ((dept ?? '').toLowerCase()) {
      case 'finance':
        return const Color(0xFF0D9488);
      case 'marketing':
        return const Color(0xFFEC4899);
      case 'sales':
        return const Color(0xFFF59E0B);
      case 'engineering':
      case 'tech':
        return const Color(0xFF3B82F6);
      case 'legal':
        return const Color(0xFF8B5CF6);
      default:
        return const Color(0xFF6366F1);
    }
  }
}
