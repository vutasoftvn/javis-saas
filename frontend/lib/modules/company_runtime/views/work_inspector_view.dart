import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/company_runtime_controller.dart';
import '../../../core/theme/app_theme.dart';

class WorkInspectorView extends StatelessWidget {
  const WorkInspectorView({super.key});

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<CompanyRuntimeController>()) {
      Get.put(CompanyRuntimeController());
    }
    final controller = Get.find<CompanyRuntimeController>();
    final searchCtrl = TextEditingController();

    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      appBar: AppBar(
        title: const Text('Work Inspector — 360° Traceability'),
        backgroundColor: const Color(0xFF1E293B),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
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
                        onSubmitted: (val) => controller.loadInspector(val.trim()),
                      ),
                    ),
                    ElevatedButton(
                      style: ElevatedButton.styleFrom(backgroundColor: AppTheme.primary),
                      onPressed: () => controller.loadInspector(searchCtrl.text.trim()),
                      child: const Text('Inspect', style: TextStyle(color: Colors.white)),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 20),

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
              final deps = data['dependencies'] as Map<String, dynamic>? ?? {};
              final reviews = (data['reviews'] as List<dynamic>?) ?? [];
              final handoffs = (data['handoffs'] as List<dynamic>?) ?? [];
              final blockers = (data['blockers'] as List<dynamic>?) ?? [];
              final artifacts = (data['artifacts'] as List<dynamic>?) ?? [];

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

                  // 3. Dependencies
                  _buildSectionCard(
                    context,
                    title: '3. Dependency DAG Connections',
                    icon: Icons.account_tree_outlined,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Upstream (${(deps['upstream'] as List?)?.length ?? 0}):', style: const TextStyle(color: Colors.white70, fontWeight: FontWeight.bold)),
                        const SizedBox(height: 4),
                        for (final d in (deps['upstream'] as List? ?? []))
                          Text(' • Task ${d['task_id']} [${d['dependency_type']}] → Status: ${d['status']}', style: const TextStyle(color: Colors.white54)),
                        const SizedBox(height: 8),
                        Text('Downstream (${(deps['downstream'] as List?)?.length ?? 0}):', style: const TextStyle(color: Colors.white70, fontWeight: FontWeight.bold)),
                        const SizedBox(height: 4),
                        for (final d in (deps['downstream'] as List? ?? []))
                          Text(' • Task ${d['task_id']} [${d['dependency_type']}] → Status: ${d['status']}', style: const TextStyle(color: Colors.white54)),
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),

                  // 4. Reviews & Rework History
                  _buildSectionCard(
                    context,
                    title: '4. Work Reviews & Feedback (${reviews.length})',
                    icon: Icons.rate_review_outlined,
                    child: reviews.isEmpty
                        ? const Text('Chưa có review nào được ghi nhận.', style: TextStyle(color: Colors.white38))
                        : Column(
                            children: [
                              for (final r in reviews)
                                Padding(
                                  padding: const EdgeInsets.only(bottom: 8),
                                  child: Row(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                        decoration: BoxDecoration(
                                          color: r['result'] == 'ACCEPTED' ? Colors.green.withValues(alpha: 0.2) : Colors.orange.withValues(alpha: 0.2),
                                          borderRadius: BorderRadius.circular(4),
                                        ),
                                        child: Text(r['result'] ?? '', style: TextStyle(color: r['result'] == 'ACCEPTED' ? Colors.greenAccent : Colors.orangeAccent, fontSize: 11)),
                                      ),
                                      const SizedBox(width: 8),
                                      Expanded(
                                        child: Text(r['feedback'] ?? 'Không có feedback', style: const TextStyle(color: Colors.white70, fontSize: 13)),
                                      ),
                                    ],
                                  ),
                                ),
                            ],
                          ),
                  ),
                  const SizedBox(height: 16),

                  // 5. Structured Handoffs
                  _buildSectionCard(
                    context,
                    title: '5. Structured Handoffs (${handoffs.length})',
                    icon: Icons.swap_horiz,
                    child: handoffs.isEmpty
                        ? const Text('Không có handoff liên quan.', style: TextStyle(color: Colors.white38))
                        : Column(
                            children: [
                              for (final h in handoffs)
                                Text(' • ${h['from_function']} → ${h['to_function']} [${h['handoff_type']}]: ${h['requested_action']} (${h['status']})', style: const TextStyle(color: Colors.white70)),
                            ],
                          ),
                  ),
                  const SizedBox(height: 16),

                  // 6. Blockers
                  _buildSectionCard(
                    context,
                    title: '6. Blockers & Exceptions (${blockers.length})',
                    icon: Icons.block,
                    child: blockers.isEmpty
                        ? const Text('Không có blocker.', style: TextStyle(color: Colors.white38))
                        : Column(
                            children: [
                              for (final b in blockers)
                                Text(' • [${b['blocker_type']}] ${b['description']} (${b['status']})', style: const TextStyle(color: Colors.white70)),
                            ],
                          ),
                  ),
                  const SizedBox(height: 16),

                  // 7. Artifacts
                  _buildSectionCard(
                    context,
                    title: '7. Artifacts & Outputs (${artifacts.length})',
                    icon: Icons.attach_file,
                    child: artifacts.isEmpty
                        ? const Text('Chưa có artifact nào được liên kết.', style: TextStyle(color: Colors.white38))
                        : Column(
                            children: [
                              for (final a in artifacts)
                                Text(' • ${a['title']} (${a['type']}) — ${a['status']}', style: const TextStyle(color: Colors.white70)),
                            ],
                          ),
                  ),
                ],
              );
            }),
          ],
        ),
      ),
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
