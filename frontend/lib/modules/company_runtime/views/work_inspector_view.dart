import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/company_runtime_controller.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/floating_app_bar.dart';

class WorkInspectorView extends StatelessWidget {
  const WorkInspectorView({super.key});

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<CompanyRuntimeController>()) {
      Get.put(CompanyRuntimeController());
    }
    final controller = Get.find<CompanyRuntimeController>();
    final searchCtrl = TextEditingController();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const JavisFloatingAppBar(
          title: 'Giám sát công việc (Work Inspector)',
          subtitle: 'Kiểm tra vết truy xuất 360° công việc, log thực thi & kết quả AI',
          icon: Icons.visibility_rounded,
        ),
        const SizedBox(height: 12),
        Expanded(
          child: SingleChildScrollView(
            padding: EdgeInsets.zero,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Search Bar
                Card(
                  color: const Color(0xFF1E293B),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                    child: Row(
                      children: [
                        const Icon(Icons.search, color: Colors.white54),
                        const SizedBox(width: 12),
                        Expanded(
                          child: TextField(
                            controller: searchCtrl,
                            style: const TextStyle(color: Colors.white),
                            decoration: const InputDecoration(
                              hintText: 'Nhập Task ID để kiểm tra toàn diện...',
                              hintStyle: TextStyle(color: Colors.white38),
                              border: InputBorder.none,
                            ),
                            onSubmitted: (val) {
                              if (val.trim().isNotEmpty) {
                                controller.loadInspector(val.trim());
                              }
                            },
                          ),
                        ),
                        ElevatedButton(
                          style: ElevatedButton.styleFrom(
                            backgroundColor: AppTheme.primary,
                            foregroundColor: Colors.white,
                          ),
                          onPressed: () {
                            final val = searchCtrl.text.trim();
                            if (val.isNotEmpty) {
                              controller.loadInspector(val);
                            }
                          },
                          child: const Text('Tra cứu'),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 20),

                // Inspection Result Area
                Obx(() {
                  if (controller.loading.value) {
                    return const Center(
                      child: Padding(
                        padding: EdgeInsets.all(40),
                        child: CircularProgressIndicator(),
                      ),
                    );
                  }

                  final data = controller.currentInspectorData.value;
                  if (data == null) {
                    return Center(
                      child: Padding(
                        padding: const EdgeInsets.all(40),
                        child: Column(
                          children: [
                            const Icon(Icons.visibility_outlined, size: 48, color: Colors.white38),
                            const SizedBox(height: 12),
                            Text(
                              controller.selectedTaskId.value.isEmpty
                                  ? 'Chọn hoặc nhập Task ID để xem Inspector'
                                  : 'Không tìm thấy dữ liệu Inspector cho Task ${controller.selectedTaskId.value}',
                              style: const TextStyle(color: Colors.white54),
                            ),
                          ],
                        ),
                      ),
                    );
                  }

                  final task = data['task'] as Map<String, dynamic>? ?? {};
                  final outcome = data['outcome'] as Map<String, dynamic>?;
                  final reviews = (data['reviews'] as List<dynamic>?) ?? [];
                  final handoffs = (data['handoffs'] as List<dynamic>?) ?? [];
                  final blockers = (data['blockers'] as List<dynamic>?) ?? [];
                  final artifacts = (data['artifacts'] as List<dynamic>?) ?? [];
                  final runSteps = (data['run_steps'] as List<dynamic>?) ?? [];

                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // 1. Task Header
                      _buildSectionCard(
                        context,
                        title: '1. Task Execution Unit',
                        icon: Icons.task_alt,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              task['title'] ?? 'Untitled Task',
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 18,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            const SizedBox(height: 10),
                            Wrap(
                              spacing: 8,
                              runSpacing: 8,
                              children: [
                                Chip(label: Text('Status: ${task['status']}')),
                                Chip(label: Text('Function: ${task['function'] ?? 'N/A'}')),
                                Chip(label: Text('Mode: ${task['execution_mode'] ?? 'N/A'}')),
                                Chip(label: Text('Priority: ${task['priority']}')),
                              ],
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 16),

                      // 2. Work Contract & Outcome
                      if (outcome != null)
                        _buildSectionCard(
                          context,
                          title: '2. Work Contract & Acceptance Criteria',
                          icon: Icons.description_outlined,
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text('Outcome: ${outcome['title']}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                              const SizedBox(height: 6),
                              Text('Kết quả mong đợi: ${outcome['desired_result']}', style: const TextStyle(color: Colors.white70)),
                              const SizedBox(height: 10),
                              Wrap(
                                spacing: 8,
                                children: [
                                  Chip(label: Text('Review: ${outcome['review_type'] ?? 'N/A'}')),
                                  Chip(label: Text('Rework Count: ${outcome['rework_count'] ?? 0}')),
                                ],
                              ),
                            ],
                          ),
                        ),
                      const SizedBox(height: 16),

                      // 3. Handoffs & Blockers
                      _buildSectionCard(
                        context,
                        title: '3. Handoffs & Blockers (${handoffs.length} Handoffs · ${blockers.length} Blockers)',
                        icon: Icons.alt_route_rounded,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            if (handoffs.isNotEmpty) ...[
                              const Text('Handoffs:', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                              ...handoffs.map((h) => ListTile(
                                    dense: true,
                                    title: Text('To: ${h['to_function']}', style: const TextStyle(color: Colors.white70)),
                                    subtitle: Text('Status: ${h['status']}', style: const TextStyle(color: Colors.white38)),
                                  )),
                            ],
                            if (blockers.isNotEmpty) ...[
                              const SizedBox(height: 8),
                              const Text('Blockers:', style: TextStyle(color: Colors.amberAccent, fontWeight: FontWeight.bold)),
                              ...blockers.map((b) => ListTile(
                                    dense: true,
                                    title: Text(b['description'] ?? 'Blocker', style: const TextStyle(color: Colors.white70)),
                                    subtitle: Text('Status: ${b['status']}', style: const TextStyle(color: Colors.white38)),
                                  )),
                            ],
                            if (handoffs.isEmpty && blockers.isEmpty)
                              const Text('Không có Handoffs hoặc Blockers nào.', style: TextStyle(color: Colors.white38)),
                          ],
                        ),
                      ),
                      const SizedBox(height: 16),

                      // 4. Artifacts & Reviews
                      _buildSectionCard(
                        context,
                        title: '4. Artifacts & Reviews (${artifacts.length} Artifacts · ${reviews.length} Reviews)',
                        icon: Icons.folder_zip_outlined,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            if (artifacts.isNotEmpty) ...[
                              const Text('Artifacts:', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                              ...artifacts.map((a) => ListTile(
                                    dense: true,
                                    title: Text(a['file_path'] ?? 'Artifact', style: const TextStyle(color: Colors.white70)),
                                    subtitle: Text('Type: ${a['artifact_type']}', style: const TextStyle(color: Colors.white38)),
                                  )),
                            ],
                            if (reviews.isNotEmpty) ...[
                              const SizedBox(height: 8),
                              const Text('Reviews:', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                              ...reviews.map((r) => ListTile(
                                    dense: true,
                                    title: Text('Verdict: ${r['verdict']}', style: const TextStyle(color: Colors.white70)),
                                    subtitle: Text('Notes: ${r['notes'] ?? 'None'}', style: const TextStyle(color: Colors.white38)),
                                  )),
                            ],
                            if (artifacts.isEmpty && reviews.isEmpty)
                              const Text('Chưa có Artifacts hoặc Reviews nào.', style: TextStyle(color: Colors.white38)),
                          ],
                        ),
                      ),
                      const SizedBox(height: 16),

                      // 5. Execution Dispatch Trace (RunSteps)
                      _buildSectionCard(
                        context,
                        title: '5. Execution Dispatch (${runSteps.length} RunSteps)',
                        icon: Icons.route_outlined,
                        child: runSteps.isEmpty
                            ? const Text(
                                'Chưa có RunStep nào được dispatch cho Task này.',
                                style: TextStyle(color: Colors.white38),
                              )
                            : Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: runSteps.map((rs) {
                                  final step = rs as Map<String, dynamic>;
                                  return ListTile(
                                    dense: true,
                                    leading: const Icon(Icons.smart_toy_outlined, size: 18, color: Colors.white54),
                                    title: Text(
                                      'Profile: ${step['assigned_agent_profile_id'] ?? 'N/A'}',
                                      style: const TextStyle(color: Colors.white70),
                                    ),
                                    subtitle: Text(
                                      'Status: ${step['status']} · Risk: ${step['risk_level'] ?? 'N/A'} · Runtime: ${step['assigned_runtime'] ?? 'N/A'}',
                                      style: const TextStyle(color: Colors.white38),
                                    ),
                                  );
                                }).toList(),
                              ),
                      ),
                    ],
                  );
                }),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildSectionCard(BuildContext context, {required String title, required IconData icon, required Widget child}) {
    return Card(
      color: const Color(0xFF1E293B),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon, size: 20, color: AppTheme.primary),
                const SizedBox(width: 8),
                Text(title, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 15)),
              ],
            ),
            const Divider(color: Colors.white10, height: 24),
            child,
          ],
        ),
      ),
    );
  }
}
