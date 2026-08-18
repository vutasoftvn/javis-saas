import 'package:flutter/material.dart';

class AgentCard extends StatelessWidget {
  final Map<String, dynamic> agent;
  final VoidCallback onTestRun;
  final VoidCallback? onDetails;
  final VoidCallback? onToggleStatus;

  const AgentCard({
    super.key,
    required this.agent,
    required this.onTestRun,
    this.onDetails,
    this.onToggleStatus,
  });

  Color _getStatusColor(String? status) {
    switch ((status ?? 'idle').toLowerCase()) {
      case 'busy':
      case 'running':
        return Colors.blueAccent;
      case 'idle':
      case 'active':
        return const Color(0xFF10B981); // Emerald
      case 'paused':
        return Colors.amber;
      case 'error':
        return Colors.redAccent;
      default:
        return Colors.grey;
    }
  }

  Color _getDepartmentColor(String? dept) {
    switch ((dept ?? '').toLowerCase()) {
      case 'finance':
        return const Color(0xFF0D9488); // Teal
      case 'marketing':
        return const Color(0xFFEC4899); // Pink
      case 'sales':
        return const Color(0xFFF59E0B); // Amber
      case 'engineering':
      case 'tech':
        return const Color(0xFF3B82F6); // Blue
      case 'legal':
        return const Color(0xFF8B5CF6); // Purple
      default:
        return const Color(0xFF6366F1); // Indigo
    }
  }

  IconData _getDepartmentIcon(String? dept) {
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
        return Icons.smart_toy_outlined;
    }
  }

  @override
  Widget build(BuildContext context) {
    final name = agent['name']?.toString() ?? 'Unnamed Agent';
    final roleTitle = agent['role_title']?.toString() ?? agent['role']?.toString() ?? 'Specialist Agent';
    final department = agent['department']?.toString() ?? 'General';
    final status = agent['status']?.toString() ?? 'idle';
    final modelProfile = agent['default_model_profile']?.toString() ?? 'reasoning';
    final riskLevel = agent['risk_level']?.toString() ?? '1';
    final statusColor = _getStatusColor(status);
    final deptColor = _getDepartmentColor(department);

    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: status == 'busy' ? Colors.blueAccent.withValues(alpha: 0.6) : const Color(0xFF334155),
          width: status == 'busy' ? 1.5 : 1,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.2),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
          if (status == 'busy')
            BoxShadow(
              color: Colors.blueAccent.withValues(alpha: 0.15),
              blurRadius: 16,
              spreadRadius: 1,
            ),
        ],
      ),
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header: Avatar, Name, Status Badge
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 46,
                height: 46,
                decoration: BoxDecoration(
                  color: deptColor.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: deptColor.withValues(alpha: 0.4), width: 1.5),
                ),
                child: Icon(_getDepartmentIcon(department), color: deptColor, size: 24),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      name,
                      style: const TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w700,
                        color: Colors.white,
                        letterSpacing: -0.2,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 2),
                    Text(
                      roleTitle,
                      style: TextStyle(
                        fontSize: 12.5,
                        color: Colors.grey.shade400,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ),
              ),
              // Status Indicator Dot & Text
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
                decoration: BoxDecoration(
                  color: statusColor.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: statusColor.withValues(alpha: 0.3)),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      width: 7,
                      height: 7,
                      decoration: BoxDecoration(
                        color: statusColor,
                        shape: BoxShape.circle,
                        boxShadow: [
                          BoxShadow(color: statusColor.withValues(alpha: 0.6), blurRadius: 4),
                        ],
                      ),
                    ),
                    const SizedBox(width: 5),
                    Text(
                      status.toUpperCase(),
                      style: TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.w700,
                        color: statusColor,
                        letterSpacing: 0.5,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),

          const SizedBox(height: 16),

          // Badges: Department, Model Profile, Risk Level
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: [
              _buildBadge(
                label: department,
                icon: Icons.domain,
                color: deptColor,
              ),
              _buildBadge(
                label: modelProfile.toUpperCase(),
                icon: Icons.psychology_outlined,
                color: const Color(0xFF60A5FA),
              ),
              _buildBadge(
                label: 'R$riskLevel Risk',
                icon: Icons.shield_outlined,
                color: int.tryParse(riskLevel) != null && int.parse(riskLevel) >= 3
                    ? Colors.amber.shade400
                    : Colors.grey.shade400,
              ),
            ],
          ),

          const Spacer(),
          const Divider(color: Color(0xFF334155), height: 24),

          // Footer: Action Buttons
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: onTestRun,
                  icon: const Icon(Icons.play_arrow_rounded, size: 18, color: Colors.blueAccent),
                  label: const Text(
                    'Test Run',
                    style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600, color: Colors.white),
                  ),
                  style: OutlinedButton.styleFrom(
                    side: const BorderSide(color: Color(0xFF475569)),
                    padding: const EdgeInsets.symmetric(vertical: 10),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                    backgroundColor: const Color(0xFF0F172A).withValues(alpha: 0.6),
                  ),
                ),
              ),
              if (onDetails != null) ...[
                const SizedBox(width: 8),
                IconButton(
                  tooltip: 'Xem cấu hình chi tiết',
                  onPressed: onDetails,
                  icon: const Icon(Icons.settings_outlined, size: 18, color: Colors.grey),
                  style: IconButton.styleFrom(
                    backgroundColor: const Color(0xFF0F172A).withValues(alpha: 0.6),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(8),
                      side: const BorderSide(color: Color(0xFF475569)),
                    ),
                  ),
                ),
              ],
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildBadge({required String label, required IconData icon, required Color color}) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3.5),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: color.withValues(alpha: 0.2)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 12, color: color),
          const SizedBox(width: 4),
          Text(
            label,
            style: TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w500,
              color: color,
            ),
          ),
        ],
      ),
    );
  }
}
