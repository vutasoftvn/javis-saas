import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../data/models/validation_models.dart';
import '../../../../data/services/validation_service.dart';

class ValidationStudioTabController extends GetxController {
  final currentProjectId = 30.obs;
  final isLoading = false.obs;
  final activeSubTab = 0.obs; // 0: Risk Matrix, 1: Hypotheses & Experiments, 2: Evidence Ledger

  final stateVector = Rxn<StateVectorModel>();
  final riskMatrix = Rxn<RiskMatrixModel>();
  final hypotheses = <ValidationHypothesisModel>[].obs;
  final experiments = <ValidationExperimentModel>[].obs;
  final evidenceList = <ValidationEvidenceModel>[].obs;

  @override
  void onInit() {
    super.onInit();
    loadAllData();
  }

  Future<void> loadAllData() async {
    isLoading.value = true;
    final pId = currentProjectId.value;
    try {
      final sv = await ValidationService.getStateVector(pId);
      final rm = await ValidationService.getRiskMatrix(pId);
      final hypos = await ValidationService.getHypotheses(pId);
      final exps = await ValidationService.getExperiments(pId);
      final evis = await ValidationService.getEvidence(pId);

      stateVector.value = sv;
      riskMatrix.value = rm;
      hypotheses.assignAll(hypos);
      experiments.assignAll(exps);
      evidenceList.assignAll(evis);
    } finally {
      isLoading.value = false;
    }
  }

  Future<void> generateHypothesisForAssumption(int assumptionId) async {
    isLoading.value = true;
    try {
      final res = await ValidationService.generateHypothesis(currentProjectId.value, assumptionId);
      if (res != null) {
        Get.snackbar(
          'Đã tạo Giả thuyết',
          'Giả thuyết mới đã được đưa vào bảng kiểm chứng',
          snackPosition: SnackPosition.BOTTOM,
          backgroundColor: Colors.green.withValues(alpha: 0.2),
        );
        await loadAllData();
      }
    } finally {
      isLoading.value = false;
    }
  }

  Future<void> recommendExperimentForHypothesis(int hypothesisId) async {
    isLoading.value = true;
    try {
      final res = await ValidationService.recommendExperiment(currentProjectId.value, hypothesisId);
      if (res != null) {
        Get.snackbar(
          'Đã đề xuất Thử nghiệm',
          'Thử nghiệm nhỏ nhất [${res.name}] đã được tạo',
          snackPosition: SnackPosition.BOTTOM,
          backgroundColor: Colors.blue.withValues(alpha: 0.2),
        );
        await loadAllData();
      }
    } finally {
      isLoading.value = false;
    }
  }
}

class ValidationStudioTab extends StatelessWidget {
  const ValidationStudioTab({super.key});

