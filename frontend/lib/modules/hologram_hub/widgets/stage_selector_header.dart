import 'package:flutter/material.dart';
import '../../../data/models/stage_model.dart';
import '../../../shared/widgets/stage_badge.dart';
import 'stage_policy_dialog.dart';

class StageSelectorHeader extends StatelessWidget {
  final StageContextModel? contextModel;
  final List<Map<String, dynamic>> projects;
  final int? selectedProjectId;
  final ValueChanged<int?> onProjectChanged;
  final bool isLoading;
  final VoidCallback? onOpenStrategy;
  final VoidCallback? onOpenStageGateAudit;
  final double? readinessScore;

  const StageSelectorHeader({
    super.key,
    required this.contextModel,
    this.projects = const [],
    this.selectedProjectId,
    required this.onProjectChanged,
    this.isLoading = false,
    this.onOpenStrategy,
    this.onOpenStageGateAudit,
    this.readinessScore,
  });

  @override
  Widget build(BuildContext context) {
    // 1. Resolve selected project object
    Map<String, dynamic>? selectedProject;
    if (selectedProjectId != null && projects.isNotEmpty) {
      for (final p in projects) {
        final pid = int.tryParse(p['id']?.toString() ?? '');
        if (pid == selectedProjectId) {
          selectedProject = p;
          break;
        }
      }
    }

    // 2. Resolve Title, Stage, Goal, Constraints, and Description
    final String projectTitle = selectedProject?['title']?.toString() ??
        contextModel?.projectTitle ??
        (selectedProjectId == null ? 'Toàn Doanh Nghiệp (Mặc Định)' : 'Dự Án #$selectedProjectId');

    final ProjectStage stage = selectedProject != null
        ? ProjectStage.fromString(selectedProject['project_stage']?.toString())
        : (contextModel?.projectStage ?? ProjectStage.s1ProblemValidation);

    final String stageGoal = (contextModel?.stageGoal?.trim().isNotEmpty ?? false)
        ? contextModel!.stageGoal!.trim()
        : 'Xác thực mục tiêu trọng tâm của giai đoạn ${stage.code}';

    final List<String> constraints = contextModel?.criticalConstraints ?? [];
    final String constraintText = constraints.isNotEmpty
        ? constraints.first
        : 'Cần bổ sung bằng chứng thực tế trước khi chuyển Stage';

    final policy = contextModel?.policy;
    final double effectiveReadiness = readinessScore ??
        (contextModel != null ? 0.65 : 0.0); // Default illustrative readiness if not yet audited
    final int readinessPercent = (effectiveReadiness * 100).clamp(0, 100).toInt();

    return Container(
      margin: const EdgeInsets.only(bottom: 14),
      decoration: BoxDecoration(
        color: const Color(0xFF131B2E).withValues(alpha: 0.85),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: stage.primaryColor.withValues(alpha: 0.35),
          width: 1.2,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.35),
            blurRadius: 14,
            offset: const Offset(0, 4),
          ),
          BoxShadow(
            color: stage.primaryColor.withValues(alpha: 0.08),
            blurRadius: 16,
          ),
        ],
      ),
      child: Material(
        color: Colors.transparent,
        borderRadius: BorderRadius.circular(14),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              // ── Row 1: Project Icon + Dropdown Selector + Single Stage Badge + Mini Readiness ──
              Row(
                children: [
                  // Project / Rocket Icon
                  Container(
                    padding: const EdgeInsets.all(6),
                    decoration: BoxDecoration(
                      color: stage.primaryColor.withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(
                        color: stage.primaryColor.withValues(alpha: 0.3),
                        width: 0.8,
                      ),
                    ),
                    child: Icon(
                      selectedProjectId == null ? Icons.business_outlined : Icons.rocket_launch_outlined,
                      color: stage.primaryColor,
                      size: 15,
                    ),
                  ),
                  const SizedBox(width: 8),

                  // Project Title with Popup/Dropdown Selector
                  Expanded(
                    child: PopupMenuButton<int?>(
                      tooltip: 'Chọn dự án',
                      color: const Color(0xFF0F172A),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                        side: const BorderSide(color: Color(0xFF1E293B)),
                      ),
                      offset: const Offset(0, 32),
                      onSelected: onProjectChanged,
                      itemBuilder: (ctx) {
                        final items = <PopupMenuEntry<int?>>[];

                        // Option 1: Default / All Company
                        items.add(
                          PopupMenuItem<int?>(
                            value: null,
                            child: Row(
                              children: [
                                const Icon(Icons.business_outlined, size: 16, color: Color(0xFF14B8A6)),
                                const SizedBox(width: 8),
                                const Expanded(
                                  child: Text(
                                    'Toàn Doanh Nghiệp (Mặc Định)',
                                    style: TextStyle(color: Colors.white, fontWeight: FontWeight.w600, fontSize: 12),
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                ),
                                if (selectedProjectId == null)
                                  const Icon(Icons.check, size: 14, color: Color(0xFF14B8A6)),
                              ],
                            ),
                          ),
                        );

                        if (projects.isNotEmpty) {
                          items.add(const PopupMenuDivider(height: 8));
                          for (final p in projects) {
                            final id = int.tryParse(p['id']?.toString() ?? '') ?? 0;
                            final title = p['title'] ?? 'Dự án $id';
                            final rawStage = p['project_stage']?.toString();
                            final pStage = ProjectStage.fromString(rawStage);
                            final isCurrent = selectedProjectId == id;

                            items.add(
                              PopupMenuItem<int?>(
                                value: id,
                                child: Row(
                                  children: [
                                    Expanded(
                                      child: Text(
                                        title,
                                        style: TextStyle(
                                          color: isCurrent ? const Color(0xFF38BDF8) : Colors.white,
                                          fontWeight: isCurrent ? FontWeight.bold : FontWeight.w500,
                                          fontSize: 12,
                                        ),
                                        overflow: TextOverflow.ellipsis,
                                      ),
                                    ),
                                    const SizedBox(width: 6),
                                    StageBadge(stage: pStage, isCompact: true),
                                    if (isCurrent) ...[
                                      const SizedBox(width: 6),
                                      const Icon(Icons.check, size: 14, color: Color(0xFF38BDF8)),
                                    ],
                                  ],
                                ),
                              ),
                            );
                          }
                        }

                        return items;
                      },
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Flexible(
                            child: Text(
                              projectTitle,
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 13,
                                fontWeight: FontWeight.bold,
                                letterSpacing: 0.3,
                              ),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                          const SizedBox(width: 4),
                          const Icon(
                            Icons.keyboard_arrow_down_rounded,
                            color: Color(0xFF94A3B8),
                            size: 16,
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(width: 6),

                  // Stage Badge
                  StageBadge(
                    stage: stage,
                    isCompact: true,
                    onTap: policy != null ? () => StagePolicyDialog.show(context, policy) : null,
                  ),

                  // Mini Readiness Gauge Badge
                  const SizedBox(width: 6),
                  Tooltip(
                    message: 'Mức độ sẵn sàng chuyển Stage: $readinessPercent%',
                    child: InkWell(
                      onTap: onOpenStageGateAudit,
                      borderRadius: BorderRadius.circular(8),
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
                        decoration: BoxDecoration(
                          color: (readinessPercent >= 70
                                  ? const Color(0xFF10B981)
                                  : (readinessPercent >= 40
                                      ? const Color(0xFFF59E0B)
                                      : const Color(0xFFEF4444)))
                              .withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(
                            color: (readinessPercent >= 70
                                    ? const Color(0xFF10B981)
                                    : (readinessPercent >= 40
                                        ? const Color(0xFFF59E0B)
                                        : const Color(0xFFEF4444)))
                                .withValues(alpha: 0.4),
                            width: 0.8,
                          ),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            SizedBox(
                              width: 10,
                              height: 10,
                              child: CircularProgressIndicator(
                                value: effectiveReadiness,
                                strokeWidth: 2,
                                backgroundColor: Colors.white12,
                                valueColor: AlwaysStoppedAnimation<Color>(
                                  readinessPercent >= 70
                                      ? const Color(0xFF10B981)
                                      : (readinessPercent >= 40
                                          ? const Color(0xFFF59E0B)
                                          : const Color(0xFFEF4444)),
                                ),
                              ),
                            ),
                            const SizedBox(width: 4),
                            Text(
                              '$readinessPercent%',
                              style: TextStyle(
                                color: readinessPercent >= 70
                                    ? const Color(0xFF10B981)
                                    : (readinessPercent >= 40
                                        ? const Color(0xFFF59E0B)
                                        : const Color(0xFFEF4444)),
                                fontSize: 10.5,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),

                  if (policy != null) ...[
                    const SizedBox(width: 4),
                    IconButton(
                      tooltip: 'Xem chính sách Stage',
                      icon: Icon(Icons.info_outline, size: 14, color: stage.primaryColor),
                      onPressed: () => StagePolicyDialog.show(context, policy),
                      padding: EdgeInsets.zero,
                      constraints: const BoxConstraints(minWidth: 18, minHeight: 18),
                    ),
                  ],
                ],
              ),

              const SizedBox(height: 8),

              // ── Row 2: Stage Goal (Mục tiêu cốt lõi) ──
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.03),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(
                    color: Colors.white.withValues(alpha: 0.05),
                  ),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Padding(
                      padding: const EdgeInsets.only(top: 1),
                      child: Icon(
                        Icons.flag_outlined,
                        size: 12,
                        color: stage.primaryColor,
                      ),
                    ),
                    const SizedBox(width: 6),
                    Expanded(
                      child: RichText(
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        text: TextSpan(
                          children: [
                            const TextSpan(
                              text: 'Mục tiêu: ',
                              style: TextStyle(
                                color: Colors.white70,
                                fontSize: 11,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            TextSpan(
                              text: stageGoal,
                              style: const TextStyle(
                                color: Color(0xFF94A3B8),
                                fontSize: 11,
                                fontWeight: FontWeight.w400,
                                height: 1.3,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 6),

              // ── Row 3: Critical Constraint (Rào cản/Giả định rủi ro) ──
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
                decoration: BoxDecoration(
                  color: const Color(0xFFF59E0B).withValues(alpha: 0.05),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(
                    color: const Color(0xFFF59E0B).withValues(alpha: 0.15),
                  ),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Padding(
                      padding: EdgeInsets.only(top: 1),
                      child: Icon(
                        Icons.warning_amber_rounded,
                        size: 12,
                        color: Color(0xFFF59E0B),
                      ),
                    ),
                    const SizedBox(width: 6),
                    Expanded(
                      child: RichText(
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        text: TextSpan(
                          children: [
                            const TextSpan(
                              text: 'Rủi ro/Rào cản: ',
                              style: TextStyle(
                                color: Color(0xFFFCD34D),
                                fontSize: 11,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            TextSpan(
                              text: constraintText,
                              style: const TextStyle(
                                color: Color(0xFF94A3B8),
                                fontSize: 11,
                                fontWeight: FontWeight.w400,
                                height: 1.3,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 8),

              // ── Row 4: Quick Action Buttons (5 Công cụ Chiến lược & Thẩm định Stage-Gate) ──
              Row(
                children: [
                  Expanded(
                    child: InkWell(
                      onTap: onOpenStrategy,
                      borderRadius: BorderRadius.circular(8),
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
                        decoration: BoxDecoration(
                          gradient: LinearGradient(
                            colors: [
                              stage.primaryColor.withValues(alpha: 0.15),
                              const Color(0xFF38BDF8).withValues(alpha: 0.08),
                            ],
                          ),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(
                            color: stage.primaryColor.withValues(alpha: 0.35),
                            width: 0.8,
                          ),
                        ),
                        child: Row(
                          children: [
                            Icon(Icons.hub_outlined, color: stage.primaryColor, size: 13),
                            const SizedBox(width: 6),
                            const Expanded(
                              child: Text(
                                '5 Trụ Cột Chiến Lược',
                                style: TextStyle(
                                  color: Colors.white,
                                  fontSize: 11,
                                  fontWeight: FontWeight.w600,
                                  letterSpacing: 0.2,
                                ),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                            Icon(Icons.arrow_forward_rounded, color: stage.primaryColor, size: 12),
                          ],
                        ),
                      ),
                    ),
                  ),
                  if (onOpenStageGateAudit != null) ...[
                    const SizedBox(width: 6),
                    InkWell(
                      onTap: onOpenStageGateAudit,
                      borderRadius: BorderRadius.circular(8),
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
                        decoration: BoxDecoration(
                          color: const Color(0xFF10B981).withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(
                            color: const Color(0xFF10B981).withValues(alpha: 0.35),
                            width: 0.8,
                          ),
                        ),
                        child: const Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(Icons.verified_user_outlined, color: Color(0xFF10B981), size: 13),
                            SizedBox(width: 4),
                            Text(
                              'Thẩm Định',
                              style: TextStyle(
                                color: Color(0xFF10B981),
                                fontSize: 11,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
