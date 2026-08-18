import 'package:flutter/material.dart';
import '../../../../core/theme/app_theme.dart';
import '../controllers/ai_team_controller.dart';

class AiTeamApprovalBanner extends StatelessWidget {
  final AiTeamController controller;

  const AiTeamApprovalBanner({
    super.key,
    required this.controller,
  });

  Color _getRiskColor(String risk) {
    switch (risk.toUpperCase()) {
      case 'CRITICAL':
        return AppTheme.error;
      case 'HIGH':
        return const Color(0xFFF97316);
      case 'MEDIUM':
        return AppTheme.warning;
      default:
        return AppTheme.success;
    }
  }

  @override
  Widget build(BuildContext context) {
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
                        Text(
                          action,
                          style: const TextStyle(
                            fontWeight: FontWeight.w600,
                            color: AppTheme.textDark,
                            fontSize: 13,
                          ),
                        ),
                        Text(
                          reason,
                          style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 11),
                        ),
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
}
