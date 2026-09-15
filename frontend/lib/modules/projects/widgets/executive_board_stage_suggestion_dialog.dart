import 'package:flutter/material.dart';
import '../services/executive_board_stage_suggestion_service.dart';

/// Sau khi Founder xác nhận chuyển Project lifecycle stage, hiển thị 2 hành
/// động Founder tách biệt (CHỈ gợi ý, KHÔNG tự kích hoạt office, KHÔNG tự
/// deploy agent):
///   - bật office ở Workspace (màn Executive Advisory Board);
///   - deploy Workspace Agent vào Project (màn Project Operating Loop).
Future<void> showExecutiveBoardStageSuggestionDialog(
  BuildContext context, {
  required String projectId,
  required String workspaceId,
  ExecutiveBoardStageSuggestionService? service,
}) async {
  final suggestionService = service ?? ExecutiveBoardStageSuggestionService();
  final result = await suggestionService.getSuggestion(projectId);
  final suggestion = result.dataOrNull;
  if (suggestion == null) {
    if (!context.mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Không thể tải gợi ý Executive Board')),
    );
    return; // Không chặn lifecycle transition đã thành công.
  }

  final officeToEnable = suggestion.workspaceOfficeToEnable;
  final agentsToDeploy = suggestion.projectAgentsToDeploy;

  if (officeToEnable.isEmpty && agentsToDeploy.isEmpty) return;
  if (!context.mounted) return;

  await showDialog<void>(
    context: context,
    builder: (dialogContext) => AlertDialog(
      title: Text('Gợi ý Executive Board cho ${suggestion.stage}'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (officeToEnable.isNotEmpty) ...[
              const Text(
                'Bật Office ở Workspace:',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
              ...officeToEnable.map((role) => Text('• $role')),
            ],
            if (agentsToDeploy.isNotEmpty) ...[
              const SizedBox(height: 8),
              const Text(
                'Deploy Agent vào Project:',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
              ...agentsToDeploy.map((role) => Text('• $role')),
            ],
            const SizedBox(height: 12),
            const Text(
              'Các hành động này phải do Founder thực hiện thủ công ở màn '
              'tương ứng — không được tự động kích hoạt hay deploy.',
              style: TextStyle(fontSize: 12),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(dialogContext).pop(),
          child: const Text('Đóng'),
        ),
      ],
    ),
  );
}
