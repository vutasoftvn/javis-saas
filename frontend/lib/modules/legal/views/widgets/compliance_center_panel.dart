import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/widgets/app_toast.dart';
import '../../../../data/models/ai_compliance_models.dart';
import '../../controllers/ai_compliance_controller.dart';
import 'compliance_incident_dialog.dart';

class ComplianceCenterPanel extends StatelessWidget {
  const ComplianceCenterPanel({super.key});

  Future<String?> _promptRationale(BuildContext context, String actionTitle) async {
    final controller = TextEditingController();
    return showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF0F172A),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        title: Text(actionTitle, style: const TextStyle(color: Colors.white, fontSize: 16)),
        content: TextField(
          controller: controller,
          maxLines: 2,
          style: const TextStyle(color: Colors.white, fontSize: 14),
          decoration: const InputDecoration(
            hintText: 'Nhập lý do / căn cứ bắt buộc...',
            hintStyle: TextStyle(color: Color(0xFF64748B), fontSize: 13),
            filled: true,
            fillColor: Color(0xFF1E293B),
            border: OutlineInputBorder(),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(null),
            child: const Text('Huỷ', style: TextStyle(color: Color(0xFF94A3B8))),
          ),
          ElevatedButton(
            onPressed: () {
              final text = controller.text.trim();
              if (text.isNotEmpty) Navigator.of(ctx).pop(text);
            },
            style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF3B82F6)),
            child: const Text('Xác nhận', style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final controller = Get.put(AiComplianceController());

    return Obx(() {
      if (controller.isLoading.value) {
        return const Center(child: CircularProgressIndicator());
      }
      final data = controller.centerData.value;
      if (data == null) {
        return Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text('Chưa có thông tin tuân thủ AI', style: TextStyle(color: Color(0xFF94A3B8))),
              const SizedBox(height: 12),
              ElevatedButton(
                onPressed: () => controller.load(),
                child: const Text('Tải lại'),
              ),
            ],
          ),
        );
      }

