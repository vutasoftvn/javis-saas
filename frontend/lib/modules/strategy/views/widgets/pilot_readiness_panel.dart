import 'package:flutter/material.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../data/models/pilot_run_model.dart';

class PilotReadinessPanel extends StatelessWidget {
  final PilotRun pilot;
  final bool isFounderOrAdmin;
  final Function(String approvalRef)? onApprove;
  final Function(String approvalRef)? onActivate;
  final Function(String reason)? onCancel;
  final VoidCallback? onComplete;

  const PilotReadinessPanel({
    super.key,
    required this.pilot,
    this.isFounderOrAdmin = true,
    this.onApprove,
    this.onActivate,
    this.onCancel,
    this.onComplete,
  });

  void _showApprovalDialog(BuildContext context, {required bool isActivation}) {
    final textController = TextEditingController();
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppTheme.surfaceDark,
        title: Text(
          isActivation ? 'Kích Hoạt Pilot (Human Authorization)' : 'Phê Duyệt Pilot Run (Approval)',
          style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16),
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              isActivation
                  ? 'Kích hoạt pilot không thay đổi lifecycle stage. Nhập mã phê duyệt (Approval Reference) từ tài liệu quyết định của Founder:'
                  : 'Xác nhận toàn bộ điều kiện tiên quyết và hồ sơ pilot đã đầy đủ. Nhập mã phê duyệt:',
              style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 13),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: textController,
              autofocus: true,
              style: const TextStyle(color: Colors.white, fontSize: 14),
              decoration: InputDecoration(
                labelText: 'Mã phê duyệt (ví dụ: APR-2026-001)',
                labelStyle: const TextStyle(color: Color(0xFF64748B), fontSize: 13),
                filled: true,
                fillColor: const Color(0xFF0F172A),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('Hủy', style: TextStyle(color: Color(0xFF94A3B8))),
          ),
          ElevatedButton(
            onPressed: () {
              final ref = textController.text.trim();
              if (ref.isNotEmpty) {
                Navigator.of(ctx).pop();
                if (isActivation) {
                  onActivate?.call(ref);
                } else {
                  onApprove?.call(ref);
                }
              }
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: isActivation ? const Color(0xFF10B981) : const Color(0xFF38BDF8),
              foregroundColor: Colors.black,
            ),
            child: Text(isActivation ? 'Xác nhận Kích hoạt' : 'Xác nhận Phê duyệt'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final missing = pilot.missingPrerequisites;
    final isApproved = pilot.status == PilotRunStatus.approved;
    final isActive = pilot.status == PilotRunStatus.active;
    final isDraft = pilot.status == PilotRunStatus.draft;

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDark,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppTheme.borderDark),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Title & Status
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Row(
                  children: const [
                    Icon(Icons.rocket_launch_outlined, color: AppTheme.primary, size: 20),
                    SizedBox(width: 8),
                    Flexible(
                      child: Text(
                        'Pilot Readiness & Verification (P3)',
                        style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 15),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: pilot.status.color.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: pilot.status.color.withValues(alpha: 0.4)),
                ),
                child: Text(
                  pilot.status.labelVi,
                  style: TextStyle(color: pilot.status.color, fontSize: 12, fontWeight: FontWeight.bold),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),

          // Invariant Banner
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: const Color(0xFF0F172A),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: const Color(0xFF334155)),
            ),
            child: Row(
              children: const [
                Icon(Icons.info_outline, color: Color(0xFF38BDF8), size: 16),
                SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Kích hoạt pilot không thay đổi lifecycle stage (quyền kiểm soát chuyển stage thuộc về quyết định Stage Gate của Founder).',
                    style: TextStyle(color: Color(0xFF94A3B8), fontSize: 12),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),

          // Checklist items
          const Text(
            'Điều Kiện Tiên Quyết (Prerequisites):',
            style: TextStyle(color: Colors.white, fontWeight: FontWeight.w600, fontSize: 13),
          ),
          const SizedBox(height: 8),

          _buildChecklistItem(
            title: 'Design Partner Evidence đã duyệt',
            value: pilot.designPartnerEvidenceRefs.isNotEmpty
                ? '${pilot.designPartnerEvidenceRefs.length} bằng chứng (Refs: ${pilot.designPartnerEvidenceRefs.join(", ")})'
                : 'Chưa có',
            isMet: pilot.designPartnerEvidenceRefs.isNotEmpty,
          ),
          _buildChecklistItem(
            title: 'Metric Contract Artifact',
            value: pilot.metricContractArtifactRef ?? 'Chưa cấu hình',
            isMet: pilot.metricContractArtifactRef != null && pilot.metricContractArtifactRef!.trim().isNotEmpty,
          ),
          _buildChecklistItem(
            title: 'Instrumentation Plan Artifact',
            value: pilot.instrumentationArtifactRef ?? 'Chưa cấu hình',
            isMet: pilot.instrumentationArtifactRef != null && pilot.instrumentationArtifactRef!.trim().isNotEmpty,
          ),
          _buildChecklistItem(
            title: 'Pilot Onboarding Runbook',
            value: pilot.onboardingArtifactRef ?? 'Chưa cấu hình',
            isMet: pilot.onboardingArtifactRef != null && pilot.onboardingArtifactRef!.trim().isNotEmpty,
          ),
          _buildChecklistItem(
            title: 'Rollback Runbook',
            value: pilot.rollbackArtifactRef ?? 'Chưa cấu hình',
            isMet: pilot.rollbackArtifactRef != null && pilot.rollbackArtifactRef!.trim().isNotEmpty,
          ),
          _buildChecklistItem(
            title: 'Release Owner',
            value: pilot.releaseOwnerMemberId.isNotEmpty ? 'ID: ${pilot.releaseOwnerMemberId}' : 'Chưa chỉ định',
            isMet: pilot.releaseOwnerMemberId.isNotEmpty,
          ),

          // Missing Items Warning
          if (missing.isNotEmpty) ...[
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: const Color(0xFF450A0A),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: const Color(0xFFEF4444)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: const [
                      Icon(Icons.warning_amber_rounded, color: Color(0xFFEF4444), size: 16),
                      SizedBox(width: 6),
                      Text(
                        'Danh sách hạng mục còn thiếu:',
                        style: TextStyle(color: Color(0xFFFCA5A5), fontWeight: FontWeight.bold, fontSize: 12),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  ...missing.map(
                    (m) => Padding(
                      padding: const EdgeInsets.only(left: 22, bottom: 2),
                      child: Text('• $m', style: const TextStyle(color: Colors.white70, fontSize: 12)),
                    ),
                  ),
                ],
              ),
            ),
          ],

