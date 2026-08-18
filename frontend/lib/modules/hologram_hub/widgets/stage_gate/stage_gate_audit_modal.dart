import 'package:flutter/material.dart';
import '../../../../data/models/stage_gate_model.dart';
import '../../../../data/models/stage_model.dart';
import '../../../../shared/widgets/stage_badge.dart';

class StageGateAuditModal extends StatefulWidget {
  final int projectId;
  final ProjectStage currentStage;
  final StageGateAuditModel? audit;
  final bool isLoading;
  final VoidCallback onRunAudit;
  final Function(int auditId) onApplyTransition;

  const StageGateAuditModal({
    super.key,
    required this.projectId,
    required this.currentStage,
    required this.audit,
    this.isLoading = false,
    required this.onRunAudit,
    required this.onApplyTransition,
  });

  static void show(
    BuildContext context, {
    required int projectId,
    required ProjectStage currentStage,
    required StageGateAuditModel? audit,
    bool isLoading = false,
    required VoidCallback onRunAudit,
    required Function(int auditId) onApplyTransition,
  }) {
    showDialog(
      context: context,
      builder: (ctx) => Dialog(
        backgroundColor: Colors.transparent,
        insetPadding: const EdgeInsets.symmetric(horizontal: 40, vertical: 30),
        child: StageGateAuditModal(
          projectId: projectId,
          currentStage: currentStage,
          audit: audit,
          isLoading: isLoading,
          onRunAudit: onRunAudit,
          onApplyTransition: onApplyTransition,
        ),
      ),
    );
  }

  @override
  State<StageGateAuditModal> createState() => _StageGateAuditModalState();
}

