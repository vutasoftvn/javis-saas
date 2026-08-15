import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/theme/app_theme.dart';
import '../../controllers/ai_operations_controller.dart';

class ExecutionJobsTab extends GetView<AiOperationsController> {
  const ExecutionJobsTab({super.key});

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        _buildFilterBar(),
        Expanded(
          child: Obx(() {
            if (controller.isLoading.value) {
              return const Center(
                child: CircularProgressIndicator(color: AppTheme.primary),
              );
            }

            final jobs = controller.jobs;
            if (jobs.isEmpty) {
              return _buildEmptyState();
            }

            return ListView.builder(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
              itemCount: jobs.length,
              itemBuilder: (context, index) {
                final job = jobs[index];
                return _buildJobCard(context, job);
              },
            );
          }),
        ),
      ],
    );
  }

  Widget _buildFilterBar() {
    final filters = [
      {'key': 'all', 'label': 'Tất cả'},
      {'key': 'running', 'label': 'Đang chạy'},
      {'key': 'completed', 'label': 'Hoàn thành'},
      {'key': 'failed', 'label': 'Thất bại'},
      {'key': 'queued', 'label': 'Đang chờ'},
    ];

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
      decoration: const BoxDecoration(
        color: AppTheme.surfaceDarkHeader,
        border: Border(bottom: BorderSide(color: AppTheme.borderDark)),
      ),
      child: Row(
        children: [
          const Icon(Icons.filter_list, size: 18, color: AppTheme.textMutedDark),
          const SizedBox(width: 10),
          Expanded(
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Obx(() {
                final active = controller.selectedStatusFilter.value;
                return Row(
                  children: filters.map((f) {
                    final isSelected = active == f['key'];
                    return Padding(
                      padding: const EdgeInsets.only(right: 8),
                      child: ChoiceChip(
                        label: Text(f['label']!),
                        selected: isSelected,
                        onSelected: (_) => controller.setFilter(f['key']!),
                        selectedColor: AppTheme.primary.withValues(alpha: 0.2),
                        backgroundColor: AppTheme.surfaceDarkLighter,
                        labelStyle: TextStyle(
                          color: isSelected ? AppTheme.primary : AppTheme.textMutedDark,
                          fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                          fontSize: 13,
                        ),
                        side: BorderSide(
                          color: isSelected ? AppTheme.primary : AppTheme.borderDark,
                        ),
                      ),
                    );
                  }).toList(),
                );
              }),
            ),
          ),
          IconButton(
            icon: const Icon(Icons.refresh, size: 20, color: AppTheme.primary),
            onPressed: () => controller.loadJobs(),
            tooltip: 'Làm mới',
          ),
        ],
      ),
    );
  }

  Widget _buildJobCard(BuildContext context, Map<String, dynamic> job) {
    final jobId = job['id_str'] ?? job['id']?.toString() ?? 'N/A';
    final agentKey = job['agent_key'] ?? 'unknown_agent';
    final status = (job['status'] ?? 'queued').toString().toLowerCase();
    final createdAt = job['created_at']?.toString().split('.').first.replaceFirst('T', ' ') ?? '';
    final steps = (job['steps'] as List?) ?? [];
    final artifacts = (job['artifacts'] as List?) ?? [];

    Color statusColor;
    String statusLabel;
    IconData statusIcon;

    switch (status) {
      case 'completed':
        statusColor = AppTheme.success;
        statusLabel = 'Hoàn thành';
        statusIcon = Icons.check_circle_outline;
        break;
      case 'running':
      case 'preparing':
      case 'collecting':
        statusColor = AppTheme.primary;
        statusLabel = 'Đang thực thi';
        statusIcon = Icons.sync;
        break;
      case 'failed':
        statusColor = AppTheme.error;
        statusLabel = 'Thất bại';
        statusIcon = Icons.error_outline;
        break;
      case 'blocked':
      case 'awaiting_approval':
        statusColor = AppTheme.warning;
        statusLabel = 'Chờ duyệt';
        statusIcon = Icons.pause_circle_outline;
        break;
      default:
        statusColor = AppTheme.textMutedDark;
        statusLabel = 'Đang chờ';
        statusIcon = Icons.hourglass_empty;
    }

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      color: AppTheme.surfaceDark,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: const BorderSide(color: AppTheme.borderDark),
      ),
      child: Theme(
        data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
        child: ExpansionTile(
          tilePadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          leading: Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: statusColor.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: statusColor.withValues(alpha: 0.3)),
            ),
            child: Icon(statusIcon, color: statusColor, size: 20),
          ),
          title: Row(
            children: [
              Text(
                agentKey.toUpperCase(),
                style: const TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.bold,
                  fontSize: 15,
                ),
              ),
              const SizedBox(width: 10),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(
                  color: statusColor.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  statusLabel,
                  style: TextStyle(color: statusColor, fontSize: 12, fontWeight: FontWeight.w600),
                ),
              ),
            ],
          ),
          subtitle: Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Row(
              children: [
                Text(
                  'Job ID: $jobId',
                  style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 12, fontFamily: 'monospace'),
                ),
                const SizedBox(width: 12),
                if (createdAt.isNotEmpty) ...[
                  const Icon(Icons.access_time, size: 12, color: AppTheme.textDimDark),
                  const SizedBox(width: 4),
                  Text(
                    createdAt,
                    style: const TextStyle(color: AppTheme.textDimDark, fontSize: 12),
                  ),
                ],
              ],
            ),
          ),
          children: [
            Container(
              padding: const EdgeInsets.all(16),
              decoration: const BoxDecoration(
                color: AppTheme.backgroundDarker,
                borderRadius: BorderRadius.only(
                  bottomLeft: Radius.circular(12),
                  bottomRight: Radius.circular(12),
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (job['error_message'] != null && job['error_message'].toString().isNotEmpty) ...[
                    Container(
                      padding: const EdgeInsets.all(10),
                      margin: const EdgeInsets.only(bottom: 12),
                      decoration: BoxDecoration(
                        color: AppTheme.error.withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: AppTheme.error.withValues(alpha: 0.3)),
                      ),
                      child: Row(
                        children: [
                          const Icon(Icons.warning_amber_rounded, color: AppTheme.error, size: 18),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              job['error_message'].toString(),
                              style: const TextStyle(color: AppTheme.error, fontSize: 13),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                  const Text(
                    'Các bước thực thi (Execution Steps):',
                    style: TextStyle(color: Colors.white70, fontSize: 13, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 8),
                  if (steps.isEmpty) ...[
                    const Text(
                      'Chưa có bước thực thi nào được ghi nhận.',
                      style: TextStyle(color: AppTheme.textDimDark, fontSize: 12),
                    ),
                  ] else ...[
                    ...steps.map((s) {
                      final cmd = s['command'] ?? '';
                      final stepStatus = s['status'] ?? 'unknown';
                      final stdout = s['stdout_excerpt'] ?? '';
                      final stderr = s['stderr_excerpt'] ?? '';
                      return Container(
                        margin: const EdgeInsets.only(bottom: 8),
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: AppTheme.surfaceDarkLighter,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: AppTheme.borderDark),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                const Icon(Icons.terminal, size: 14, color: AppTheme.primary),
                                const SizedBox(width: 6),
                                Expanded(
                                  child: Text(
                                    cmd,
                                    style: const TextStyle(
                                      color: AppTheme.primaryLight,
                                      fontFamily: 'monospace',
                                      fontSize: 12.5,
                                    ),
                                  ),
                                ),
                                Text(
                                  stepStatus.toString().toUpperCase(),
                                  style: TextStyle(
                                    fontSize: 11,
                                    fontWeight: FontWeight.bold,
                                    color: stepStatus == 'completed' ? AppTheme.success : AppTheme.error,
                                  ),
                                ),
                              ],
                            ),
                            if (stdout.toString().isNotEmpty) ...[
                              const SizedBox(height: 6),
                              Container(
                                width: double.infinity,
                                padding: const EdgeInsets.all(8),
                                decoration: BoxDecoration(
                                  color: Colors.black45,
                                  borderRadius: BorderRadius.circular(4),
                                ),
                                child: Text(
                                  stdout.toString(),
                                  style: const TextStyle(color: Colors.white70, fontSize: 11.5, fontFamily: 'monospace'),
                                ),
                              ),
                            ],
                            if (stderr.toString().isNotEmpty) ...[
                              const SizedBox(height: 6),
                              Container(
                                width: double.infinity,
                                padding: const EdgeInsets.all(8),
                                decoration: BoxDecoration(
                                  color: AppTheme.error.withValues(alpha: 0.1),
                                  borderRadius: BorderRadius.circular(4),
                                ),
                                child: Text(
                                  stderr.toString(),
                                  style: const TextStyle(color: AppTheme.error, fontSize: 11.5, fontFamily: 'monospace'),
                                ),
                              ),
                            ],
                          ],
                        ),
                      );
                    }),
                  ],
                  if (artifacts.isNotEmpty) ...[
                    const SizedBox(height: 12),
                    Text(
                      'Tệp tin kết quả (${artifacts.length} artifacts):',
                      style: const TextStyle(color: Colors.white70, fontSize: 13, fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 6),
                    Wrap(
                      spacing: 8,
                      runSpacing: 6,
                      children: artifacts.map((a) {
                        final name = a['name'] ?? a['path'] ?? 'file';
                        return Chip(
                          backgroundColor: AppTheme.surfaceDarkLighter,
                          side: const BorderSide(color: AppTheme.borderDark),
                          avatar: const Icon(Icons.insert_drive_file, size: 14, color: AppTheme.primary),
                          label: Text(
                            name.toString(),
                            style: const TextStyle(color: Colors.white, fontSize: 12),
                          ),
                        );
                      }).toList(),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: AppTheme.surfaceDarkLighter,
              shape: BoxShape.circle,
              border: Border.all(color: AppTheme.borderDark),
            ),
            child: const Icon(Icons.memory, size: 40, color: AppTheme.textDimDark),
          ),
          const SizedBox(height: 16),
          const Text(
            'Chưa có công việc thực thi nào',
            style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 6),
          const Text(
            'Các công việc phân tích dữ liệu và nghiên cứu web sẽ xuất hiện tại đây.',
            style: TextStyle(color: AppTheme.textMutedDark, fontSize: 13),
          ),
        ],
      ),
    );
  }
}