  @override
  Widget build(BuildContext context) {
    final controller = Get.put(ValidationStudioTabController());
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return Obx(() {
      if (controller.isLoading.value && controller.stateVector.value == null) {
        return const Center(child: CircularProgressIndicator(color: AppTheme.primaryLight));
      }

      return SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildHeader(context, controller, isDark),
            const SizedBox(height: 24),
            _buildSubNav(context, controller),
            const SizedBox(height: 24),
            if (controller.activeSubTab.value == 0)
              _buildRiskMatrixSection(context, controller, isDark)
            else if (controller.activeSubTab.value == 1)
              _buildHypothesisExperimentSection(context, controller, isDark)
            else
              _buildEvidenceLedgerSection(context, controller, isDark),
          ],
        ),
      );
    });
  }

  Widget _buildHeader(BuildContext context, ValidationStudioTabController controller, bool isDark) {
    final sv = controller.stateVector.value;
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF1E222D) : Colors.white,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: isDark ? const Color(0xFF2A3142) : const Color(0xFFE2E8F0)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.04),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  const Icon(Icons.rocket_launch_rounded, color: Colors.blueAccent, size: 24),
                  const SizedBox(width: 10),
                  Text(
                    'PROJECT VALIDATION STUDIO',
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                      letterSpacing: 0.5,
                      color: isDark ? Colors.white : Colors.black87,
                    ),
                  ),
                ],
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: BoxDecoration(
                  color: Colors.blueAccent.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.blueAccent.withValues(alpha: 0.4)),
                ),
                child: Text(
                  'STAGE: ${sv?.projectStage ?? "VALIDATION"}',
                  style: const TextStyle(color: Colors.blueAccent, fontWeight: FontWeight.bold, fontSize: 12),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Text(
            'Next Best Action: ${sv?.primaryNextBestAction ?? "Test pricing before building more features."}',
            style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: Colors.amber),
          ),
          const SizedBox(height: 14),
          Row(
            children: [
              Text('Overall Confidence: ${( (sv?.overallConfidence ?? 0.0) * 100).toInt()}%',
                  style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w500)),
              const SizedBox(width: 14),
              Expanded(
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(6),
                  child: LinearProgressIndicator(
                    value: sv?.overallConfidence ?? 0.0,
                    minHeight: 8,
                    backgroundColor: isDark ? const Color(0xFF2A3142) : Colors.grey.shade200,
                    color: Colors.greenAccent.shade700,
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildSubNav(BuildContext context, ValidationStudioTabController controller) {
    final tabs = [
      {'title': 'Ma Trận Rủi Ro (Risk Matrix)', 'icon': Icons.grid_4x4_rounded},
      {'title': 'Giả Thuyết & Thử Nghiệm', 'icon': Icons.science_outlined},
      {'title': 'Sổ Cái Bằng Chứng (Evidence Ledger)', 'icon': Icons.fact_check_outlined},
    ];

    return Row(
      children: List.generate(tabs.length, (index) {
        final isSelected = controller.activeSubTab.value == index;
        return Padding(
          padding: const EdgeInsets.only(right: 12),
          child: ChoiceChip(
            label: Row(
              children: [
                Icon(tabs[index]['icon'] as IconData, size: 16),
                const SizedBox(width: 6),
                Text(tabs[index]['title'] as String),
              ],
            ),
            selected: isSelected,
            onSelected: (_) => controller.activeSubTab.value = index,
            selectedColor: Colors.blueAccent,
            labelStyle: TextStyle(
              color: isSelected ? Colors.white : Colors.grey,
              fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
            ),
          ),
        );
      }),
    );
  }

  Widget _buildRiskMatrixSection(BuildContext context, ValidationStudioTabController controller, bool isDark) {
    final rm = controller.riskMatrix.value;
    final critical = rm?.criticalRisks ?? [];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Text(
              'Góc Tử Huyệt (Critical Risks - Điểm 16–25)',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.redAccent),
            ),
            Text('Tổng cộng: ${rm?.totalAssumptions ?? 0} Giả định',
                style: const TextStyle(fontSize: 13, color: Colors.grey)),
          ],
        ),
        const SizedBox(height: 12),
        if (critical.isEmpty)
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: Colors.green.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(10),
            ),
            child: const Row(
              children: [
                Icon(Icons.verified, color: Colors.green),
                SizedBox(width: 10),
                Text('Chưa phát hiện giả định có rủi ro tử huyệt (>15 điểm).'),
              ],
            ),
          )
        else
          ...critical.map((item) => Card(
                margin: const EdgeInsets.only(bottom: 12),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.redAccent.withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Text(
                          '${item.riskScore}',
                          style: const TextStyle(
                            color: Colors.redAccent,
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                      const SizedBox(width: 16),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              '[${item.category}] ${item.statement}',
                              style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600),
                            ),
                            const SizedBox(height: 6),
                            Text(
                              'Importance: ${item.importance}/5 • Uncertainty: ${item.uncertainty}/5 • Status: ${item.status}',
                              style: const TextStyle(fontSize: 12, color: Colors.grey),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(width: 12),
                      ElevatedButton.icon(
                        onPressed: () => controller.generateHypothesisForAssumption(item.id),
                        icon: const Icon(Icons.auto_awesome, size: 14),
                        label: const Text('Tạo Giả Thuyết'),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.blueAccent,
                          foregroundColor: Colors.white,
                        ),
                      ),
                    ],
                  ),
                ),
              )),
      ],
    );
  }

  Widget _buildHypothesisExperimentSection(BuildContext context, ValidationStudioTabController controller, bool isDark) {
    final hypos = controller.hypotheses;
    final exps = controller.experiments;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('Giả Thuyết Đang Kiểm Chứng (Hypotheses Board)',
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
        const SizedBox(height: 12),
        if (hypos.isEmpty)
          const Text('Chưa có giả thuyết nào được khởi tạo. Hãy tạo từ Ma trận rủi ro.')
        else
          ...hypos.map((h) => Card(
                margin: const EdgeInsets.only(bottom: 12),
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text('Hypothesis #${h.id}', style: const TextStyle(fontWeight: FontWeight.bold)),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                            decoration: BoxDecoration(
                              color: Colors.blueAccent.withValues(alpha: 0.15),
                              borderRadius: BorderRadius.circular(6),
                            ),
                            child: Text(h.status,
                                style: const TextStyle(color: Colors.blueAccent, fontSize: 11, fontWeight: FontWeight.bold)),
                          ),
                        ],
                      ),
                      const SizedBox(height: 10),
                      Text(h.statement, style: const TextStyle(fontSize: 14, height: 1.3)),
                      const SizedBox(height: 12),
                      Align(
                        alignment: Alignment.centerRight,
                        child: OutlinedButton.icon(
                          onPressed: () => controller.recommendExperimentForHypothesis(h.id),
                          icon: const Icon(Icons.science, size: 14),
                          label: const Text('Đề Xuất Thử Nghiệm'),
                        ),
                      ),
                    ],
                  ),
                ),
              )),
        const SizedBox(height: 24),
        const Text('Thử Nghiệm Nhỏ Nhất Đang Chạy (Smallest Useful Experiments)',
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
        const SizedBox(height: 12),
        if (exps.isEmpty)
          const Text('Chưa có thử nghiệm nào đang chạy.')
        else
          ...exps.map((exp) => ListTile(
                tileColor: isDark ? const Color(0xFF1E222D) : Colors.white,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                leading: const Icon(Icons.biotech, color: Colors.greenAccent),
                title: Text(exp.name, style: const TextStyle(fontWeight: FontWeight.w600)),
                subtitle: Text('Type: ${exp.experimentType} • Target Threshold: ${exp.successThreshold}'),
                trailing: Text('${exp.durationDays} ngày', style: const TextStyle(color: Colors.amber)),
              )),
      ],
    );
  }

  Widget _buildEvidenceLedgerSection(BuildContext context, ValidationStudioTabController controller, bool isDark) {
    final evis = controller.evidenceList;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('Sổ Cái Bằng Chứng Thực Tế (Evidence Ledger)',
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
        const SizedBox(height: 12),
        if (evis.isEmpty)
          const Text('Chưa ghi nhận bằng chứng nào.')
        else
          ...evis.map((evi) => Card(
                margin: const EdgeInsets.only(bottom: 10),
                child: ListTile(
                  leading: Icon(
                    evi.relationship == 'SUPPORTS' ? Icons.check_circle : Icons.cancel,
                    color: evi.relationship == 'SUPPORTS' ? Colors.green : Colors.redAccent,
                  ),
                  title: Text(evi.observation),
                  subtitle: Text('Nguồn: ${evi.sourceType} • Loại: ${evi.evidenceType} • Độ tin cậy: ${(evi.confidence * 100).toInt()}%'),
                  trailing: Text(evi.relationship, style: TextStyle(
                    color: evi.relationship == 'SUPPORTS' ? Colors.green : Colors.redAccent,
                    fontWeight: FontWeight.bold,
                  )),
                ),
              )),
      ],
    );
  }
}
