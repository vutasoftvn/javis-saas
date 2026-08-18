import 'package:flutter/material.dart';
import '../../../../data/models/strategy_lens_model.dart';

class BscScorecardWidget extends StatelessWidget {
  final bool isUnlocked;
  final String currentStage;
  final List<BscGoalModel> bscGoals;
  final Function(BscPerspective perspective, String objective, String kpiName, String target, String current) onCreateGoal;

  const BscScorecardWidget({
    super.key,
    required this.isUnlocked,
    required this.currentStage,
    required this.bscGoals,
    required this.onCreateGoal,
  });

  void _showAddGoalDialog(BuildContext context, BscPerspective initialPerspective) {
    final objCtrl = TextEditingController();
    final kpiCtrl = TextEditingController();
    final targetCtrl = TextEditingController();
    final currentCtrl = TextEditingController();
    BscPerspective selectedPerspective = initialPerspective;

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setState) => AlertDialog(
          backgroundColor: const Color(0xFF0F172A),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
            side: BorderSide(color: selectedPerspective.color, width: 1.5),
          ),
          title: Row(
            children: [
              Icon(selectedPerspective.icon, color: selectedPerspective.color, size: 20),
              const SizedBox(width: 8),
              const Text(
                'Thiết Lập Mục Tiêu BSC',
                style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
              ),
            ],
          ),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                DropdownButtonFormField<BscPerspective>(
                  initialValue: selectedPerspective,
                  dropdownColor: const Color(0xFF1E293B),
                  decoration: const InputDecoration(
                    labelText: 'Trụ cột Balanced Scorecard',
                    labelStyle: TextStyle(color: Colors.white70),
                  ),
                  items: BscPerspective.values.map((p) {
                    return DropdownMenuItem(
                      value: p,
                      child: Row(
                        children: [
                          Icon(p.icon, color: p.color, size: 16),
                          const SizedBox(width: 8),
                          Text(p.labelVi, style: TextStyle(color: p.color, fontSize: 12, fontWeight: FontWeight.bold)),
                        ],
                      ),
                    );
                  }).toList(),
                  onChanged: (val) {
                    if (val != null) setState(() => selectedPerspective = val);
                  },
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: objCtrl,
                  style: const TextStyle(color: Colors.white, fontSize: 13),
                  decoration: const InputDecoration(
                    labelText: 'Mục tiêu chiến lược (Objective) (*)',
                    labelStyle: TextStyle(color: Colors.white70),
                    hintText: 'Ví dụ: Đạt ARR 1M USD & Runway > 24 tháng...',
                    hintStyle: TextStyle(color: Colors.white30, fontSize: 12),
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: kpiCtrl,
                  style: const TextStyle(color: Colors.white, fontSize: 13),
                  decoration: const InputDecoration(
                    labelText: 'Tên chỉ số đo lường (KPI) (*)',
                    labelStyle: TextStyle(color: Colors.white70),
                  ),
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: targetCtrl,
                        style: const TextStyle(color: Colors.white, fontSize: 13),
                        decoration: const InputDecoration(
                          labelText: 'Mục tiêu (Target)',
                          labelStyle: TextStyle(color: Colors.white70),
                        ),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: TextField(
                        controller: currentCtrl,
                        style: const TextStyle(color: Colors.white, fontSize: 13),
                        decoration: const InputDecoration(
                          labelText: 'Hiện tại (Actual)',
                          labelStyle: TextStyle(color: Colors.white70),
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(),
              child: const Text('Hủy', style: TextStyle(color: Colors.white60)),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: selectedPerspective.color,
                foregroundColor: Colors.black,
              ),
              onPressed: () {
                if (objCtrl.text.trim().isNotEmpty && kpiCtrl.text.trim().isNotEmpty) {
                  onCreateGoal(
                    selectedPerspective,
                    objCtrl.text.trim(),
                    kpiCtrl.text.trim(),
                    targetCtrl.text.trim(),
                    currentCtrl.text.trim(),
                  );
                  Navigator.of(ctx).pop();
                }
              },
              child: const Text('Lưu Mục Tiêu BSC', style: TextStyle(fontWeight: FontWeight.bold)),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (!isUnlocked) {
      return Center(
        child: Container(
          constraints: const BoxConstraints(maxWidth: 580),
          padding: const EdgeInsets.all(28),
          decoration: BoxDecoration(
            color: const Color(0xFF1E293B).withValues(alpha: 0.8),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: const Color(0xFFA855F7).withValues(alpha: 0.4), width: 1.5),
            boxShadow: [
              BoxShadow(
                color: const Color(0xFFA855F7).withValues(alpha: 0.1),
                blurRadius: 20,
                spreadRadius: 4,
              ),
            ],
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: const Color(0xFFA855F7).withValues(alpha: 0.15),
                  shape: BoxShape.circle,
                ),
                child: const Icon(Icons.lock_outline_rounded, color: Color(0xFFA855F7), size: 36),
              ),
              const SizedBox(height: 18),
              const Text(
                'Balanced Scorecard (BSC) Đang Khóa',
                style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 10),
              Text(
                'Dự án hiện tại đang ở giai đoạn $currentStage.\nTheo nguyên tắc COSA Stage-Aware, Bảng Điểm Cân Bằng (BSC) chỉ mở khóa từ S5 (Operate & Grow) và S6 (Scale & Govern) nhằm bảo vệ startup không bị phân tán nguồn lực vào các chỉ số vận hành cồng kềnh trước khi đạt Product-Market Fit vững chắc.',
                style: TextStyle(color: Colors.white.withValues(alpha: 0.75), fontSize: 13, height: 1.5),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 18),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                decoration: BoxDecoration(
                  color: const Color(0xFF0F172A),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: Colors.white12),
                ),
                child: const Row(
                  children: [
                    Icon(Icons.lightbulb_outline, color: Color(0xFFF59E0B), size: 16),
                    SizedBox(width: 6),
                    Expanded(
                      child: Text(
                        'Khuyến nghị: Hãy tập trung vào Giả định rủi ro cao nhất & 12WY Tactics.',
                        style: TextStyle(color: Colors.white70, fontSize: 11),
                      ),
                    ),
                  ],
                ),
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
          child: const Row(
            children: [
              Icon(Icons.dashboard_customize_outlined, color: Color(0xFFA855F7), size: 20),
              SizedBox(width: 10),
              Expanded(
                child: Text(
                  'Balanced Scorecard (BSC): Quản trị toàn diện 4 trụ cột (Tài chính, Khách hàng, Vận hành, Con người) để mở rộng quy mô bền vững.',
                  style: TextStyle(color: Colors.white70, fontSize: 12, height: 1.4),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),

        // 4 Perspectives Grid
        Expanded(
          child: GridView.count(
            crossAxisCount: 2,
            crossAxisSpacing: 12,
            mainAxisSpacing: 12,
            childAspectRatio: 1.2,
            children: BscPerspective.values.map((persp) {
              final goals = bscGoals.where((g) => g.perspective == persp).toList();

              return Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFF1E293B).withValues(alpha: 0.6),
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: persp.color.withValues(alpha: 0.4), width: 1.2),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Title & Add
                    Row(
                      children: [
                        Icon(persp.icon, color: persp.color, size: 16),
                        const SizedBox(width: 6),
                        Expanded(
                          child: Text(
                            persp.labelVi,
                            style: TextStyle(color: persp.color, fontSize: 12, fontWeight: FontWeight.bold),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        IconButton(
                          tooltip: 'Thêm mục tiêu ${persp.name}',
                          icon: Icon(Icons.add_circle_outline, color: persp.color, size: 18),
                          onPressed: () => _showAddGoalDialog(context, persp),
                          padding: EdgeInsets.zero,
                          constraints: const BoxConstraints(minWidth: 24, minHeight: 24),
                        ),
                      ],
                    ),
                    const Divider(color: Colors.white12, height: 10),

                    // Goals list
                    Expanded(
                      child: goals.isEmpty
                          ? Center(
                              child: Text(
                                'Chưa có mục tiêu',
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
                                      const SizedBox(height: 4),
                                      Row(
                                        children: [
                                          Text(
                                            'KPI: ${goal.kpiName}',
                                            style: TextStyle(color: persp.color, fontSize: 10, fontWeight: FontWeight.w600),
                                          ),
                                          const Spacer(),
                                          Text(
                                            '${goal.currentValue} / ${goal.targetValue}',
                                            style: const TextStyle(color: Colors.white70, fontSize: 10, fontWeight: FontWeight.bold),
                                          ),
                                        ],
                                      ),
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