class _StageGateAuditModalState extends State<StageGateAuditModal>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final audit = widget.audit;
    final readinessPercent = ((audit?.readinessScore ?? 0.0) * 100).toInt();
    final status = audit?.auditStatus ?? AuditStatus.rejected;
    final passedCriteria = audit?.passedCriteria ?? [];
    final missingCriteria = audit?.missingCriteria ?? [];
    final risks = audit?.detectedRisks ?? [];
    final isAdvancementEligible = status == AuditStatus.approved || status == AuditStatus.conditionallyApproved;

    return Container(
      width: 960,
      height: 680,
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: status.color.withValues(alpha: 0.5), width: 1.5),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.6),
            blurRadius: 30,
            spreadRadius: 5,
          ),
        ],
      ),
      child: Column(
        children: [
          // Header
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
            decoration: BoxDecoration(
              color: const Color(0xFF1E293B).withValues(alpha: 0.7),
              borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
              border: const Border(bottom: BorderSide(color: Colors.white12)),
            ),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: status.color.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Icon(Icons.verified_user_outlined, color: status.color, size: 22),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Phiên Thẩm Định Chuyển Giai Đoạn (Stage Gate Auditor)',
                        style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
                        overflow: TextOverflow.ellipsis,
                      ),
                      const SizedBox(height: 2),
                      Text(
                        'Kiểm tra nghiêm ngặt tiêu chí Evidence Gates & Hàng rào chống Premature Scaling',
                        style: TextStyle(color: Colors.white.withValues(alpha: 0.6), fontSize: 12),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 12),
                StageBadge(stage: widget.currentStage, showFullName: true),
                const SizedBox(width: 12),
                IconButton(
                  icon: const Icon(Icons.close, color: Colors.white70),
                  onPressed: () => Navigator.of(context).pop(),
                ),
              ],
            ),
          ),

          // Scorecard Summary Bar
          Container(
            padding: const EdgeInsets.all(20),
            color: const Color(0xFF1E293B).withValues(alpha: 0.4),
            child: Row(
              children: [
                // Gauge
                Container(
                  width: 90,
                  height: 90,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: status.color.withValues(alpha: 0.1),
                    border: Border.all(color: status.color, width: 3),
                  ),
                  child: Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          '$readinessPercent%',
                          style: TextStyle(color: status.color, fontSize: 20, fontWeight: FontWeight.bold),
                        ),
                        Text(
                          'Sẵn sàng',
                          style: TextStyle(color: Colors.white.withValues(alpha: 0.6), fontSize: 9),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(width: 20),

                // Status & Recommendation
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Wrap(
                        crossAxisAlignment: WrapCrossAlignment.center,
                        spacing: 10,
                        runSpacing: 6,
                        children: [
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                            decoration: BoxDecoration(
                              color: status.color.withValues(alpha: 0.2),
                              borderRadius: BorderRadius.circular(6),
                              border: Border.all(color: status.color.withValues(alpha: 0.4)),
                            ),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(status.icon, color: status.color, size: 14),
                                const SizedBox(width: 6),
                                Flexible(
                                  child: Text(
                                    status.labelVi,
                                    style: TextStyle(color: status.color, fontSize: 12, fontWeight: FontWeight.bold),
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                ),
                              ],
                            ),
                          ),
                          if (audit != null)
                            Text(
                              'Đích đến: ${audit.toStage}',
                              style: const TextStyle(color: Color(0xFF38BDF8), fontSize: 12, fontWeight: FontWeight.w600),
                            ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Text(
                        audit?.recommendationNote ?? 'Bấm "Chạy Thẩm Định Lại" để quét dữ liệu thực tế.',
                        style: const TextStyle(color: Colors.white70, fontSize: 12, height: 1.4),
                      ),
                    ],
                  ),
                ),

                // Actions
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    ElevatedButton.icon(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF38BDF8),
                        foregroundColor: Colors.black,
                        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                      ),
                      onPressed: widget.isLoading ? null : widget.onRunAudit,
                      icon: widget.isLoading
                          ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black))
                          : const Icon(Icons.refresh, size: 16),
                      label: const Text('Thẩm Định Lại', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12)),
                    ),
                    const SizedBox(height: 8),
                    if (isAdvancementEligible && audit != null)
                      ElevatedButton.icon(
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF10B981),
                          foregroundColor: Colors.black,
                          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                        ),
                        onPressed: () {
                          widget.onApplyTransition(audit.id);
                          Navigator.of(context).pop();
                        },
                        icon: const Icon(Icons.upgrade, size: 16),
                        label: const Text('Nâng Cấp Stage', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12)),
                      ),
                  ],
                ),
              ],
            ),
          ),

          // Tabs
          Container(
            color: const Color(0xFF1E293B),
            child: TabBar(
              controller: _tabController,
              indicatorColor: status.color,
              indicatorWeight: 3,
              labelColor: Colors.white,
              unselectedLabelColor: Colors.white60,
              labelStyle: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold),
              tabs: [
                Tab(
                  icon: const Icon(Icons.check_circle_outline, color: Color(0xFF10B981), size: 16),
                  text: 'Tiêu Chí Đạt (${passedCriteria.length})',
                ),
                Tab(
                  icon: const Icon(Icons.highlight_off, color: Color(0xFFEF4444), size: 16),
                  text: 'Tiêu Chí Còn Thiếu (${missingCriteria.length})',
                ),
                Tab(
                  icon: const Icon(Icons.warning_amber_rounded, color: Color(0xFFF59E0B), size: 16),
                  text: 'Rủi Ro Premature (${risks.length})',
                ),
              ],
            ),
          ),

          // Content
          Expanded(
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: TabBarView(
                controller: _tabController,
                children: [
                  // Tab 1: Passed Criteria
                  passedCriteria.isEmpty
                      ? const Center(
                          child: Text('Chưa có tiêu chí nào đạt chuẩn', style: TextStyle(color: Colors.white38, fontSize: 12)),
                        )
                      : ListView.separated(
                          itemCount: passedCriteria.length,
                          separatorBuilder: (_, _) => const SizedBox(height: 8),
                          itemBuilder: (context, idx) {
                            final c = passedCriteria[idx];
                            return Container(
                              padding: const EdgeInsets.all(12),
                              decoration: BoxDecoration(
                                color: const Color(0xFF10B981).withValues(alpha: 0.1),
                                borderRadius: BorderRadius.circular(10),
                                border: Border.all(color: const Color(0xFF10B981).withValues(alpha: 0.3)),
                              ),
                              child: Row(
                                children: [
                                  const Icon(Icons.check_circle, color: Color(0xFF10B981), size: 18),
                                  const SizedBox(width: 10),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Text(c.title, style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.bold)),
                                        const SizedBox(height: 2),
                                        Text(c.description, style: const TextStyle(color: Colors.white70, fontSize: 11)),
                                      ],
                                    ),
                                  ),
                                ],
                              ),
                            );
                          },
                        ),

                  // Tab 2: Missing Criteria
                  missingCriteria.isEmpty
                      ? const Center(
                          child: Text('Tất cả tiêu chí đã hoàn thành xuất sắc!', style: TextStyle(color: Color(0xFF10B981), fontSize: 12, fontWeight: FontWeight.bold)),
                        )
                      : ListView.separated(
                          itemCount: missingCriteria.length,
                          separatorBuilder: (_, _) => const SizedBox(height: 8),
                          itemBuilder: (context, idx) {
                            final c = missingCriteria[idx];
                            return Container(
                              padding: const EdgeInsets.all(12),
                              decoration: BoxDecoration(
                                color: const Color(0xFFEF4444).withValues(alpha: 0.1),
                                borderRadius: BorderRadius.circular(10),
                                border: Border.all(color: const Color(0xFFEF4444).withValues(alpha: 0.3)),
                              ),
                              child: Row(
                                children: [
                                  const Icon(Icons.cancel, color: Color(0xFFEF4444), size: 18),
                                  const SizedBox(width: 10),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Text(c.title, style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.bold)),
                                        const SizedBox(height: 2),
                                        Text(c.description, style: const TextStyle(color: Colors.white70, fontSize: 11)),
                                      ],
                                    ),
                                  ),
                                ],
                              ),
                            );
                          },
                        ),

                  // Tab 3: Detected Risks
                  risks.isEmpty
                      ? const Center(
                          child: Text('Không phát hiện rủi ro mở rộng sớm nào', style: TextStyle(color: Color(0xFF10B981), fontSize: 12)),
                        )
                      : ListView.separated(
                          itemCount: risks.length,
                          separatorBuilder: (_, _) => const SizedBox(height: 8),
                          itemBuilder: (context, idx) {
                            final r = risks[idx];
                            final sev = (r['severity'] ?? 'WARNING').toString().toUpperCase();
                            final isCritical = sev == 'CRITICAL';
                            final color = isCritical ? const Color(0xFFEF4444) : const Color(0xFFF59E0B);

                            return Container(
                              padding: const EdgeInsets.all(12),
                              decoration: BoxDecoration(
                                color: color.withValues(alpha: 0.1),
                                borderRadius: BorderRadius.circular(10),
                                border: Border.all(color: color.withValues(alpha: 0.3)),
                              ),
                              child: Row(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Icon(isCritical ? Icons.dangerous : Icons.warning_amber, color: color, size: 18),
                                  const SizedBox(width: 10),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Text(
                                          r['rule_code'] ?? 'PREMATURE_RISK',
                                          style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.bold),
                                        ),
                                        const SizedBox(height: 2),
                                        Text(
                                          r['message'] ?? '',
                                          style: const TextStyle(color: Colors.white70, fontSize: 11),
                                        ),
                                      ],
                                    ),
                                  ),
                                ],
                              ),
                            );
                          },
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