          // Approval & Activation metadata
          if (pilot.approvalRef != null) ...[
            const SizedBox(height: 12),
            Text(
              'Mã phê duyệt: ${pilot.approvalRef} (${pilot.approvedAt != null ? pilot.approvedAt!.toLocal().toString().split('.')[0] : ''})',
              style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 12),
            ),
          ],

          const SizedBox(height: 16),

          // Actions
          Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              if (isDraft && missing.isEmpty && isFounderOrAdmin)
                ElevatedButton.icon(
                  onPressed: () => _showApprovalDialog(context, isActivation: false),
                  icon: const Icon(Icons.check_circle_outline, size: 16),
                  label: const Text('Phê duyệt pilot'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF38BDF8),
                    foregroundColor: Colors.black,
                  ),
                ),
              if (isApproved && isFounderOrAdmin) ...[
                const SizedBox(width: 8),
                ElevatedButton.icon(
                  onPressed: () => _showApprovalDialog(context, isActivation: true),
                  icon: const Icon(Icons.play_arrow_rounded, size: 18),
                  label: const Text('Kích hoạt pilot'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF10B981),
                    foregroundColor: Colors.black,
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                  ),
                ),
              ],
              if (isActive && isFounderOrAdmin) ...[
                const SizedBox(width: 8),
                ElevatedButton.icon(
                  onPressed: onComplete,
                  icon: const Icon(Icons.task_alt, size: 16),
                  label: const Text('Hoàn thành pilot'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF6366F1),
                    foregroundColor: Colors.white,
                  ),
                ),
              ],
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildChecklistItem({
    required String title,
    required String value,
    required bool isMet,
  }) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            isMet ? Icons.check_circle_rounded : Icons.cancel_rounded,
            color: isMet ? const Color(0xFF10B981) : const Color(0xFFEF4444),
            size: 16,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: RichText(
              text: TextSpan(
                style: const TextStyle(fontSize: 12, color: Colors.white),
                children: [
                  TextSpan(text: '$title: ', style: const TextStyle(color: Color(0xFF94A3B8))),
                  TextSpan(
                    text: value,
                    style: TextStyle(
                      color: isMet ? Colors.white : const Color(0xFFFCA5A5),
                      fontWeight: isMet ? FontWeight.normal : FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
