import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/theme/app_theme.dart';
import '../../controllers/ai_operations_controller.dart';

class ExecutionArtifactsTab extends GetView<AiOperationsController> {
  const ExecutionArtifactsTab({super.key});

  @override
  Widget build(BuildContext context) {
    return Obx(() {
      if (controller.isLoading.value) {
        return const Center(
          child: CircularProgressIndicator(color: AppTheme.primary),
        );
      }

      final artifacts = controller.allArtifacts;
      if (artifacts.isEmpty) {
        return _buildEmptyState();
      }

      return ListView.builder(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
        itemCount: artifacts.length,
        itemBuilder: (context, index) {
          final art = artifacts[index];
          return _buildArtifactCard(context, art);
        },
      );
    });
  }

  Widget _buildArtifactCard(BuildContext context, Map<String, dynamic> art) {
    final name = art['name'] ?? art['title'] ?? 'unnamed_artifact';
    final sizeBytes = (art['size_bytes'] as num?)?.toInt() ?? 0;
    final sha256 = art['sha256'] ?? art['content_hash'] ?? '';
    final mime = art['mime_type'] ?? 'application/octet-stream';
    final jobId = art['job_id'] ?? '';
    final agentKey = art['agent_key'] ?? '';

    String sizeStr;
    if (sizeBytes > 1024 * 1024) {
      sizeStr = '${(sizeBytes / (1024 * 1024)).toStringAsFixed(2)} MB';
    } else if (sizeBytes > 1024) {
      sizeStr = '${(sizeBytes / 1024).toStringAsFixed(1)} KB';
    } else {
      sizeStr = '$sizeBytes B';
    }

    IconData fileIcon = Icons.insert_drive_file;
    if (name.endsWith('.json')) {
      fileIcon = Icons.data_object;
    } else if (name.endsWith('.md') || name.endsWith('.txt')) {
      fileIcon = Icons.description;
    } else if (name.endsWith('.csv')) {
      fileIcon = Icons.table_chart;
    } else if (name.endsWith('.png') || name.endsWith('.jpg')) {
      fileIcon = Icons.image;
    }

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      color: AppTheme.surfaceDark,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: const BorderSide(color: AppTheme.borderDark),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AppTheme.primary.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: AppTheme.primary.withValues(alpha: 0.3)),
              ),
              child: Icon(fileIcon, color: AppTheme.primary, size: 24),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    name,
                    style: const TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.bold,
                      fontSize: 15,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Row(
                    children: [
                      Text(
                        sizeStr,
                        style: const TextStyle(color: AppTheme.primaryLight, fontSize: 12, fontWeight: FontWeight.w600),
                      ),
                      const SizedBox(width: 8),
                      const Text('•', style: TextStyle(color: AppTheme.textDimDark)),
                      const SizedBox(width: 8),
                      Text(
                        mime,
                        style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 12),
                      ),
                      if (agentKey.isNotEmpty) ...[
                        const SizedBox(width: 8),
                        const Text('•', style: TextStyle(color: AppTheme.textDimDark)),
                        const SizedBox(width: 8),
                        Text(
                          agentKey,
                          style: const TextStyle(color: AppTheme.textDimDark, fontSize: 12),
                        ),
                      ],
                      if (jobId.isNotEmpty) ...[
                        const SizedBox(width: 8),
                        const Text('•', style: TextStyle(color: AppTheme.textDimDark)),
                        const SizedBox(width: 8),
                        Text(
                          'Job: $jobId',
                          style: const TextStyle(color: AppTheme.textDimDark, fontSize: 11, fontFamily: 'monospace'),
                        ),
                      ],
                    ],
                  ),
                  if (sha256.isNotEmpty) ...[
                    const SizedBox(height: 4),
                    Text(
                      'SHA256: ${sha256.length > 16 ? "${sha256.substring(0, 16)}..." : sha256}',
                      style: const TextStyle(color: AppTheme.textDimDark, fontSize: 11, fontFamily: 'monospace'),
                    ),
                  ],
                ],
              ),
            ),
            const Icon(Icons.verified_outlined, color: AppTheme.success, size: 20),
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
            child: const Icon(Icons.folder_zip_outlined, size: 40, color: AppTheme.textDimDark),
          ),
          const SizedBox(height: 16),
          const Text(
            'Chưa có Artifacts nào',
            style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 6),
          const Text(
            'Các tệp báo cáo JSON, Markdown và kết quả xuất từ sandbox sẽ được lưu trữ tại đây.',
            style: TextStyle(color: AppTheme.textMutedDark, fontSize: 13),
          ),
        ],
      ),
    );
  }
}
