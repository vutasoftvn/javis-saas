import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../controllers/strategy_controller.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/widgets/app_modal_dialog.dart';

class TwelveWyGovernanceDialog {
  static void showCycleGovernanceDialog(BuildContext context, StrategyController controller) {
    String? currentCycleId;
    if (controller.twelveWeekCycles.isNotEmpty) {
      currentCycleId = controller.twelveWeekCycles.first['id']?.toString();
    }

    if (currentCycleId != null) {
      controller.loadCycleGovernance(currentCycleId);
    }

    AppModalDialog.show(
      context: context,
      title: 'Quản Trị Chu Kỳ 13 Tuần (13-Week Stages & Gate Governance)',
      subtitle: 'Khung kiểm soát giai đoạn thực thi, cổng đánh giá (Gate) và lưu vết bằng chứng',
      icon: Icons.shield_outlined,
      maxWidth: 780,
      content: StatefulBuilder(
        builder: (context, setState) {
          final stages = controller.cycleStages;
          final decisions = controller.gateDecisions;

          return SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text('Các Giai Đoạn Chu Kỳ (Cycle Stages):', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: Colors.white)),
                    Row(
                      children: [
                        if (currentCycleId != null) ...[
                          OutlinedButton.icon(
                            onPressed: () => showCycleContractDialog(context, controller, currentCycleId!),
                            icon: const Icon(Icons.description_outlined, size: 14, color: AppTheme.secondaryLight),
                            label: const Text('Hợp đồng Chu kỳ', style: TextStyle(fontSize: 12, color: AppTheme.secondaryLight)),
                          ),
                          const SizedBox(width: 8),
                          ElevatedButton.icon(
                            onPressed: () async {
                              await controller.generateStandardStages(currentCycleId!);
                              setState(() {});
                            },
                            icon: const Icon(Icons.auto_fix_high_rounded, size: 14),
                            label: const Text('Sinh 5 Giai đoạn Chuẩn (13 Tuần)', style: TextStyle(fontSize: 12)),
                            style: ElevatedButton.styleFrom(backgroundColor: AppTheme.primary, foregroundColor: const Color(0xFF04070E)),
                          ),
                        ],
                      ],
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                if (stages.isEmpty)
                  Container(
                    padding: const EdgeInsets.all(20),
                    decoration: BoxDecoration(color: AppTheme.surfaceDark, borderRadius: BorderRadius.circular(12)),
                    child: const Center(child: Text('Chưa có giai đoạn nào. Nhấn "Sinh 5 Giai đoạn Chuẩn" để khởi tạo cấu trúc 13 tuần.', style: TextStyle(color: Colors.white70, fontSize: 13))),
                  )
                else
                  ...stages.map((s) => Container(
                    margin: const EdgeInsets.only(bottom: 8),
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: AppTheme.surfaceDark.withValues(alpha: 0.6),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: Colors.white10),
                    ),
                    child: Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                          decoration: BoxDecoration(color: AppTheme.secondary.withValues(alpha: 0.2), borderRadius: BorderRadius.circular(6)),
                          child: Text('W${s['start_week']}-W${s['end_week']}', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 11, color: AppTheme.secondaryLight)),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(s['name'] ?? '', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.white)),
                              if (s['purpose'] != null) Text(s['purpose'], style: const TextStyle(color: Colors.white60, fontSize: 11)),
                            ],
                          ),
                        ),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                          decoration: BoxDecoration(color: Colors.white10, borderRadius: BorderRadius.circular(4)),
                          child: Text(s['status'] ?? 'pending', style: const TextStyle(fontSize: 10, color: Colors.white70)),
                        ),
                      ],
                    ),
                  )),

                const SizedBox(height: 20),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text('Nhật Ký Quyết Định Cổng (Gate Decisions):', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: Colors.white)),
                    OutlinedButton.icon(
                      onPressed: () => showGateDecisionDialog(context, controller),
                      icon: const Icon(Icons.gavel_rounded, size: 14, color: AppTheme.accentLight),
                      label: const Text('Ghi Quyết định Cổng', style: TextStyle(fontSize: 12, color: AppTheme.accentLight)),
                      style: OutlinedButton.styleFrom(side: BorderSide(color: AppTheme.accent.withValues(alpha: 0.4))),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                if (decisions.isEmpty)
                  const Text('Chưa có quyết định cổng nào được ghi nhận trong chu kỳ này.', style: TextStyle(color: Colors.white54, fontSize: 12))
                else
                  ...decisions.take(5).map((d) => Container(
                    margin: const EdgeInsets.only(bottom: 6),
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.04), borderRadius: BorderRadius.circular(8)),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                              decoration: BoxDecoration(
                                color: (d['decision'] == 'GO' ? Colors.green : Colors.orange).withValues(alpha: 0.2),
                                borderRadius: BorderRadius.circular(4),
                              ),
                              child: Text(d['decision'] ?? '', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 11, color: d['decision'] == 'GO' ? Colors.greenAccent : Colors.orangeAccent)),
                            ),
                            const SizedBox(width: 8),
                            Text(d['rationale'] ?? '', style: const TextStyle(color: Colors.white, fontSize: 12)),
                          ],
                        ),
                        Text(d['decided_at']?.toString().split('T')[0] ?? '', style: const TextStyle(color: Colors.white38, fontSize: 11)),
                      ],
                    ),
                  )),
              ],
            ),
          );
        },
      ),
      actions: [
        TextButton(onPressed: () => Get.back(), child: const Text('Đóng', style: TextStyle(color: Colors.white60))),
      ],
    );
  }

  static void showGateDecisionDialog(BuildContext context, StrategyController controller) {
    String? selectedProjectId = controller.projects.isNotEmpty ? controller.projects.first['id']?.toString() : null;
    String decision = 'GO';
    final rationaleController = TextEditingController();
    final nextStepController = TextEditingController();

    AppModalDialog.show(
      context: context,
      title: 'Ghi Nhận Quyết Định Cổng (Gate Decision)',
      subtitle: 'Đánh giá điều kiện vượt cổng kiểm soát (Stage-Gate) để tiếp tục, lặp lại hoặc dừng lại',
      icon: Icons.gavel_rounded,
      maxWidth: 640,
      content: StatefulBuilder(
        builder: (context, setState) => Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (controller.projects.isNotEmpty) ...[
              DropdownButtonFormField<String>(
                initialValue: selectedProjectId,
                dropdownColor: AppTheme.surfaceDark,
                decoration: const InputDecoration(labelText: 'Dự án áp dụng cổng kiểm soát'),
                items: controller.projects.map((p) => DropdownMenuItem(value: p['id'].toString(), child: Text(p['title'] ?? p['name'] ?? ''))).toList(),
                onChanged: (v) => setState(() => selectedProjectId = v),
              ),
              const SizedBox(height: 14),
            ],
            DropdownButtonFormField<String>(
              initialValue: decision,
              dropdownColor: AppTheme.surfaceDark,
              decoration: const InputDecoration(labelText: 'Quyết định Cổng (Decision)'),
              items: const [
                DropdownMenuItem(value: 'GO', child: Text('GO — Tiếp tục sang giai đoạn kế tiếp')),
                DropdownMenuItem(value: 'ITERATE', child: Text('ITERATE — Tái thử nghiệm & bổ sung bằng chứng')),
                DropdownMenuItem(value: 'HOLD', child: Text('HOLD — Tạm hoãn bảo lưu nguồn lực')),
                DropdownMenuItem(value: 'PIVOT', child: Text('PIVOT — Chuyển hướng chiến lược')),
                DropdownMenuItem(value: 'STOP', child: Text('STOP — Dừng dự án & thu hồi ngân sách')),
              ],
              onChanged: (v) => setState(() => decision = v ?? 'GO'),
            ),
            const SizedBox(height: 14),
            TextField(
              controller: rationaleController,
              decoration: const InputDecoration(labelText: 'Lý do & Căn cứ phê duyệt', hintText: 'Đạt 100% mục tiêu đo lường...'),
            ),
            const SizedBox(height: 14),
            TextField(
              controller: nextStepController,
              decoration: const InputDecoration(labelText: 'Chỉ đạo hành động tiếp theo', hintText: 'Tiến hành tuyển dụng 2 kỹ sư...'),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(onPressed: () => Get.back(), child: const Text('Huỷ', style: TextStyle(color: Colors.white60))),
        const SizedBox(width: 12),
        ElevatedButton(
          onPressed: () async {
            if (selectedProjectId == null || rationaleController.text.trim().isEmpty) return;
            Get.back();
            await controller.recordGateDecision(
              projectId: selectedProjectId!,
              decision: decision,
              rationale: rationaleController.text.trim(),
              nextStepInstructions: nextStepController.text.trim().isNotEmpty ? nextStepController.text.trim() : null,
            );
          },
          style: ElevatedButton.styleFrom(backgroundColor: AppTheme.primary, foregroundColor: const Color(0xFF04070E)),
          child: const Text('Lưu Quyết Định'),
        ),
      ],
    );
  }

  static void showCycleContractDialog(BuildContext context, StrategyController controller, String cycleId) {
    final defController = TextEditingController(text: 'Hoàn thành các mục tiêu chiến lược và bàn giao MVP đúng tiến độ');
    final capacityController = TextEditingController(text: '40');
    final bufferController = TextEditingController(text: '20');

    AppModalDialog.show(
      context: context,
      title: 'Hợp Đồng Chu Kỳ Thực Thi (Cycle Contract)',
      subtitle: 'Cam kết năng lực lãnh đạo, đệm dự phòng rủi ro và định nghĩa thành công (Success Definition)',
      icon: Icons.handshake_rounded,
      maxWidth: 620,
      content: StatefulBuilder(
        builder: (context, setState) => Column(
          children: [
            TextField(
              controller: defController,
              maxLines: 2,
              decoration: const InputDecoration(labelText: 'Định nghĩa Thành công Chu kỳ (Success Definition)'),
            ),
            const SizedBox(height: 14),
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: capacityController,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(labelText: 'Năng lực Founder (Giờ/tuần)'),
                  ),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: TextField(
                    controller: bufferController,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(labelText: 'Đệm dự phòng rủi ro (%)'),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
      actions: [
        TextButton(onPressed: () => Get.back(), child: const Text('Huỷ', style: TextStyle(color: Colors.white60))),
        const SizedBox(width: 12),
        ElevatedButton(
          onPressed: () async {
            Get.back();
            await controller.saveCycleContract(
              cycleId: cycleId,
              successDefinition: defController.text.trim(),
              founderCapacityHours: double.tryParse(capacityController.text.trim()) ?? 40.0,
              riskBufferPercent: double.tryParse(bufferController.text.trim()) ?? 20.0,
            );
          },
          style: ElevatedButton.styleFrom(backgroundColor: AppTheme.primary, foregroundColor: const Color(0xFF04070E)),
          child: const Text('Lưu Hợp Đồng'),
        ),
      ],
    );
  }
}
