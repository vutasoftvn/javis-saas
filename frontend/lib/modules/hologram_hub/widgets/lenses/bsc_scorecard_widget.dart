import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/localization/app_translations.dart';
import '../../../../data/models/strategy_lens_model.dart';

/// Read-only Balanced Scorecard (BSC) widget displaying published objectives
/// and indicators grouped by the 4 perspectives.
///
/// Under governed BSC workflow, BSC is not an independent ad-hoc planning phase,
/// but a scorecard reflecting published Strategic Objectives and Key Results.
class BscScorecardWidget extends StatelessWidget {
  final bool isUnlocked;
  final String currentStage;
  final List<BscGoalModel> bscGoals;
  final Function(BscPerspective perspective, String objective, String kpiName, String target, String current)? onCreateGoal;

  const BscScorecardWidget({
    super.key,
    required this.isUnlocked,
    required this.currentStage,
    required this.bscGoals,
    this.onCreateGoal,
  });

  static String _tr(String key, String fallback) {
    final translated = key.tr;
    return translated != key ? translated : fallback;
  }

  @override
  Widget build(BuildContext context) {
    if (!isUnlocked) {
      return Center(
        child: Container(
          key: const Key('bsc_locked_container'),
          margin: const EdgeInsets.all(32),
          padding: const EdgeInsets.all(32),
          decoration: BoxDecoration(
            color: const Color(0xFF1E293B),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: const Color(0xFF334155)),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: const Color(0xFFA855F7).withValues(alpha: 0.1),
                  shape: BoxShape.circle,
                ),
                child: const Icon(
                  Icons.lock_outline,
                  color: Color(0xFFA855F7),
                  size: 42,
                ),
              ),
              const SizedBox(height: 18),
              Text(
                _tr(L10nKey.bscTitle, 'Thẻ điểm Cân bằng BSC (Balanced Scorecard)'),
                style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 10),
              Text(
                _tr(
                  L10nKey.bscHeaderDesc,
                  'Thẻ điểm BSC phản ánh các Mục tiêu & Kết quả then chốt (OKRs) đã được phê duyệt và công bố.\n'
                  'Các chỉ số sẽ tự động đồng bộ theo từng trụ cột khi OKR chu kỳ được xuất bản.',
                ),
                style: TextStyle(color: Colors.white.withValues(alpha: 0.75), fontSize: 13, height: 1.5),
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      );
    }

    return Column(
      children: [
        // Header
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: const Color(0xFFA855F7).withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: const Color(0xFFA855F7).withValues(alpha: 0.3)),
          ),
          child: Row(
            children: [
              const Icon(Icons.dashboard_customize_outlined, color: Color(0xFFA855F7), size: 20),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  _tr(
                    L10nKey.bscReadOnlyDesc,
                    'Thẻ điểm Balanced Scorecard (Chỉ xem): Tổng hợp các mục tiêu & chỉ số đo lường đã công bố trên 4 trụ cột chiến lược.',
                  ),
                  style: const TextStyle(color: Colors.white70, fontSize: 12, height: 1.4),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),

        // 4 Perspectives Grid (Read-only)
        Expanded(
          child: GridView.count(
            crossAxisCount: 2,
            crossAxisSpacing: 12,
            mainAxisSpacing: 12,
            childAspectRatio: 1.2,
            children: BscPerspective.values.map((persp) {
              final goals = bscGoals.where((g) => g.perspective == persp).toList();

              return Container(
                key: Key('bsc_card_${persp.name}'),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFF1E293B).withValues(alpha: 0.6),
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: persp.color.withValues(alpha: 0.4), width: 1.2),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Title
                    Row(
                      children: [
                        Icon(persp.icon, color: persp.color, size: 16),
                        const SizedBox(width: 6),
                        Expanded(
                          child: Text(
                            persp.localizedLabel,
                            style: TextStyle(color: persp.color, fontSize: 12, fontWeight: FontWeight.bold),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                          decoration: BoxDecoration(
                            color: persp.color.withValues(alpha: 0.2),
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: Text(
                            '${goals.length}',
                            style: TextStyle(color: persp.color, fontSize: 10, fontWeight: FontWeight.bold),
                          ),
                        ),
                      ],
                    ),
                    const Divider(color: Colors.white12, height: 10),

                    // Goals list
                    Expanded(
                      child: goals.isEmpty
                          ? Center(
                              child: Text(
                                _tr(L10nKey.bscEmpty, 'Chưa có chỉ số xuất bản'),
                                style: TextStyle(color: Colors.white.withValues(alpha: 0.3), fontSize: 11),
                              ),
                            )
                          : ListView.separated(
                              itemCount: goals.length,
                              separatorBuilder: (_, _) => const SizedBox(height: 6),
                              itemBuilder: (context, idx) {
                                final goal = goals[idx];

                                return Container(
                                  padding: const EdgeInsets.all(8),
                                  decoration: BoxDecoration(
                                    color: Colors.black.withValues(alpha: 0.25),
                                    borderRadius: BorderRadius.circular(8),
                                  ),
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        goal.objective,
                                        style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.bold),
                                        maxLines: 2,
                                        overflow: TextOverflow.ellipsis,
                                      ),
                                      if (goal.kpiName.isNotEmpty) ...[
                                        const SizedBox(height: 4),
                                        Row(
                                          children: [
                                            Text(
                                              'KPI: ${goal.kpiName}',
                                              style: TextStyle(color: persp.color, fontSize: 10, fontWeight: FontWeight.w600),
                                            ),
                                            const Spacer(),
                                            if (goal.targetValue.isNotEmpty)
                                              Text(
                                                '${goal.currentValue} / ${goal.targetValue}',
                                                style: const TextStyle(color: Colors.white70, fontSize: 10, fontWeight: FontWeight.bold),
                                              ),
                                          ],
                                        ),
                                      ],
                                    ],
                                  ),
                                );
                              },
                            ),
                    ),
                  ],
                ),
              );
            }).toList(),
          ),
        ),
      ],
    );
  }
}
