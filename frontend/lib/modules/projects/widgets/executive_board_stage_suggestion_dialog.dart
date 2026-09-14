import 'package:flutter/material.dart';
import '../services/executive_board_stage_suggestion_service.dart';

/// Sau khi founder xác nhận chuyển Project lifecycle stage, hỏi có muốn
/// kích hoạt role Executive Board gợi ý cho stage mới không. Founder bấm
/// từng role muốn kích hoạt — KHÔNG có hành động "activate all" tự động,
/// đúng nguyên tắc CLAUDE.md "không tự động".
Future<void> showExecutiveBoardStageSuggestionDialog(
  BuildContext context, {
  required String projectId,
  required String workspaceId,
}) async {
  final service = ExecutiveBoardStageSuggestionService();
  Map<String, dynamic>? suggestion;
  try {
    suggestion = await service.getSuggestion(projectId);
  } catch (_) {
    return; // Không chặn luồng chuyển stage nếu suggestion tạm thời lỗi.
  }

  final toActivate = (suggestion['toActivate'] as List<dynamic>? ?? []).cast<String>();
  final toSuggestDeactivate = (suggestion['toSuggestDeactivate'] as List<dynamic>? ?? []).cast<String>();

  if (toActivate.isEmpty && toSuggestDeactivate.isEmpty) return;
  if (!context.mounted) return;

  final activated = <String>{};

  await showDialog<void>(
    context: context,
    builder: (dialogContext) => StatefulBuilder(
      builder: (dialogContext, setState) => AlertDialog(
        title: Text('Gợi ý Executive Board cho ${suggestion!['stage']}'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (toActivate.isNotEmpty) ...[
                const Text('Nên kích hoạt:', style: TextStyle(fontWeight: FontWeight.bold)),
                ...toActivate.map(
                  (role) => CheckboxListTile(
                    title: Text(role),
                    value: activated.contains(role),
                    onChanged: (checked) => setState(() {
                      if (checked == true) {
                        activated.add(role);
                      } else {
                        activated.remove(role);
                      }
                    }),
                  ),
                ),
              ],
              if (toSuggestDeactivate.isNotEmpty) ...[
                const SizedBox(height: 8),
                const Text('Có thể tắt (founder tự quyết ở màn Executive Board):', style: TextStyle(fontWeight: FontWeight.bold)),
                ...toSuggestDeactivate.map((role) => Text('- $role')),
              ],
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(),
            child: const Text('Bỏ qua'),
          ),
          ElevatedButton(
            onPressed: () async {
              for (final role in activated) {
                try {
                  await service.activateRole(workspaceId, role);
                } catch (_) {
                  // Bỏ qua lỗi từng role riêng lẻ — không chặn các role còn lại.
                }
              }
              if (dialogContext.mounted) Navigator.of(dialogContext).pop();
            },
            child: const Text('Xác nhận kích hoạt đã chọn'),
          ),
        ],
      ),
    ),
  );
}
