import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../data/models/stage_model.dart';
import '../../../../shared/widgets/stage_badge.dart';
import '../../controllers/dashboard_controller.dart';

class DashboardStageDemoBar extends StatelessWidget {
  final DashboardController controller;

  const DashboardStageDemoBar({super.key, required this.controller});

  @override
  Widget build(BuildContext context) {
    return Obx(() {
      final stage = controller.selectedStage.value;
      final isFiltered = controller.isStageFilteringEnabled.value;
      return Container(
        margin: const EdgeInsets.fromLTRB(14, 2, 14, 6),
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
        decoration: BoxDecoration(
          color: stage.primaryColor.withValues(alpha: 0.08),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
            color: stage.primaryColor.withValues(alpha: 0.35),
            width: 1.0,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            // Row 1: Stage Badge + Demo Switcher Dropdown
            Row(
              children: [
                Icon(stage.icon, size: 14, color: stage.primaryColor),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    'Demo Stage: ${stage.code}',
                    style: TextStyle(
                      color: stage.primaryColor,
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                PopupMenuButton<ProjectStage>(
                  tooltip: 'Chuyển đổi Stage để Test',
                  padding: EdgeInsets.zero,
                  color: const Color(0xFF0F172A),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(10),
                    side: const BorderSide(color: Color(0xFF1E293B)),
                  ),
                  onSelected: controller.setDemoStage,
                  itemBuilder: (ctx) => ProjectStage.values.map((s) {
                    final isCurrent = s == stage;
                    return PopupMenuItem<ProjectStage>(
                      value: s,
                      child: Row(
                        children: [
                          StageBadge(stage: s, isCompact: true),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              s.displayNameVi,
                              style: TextStyle(
                                color: isCurrent ? s.primaryColor : Colors.white,
                                fontSize: 12,
                                fontWeight: isCurrent ? FontWeight.bold : FontWeight.w500,
                              ),
                            ),
                          ),
                          if (isCurrent) ...[
                            const SizedBox(width: 4),
                            Icon(Icons.check, size: 14, color: s.primaryColor),
                          ],
                        ],
                      ),
                    );
                  }).toList(),
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
                    decoration: BoxDecoration(
                      color: stage.primaryColor.withValues(alpha: 0.2),
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: stage.primaryColor.withValues(alpha: 0.4), width: 0.8),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          'Đổi Stage',
                          style: TextStyle(color: stage.primaryColor, fontSize: 10.5, fontWeight: FontWeight.bold),
                        ),
                        const SizedBox(width: 2),
                        Icon(Icons.keyboard_arrow_down_rounded, size: 14, color: stage.primaryColor),
                      ],
                    ),
                  ),
                ),
              ],
            ),

            const SizedBox(height: 5),

            // Row 2: Filter Toggle Switch
            InkWell(
              onTap: controller.toggleStageFiltering,
              borderRadius: BorderRadius.circular(6),
              child: Row(
                children: [
                  Icon(
                    isFiltered ? Icons.filter_alt_outlined : Icons.filter_alt_off_outlined,
                    size: 13,
                    color: isFiltered ? const Color(0xFF10B981) : const Color(0xFF94A3B8),
                  ),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      isFiltered ? 'Lọc ưu tiên Stage ${stage.code}' : 'Hiện tất cả (Không lọc)',
                      style: TextStyle(
                        color: isFiltered ? const Color(0xFF10B981) : const Color(0xFF94A3B8),
                        fontSize: 10.5,
                        fontWeight: isFiltered ? FontWeight.w600 : FontWeight.normal,
                      ),
                    ),
                  ),
                  SizedBox(
                    height: 18,
                    width: 30,
                    child: Transform.scale(
                      scale: 0.65,
                      child: Switch(
                        value: isFiltered,
                        onChanged: (_) => controller.toggleStageFiltering(),
                        materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                        activeThumbColor: const Color(0xFF10B981),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      );
    });
  }
}
