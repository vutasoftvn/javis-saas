import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/network/api_result.dart';
import '../controllers/workspace_runtime_controller.dart';
import '../models/mvp_runtime_models.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/floating_app_bar.dart';

class WorkInspectorView extends StatelessWidget {
  const WorkInspectorView({super.key});

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<WorkspaceRuntimeController>()) {
      Get.put(WorkspaceRuntimeController());
    }
    final controller = Get.find<WorkspaceRuntimeController>();
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
                              hintText: 'Nhập ID tác vụ để kiểm tra...',
                              hintStyle: TextStyle(color: Colors.white38),
                              border: InputBorder.none,
                            ),
                            onSubmitted: (val) {
                              if (val.trim().isNotEmpty) {
                                controller.loadInspector('task', val.trim());
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
                              controller.loadInspector('task', val);
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

                  final result = controller.currentInspectorResult.value;
                  if (result == null) {
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
                                  : 'Không tìm thấy thông tin tác vụ',
                              style: const TextStyle(color: Colors.white54),
                            ),
                          ],
                        ),
                      ),
                    );
                  }

                  if (result is ApiFailure) {
                    final failure = (result as ApiFailure).failure;
                    return Center(
                      child: Padding(
                        padding: const EdgeInsets.all(40),
                        child: Column(
                          children: [
                            const Icon(Icons.error_outline, size: 48, color: AppTheme.warning),
                            const SizedBox(height: 12),
                            Text(
                              'Không thể tải chi tiết tác vụ: ${failure.message}',
                              style: const TextStyle(color: Colors.white70),
                            ),
                          ],
                        ),
                      ),
                    );
                  }

                  final data = (result as ApiSuccess<MvpRuntimeItemDetail>).data;

                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Header Card
                      Card(
                        color: const Color(0xFF1E293B),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                        child: Padding(
                          padding: const EdgeInsets.all(20),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                children: [
                                  Chip(
                                    label: Text(
                                      data.sourceRef.kind.toUpperCase(),
                                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12),
                                    ),
                                    backgroundColor: AppTheme.primary.withValues(alpha: 0.2),
                                  ),
                                  const SizedBox(width: 8),
                                  Text(
                                    data.state,
                                    style: const TextStyle(color: Colors.white70, fontSize: 13),
                                  ),
                                  const Spacer(),
                                  Text(
                                    'Nguồn: ${data.sourceRef.ref}',
                                    style: const TextStyle(color: Colors.white38, fontSize: 12),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 12),
                              Text(
                                data.title,
                                style: const TextStyle(
                                  color: Colors.white,
                                  fontWeight: FontWeight.bold,
                                  fontSize: 20,
                                ),
                              ),
                              if (data.description != null && data.description!.isNotEmpty) ...[
                                const SizedBox(height: 8),
                                Text(
                                  data.description!,
                                  style: const TextStyle(color: Colors.white70, fontSize: 14),
                                ),
                              ],
                              const SizedBox(height: 16),
                              Row(
                                children: [
                                  _InfoBadge(label: 'Mức độ', value: data.severity),
                                  const SizedBox(width: 16),
                                  _InfoBadge(
                                    label: 'Quan sát lúc',
                                    value: data.observedAt.length >= 19
                                        ? data.observedAt.substring(0, 19).replaceAll('T', ' ')
                                        : data.observedAt,
                                  ),
                                ],
                              ),
                            ],
                          ),
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
}

class _InfoBadge extends StatelessWidget {
  final String label;
  final String value;

  const _InfoBadge({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(color: Colors.white38, fontSize: 11)),
        const SizedBox(height: 2),
        Text(value, style: const TextStyle(color: Colors.white70, fontWeight: FontWeight.w600, fontSize: 13)),
      ],
    );
  }
}