      return SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Expanded(
                  child: Text(
                    'Trung tâm Tuân thủ AI (AI Compliance Center)',
                    style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.refresh, color: Color(0xFF38BDF8)),
                  onPressed: () => controller.load(),
                ),
              ],
            ),

            const SizedBox(height: 16),
            Row(
              children: [
                _buildStatCard('Hệ thống hoạt động', '${data.activeCount}', const Color(0xFF10B981)),
                const SizedBox(width: 12),
                _buildStatCard('Sự cố tuân thủ', '${data.incidentCount}', const Color(0xFFEF4444)),
              ],
            ),
            const SizedBox(height: 24),
            const Text(
              'Danh sách Triển khai AI',
              style: TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 12),
            ...data.deployments.map((dep) => _buildDeploymentCard(context, dep, controller)),
            if (data.recentIncidents.isNotEmpty) ...[
              const SizedBox(height: 24),
              const Text(
                'Sự cố gần đây',
                style: TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 12),
              ...data.recentIncidents.map(_buildIncidentCard),
            ],
          ],
        ),
      );
    });
  }

  Widget _buildStatCard(String title, String count, Color color) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: const Color(0xFF1E293B),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: color.withValues(alpha: 0.3)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 12)),
            const SizedBox(height: 6),
            Text(count, style: TextStyle(color: color, fontSize: 24, fontWeight: FontWeight.bold)),
          ],
        ),
      ),
    );
  }

  Widget _buildDeploymentCard(
    BuildContext context,
    AiComplianceDeployment dep,
    AiComplianceController controller,
  ) {
    final isApproved = dep.status == 'APPROVED_FOR_USE';
    final isSuspended = dep.status == 'SUSPENDED';

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: isApproved
              ? const Color(0xFF10B981).withValues(alpha: 0.3)
              : (isSuspended ? const Color(0xFFEF4444).withValues(alpha: 0.3) : const Color(0xFF334155)),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                dep.id,
                style: const TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.bold),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: isApproved
                      ? const Color(0xFF10B981).withValues(alpha: 0.2)
                      : (isSuspended ? const Color(0xFFEF4444).withValues(alpha: 0.2) : const Color(0xFF334155)),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  dep.status,
                  style: TextStyle(
                    color: isApproved
                        ? const Color(0xFF10B981)
                        : (isSuspended ? const Color(0xFFEF4444) : const Color(0xFF94A3B8)),
                    fontSize: 11,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text('Chế độ: ${dep.mode}', style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 12)),
          Text('Người quản lý: ${dep.ownerName}', style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 12)),
          if (dep.assessmentExpiresAt.isNotEmpty)
            Text('Hạn đánh giá: ${dep.assessmentExpiresAt}', style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 12)),
          const SizedBox(height: 12),
          Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              TextButton.icon(
                icon: const Icon(Icons.report_problem, size: 16, color: Color(0xFFF59E0B)),
                label: const Text('Báo sự cố', style: TextStyle(color: Color(0xFFF59E0B), fontSize: 12)),
                onPressed: () {
                  showDialog(
                    context: context,
                    builder: (ctx) => ComplianceIncidentDialog(
                      deploymentId: dep.id,
                      onSubmit: (sev, sum) => controller.reportIncident(
                        deploymentId: dep.id,
                        severity: sev,
                        summary: sum,
                      ),
                    ),
                  );
                },
              ),
              if (isApproved) ...[
                const SizedBox(width: 8),
                ElevatedButton(
                  onPressed: () async {
                    final rationale = await _promptRationale(context, 'Tạm đình chỉ triển khai AI');
                    if (rationale != null) {
                      await controller.suspendDeployment(dep.id, reason: rationale);
                    }
                  },
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFFEF4444),
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  ),
                  child: const Text('Đình chỉ', style: TextStyle(color: Colors.white, fontSize: 12)),
                ),
              ],
              if (isSuspended) ...[
                const SizedBox(width: 8),
                ElevatedButton(
                  onPressed: () async {
                    final rationale = await _promptRationale(context, 'Phục hồi triển khai AI');
                    if (rationale != null) {
                      await controller.resumeDeployment(dep.id, reason: rationale);
                    }
                  },
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF10B981),
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  ),
                  child: const Text('Phục hồi', style: TextStyle(color: Colors.white, fontSize: 12)),
                ),
              ],
              if (!isApproved && !isSuspended) ...[
                const SizedBox(width: 8),
                ElevatedButton(
                  onPressed: () async {
                    if (dep.currentAssessmentId == null ||
                        dep.currentAssessmentId!.isEmpty ||
                        dep.assessmentExpiresAt.isEmpty) {
                      AppToast.warning(
                        'Triển khai này chưa có đánh giá rủi ro (assessment) hoặc hạn đánh giá hợp lệ',
                        title: 'Chưa thể phê duyệt',
                      );
                      return;
                    }
                    final rationale = await _promptRationale(context, 'Phê duyệt triển khai AI');
                    if (rationale != null) {
                      await controller.approveDeployment(
                        dep.id,
                        assessmentId: dep.currentAssessmentId!,
                        rationale: rationale,
                        expiresAt: dep.assessmentExpiresAt,
                      );
                    }
                  },
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF3B82F6),
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  ),
                  child: const Text('Phê duyệt (Founder)', style: TextStyle(color: Colors.white, fontSize: 12)),
                ),
              ],
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildIncidentCard(AiIncidentSummary inc) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFFEF4444).withValues(alpha: 0.2)),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  inc.summary,
                  style: const TextStyle(color: Colors.white, fontSize: 13),
                ),
                const SizedBox(height: 4),
                Text(
                  '${inc.severity} • ${inc.createdAt}',
                  style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 11),
                ),
              ],
            ),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
            decoration: BoxDecoration(
              color: const Color(0xFFEF4444).withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(4),
            ),
            child: Text(
              inc.status,
              style: const TextStyle(color: Color(0xFFEF4444), fontSize: 11, fontWeight: FontWeight.bold),
            ),
          ),
        ],
      ),
    );
  }
}
