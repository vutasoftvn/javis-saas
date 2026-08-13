import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/audit_controller.dart';
import '../../../core/theme/app_theme.dart';

class AuditView extends GetView<AuditController> {
  const AuditView({super.key});

  static const List<String> _commonActions = [
    'workflow.step.approve',
    'workflow.step.reject',
    'workflow.run.start',
    'workflow.definition.create',
  ];

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<AuditController>()) {
      Get.put(AuditController());
    }

    return Scaffold(
      backgroundColor: Colors.transparent,
      body: Padding(
        padding: const EdgeInsets.all(20.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: const [
                    Text(
                      'Nhật ký kiểm toán (Audit Trail)',
                      style: TextStyle(
                        fontSize: 22,
                        fontWeight: FontWeight.w800,
                        color: Colors.white,
                        letterSpacing: -0.5,
                      ),
                    ),
                    SizedBox(height: 4),
                    Text(
                      'Lưu trữ bất biến mọi hành động trọng yếu của người dùng, tác tử AI và hệ thống.',
                      style: TextStyle(
                        fontSize: 13,
                        color: AppTheme.textMutedDark,
                      ),
                    ),
                  ],
                ),
                IconButton(
                  icon: const Icon(Icons.refresh, color: AppTheme.primary),
                  tooltip: 'Tải lại',
                  onPressed: controller.loadAuditEvents,
                ),
              ],
            ),
            const SizedBox(height: 16),

            // Action Filter Chips
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  const Text('Lọc nhanh: ', style: TextStyle(color: AppTheme.textMutedDark, fontSize: 12)),
                  const SizedBox(width: 8),
                  ..._commonActions.map((act) {
                    return Obx(() {
                      final isSelected = controller.selectedAction.value == act;
                      return Padding(
                        padding: const EdgeInsets.only(right: 8.0),
                        child: FilterChip(
                          label: Text(act, style: TextStyle(fontSize: 11, color: isSelected ? const Color(0xFF00F0FF) : AppTheme.textDark)),
                          selected: isSelected,
                          onSelected: (_) => controller.filterByAction(act),
                          backgroundColor: const Color(0xFF0D172A),
                          selectedColor: const Color(0xFF00F0FF).withValues(alpha: 0.15),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(8),
                            side: BorderSide(
                              color: isSelected ? const Color(0xFF00F0FF) : const Color(0xFF1E293B),
                            ),
                          ),
                        ),
                      );
                    });
                  }),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // Events List / Table
            Expanded(
              child: Obx(() {
                if (controller.isLoading.value) {
                  return const Center(child: CircularProgressIndicator());
                }

                if (controller.events.isEmpty) {
                  return Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: const [
                        Icon(Icons.history_toggle_off, size: 54, color: AppTheme.textMutedDark),
                        SizedBox(height: 16),
                        Text(
                          'Chưa có sự kiện kiểm toán nào được ghi lại',
                          style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white),
                        ),
                        SizedBox(height: 4),
                        Text(
                          'Mọi thao tác phê duyệt, chạy workflow hoặc tạo cấu hình sẽ tự động ghi lại tại đây.',
                          style: TextStyle(fontSize: 13, color: AppTheme.textMutedDark),
                        ),
                      ],
                    ),
                  );
                }

                return ListView.builder(
                  itemCount: controller.events.length,
                  itemBuilder: (context, index) {
                    final item = controller.events[index];
                    final action = item['action'] as String? ?? 'action';
                    final actorType = item['actor_type'] as String? ?? 'system';
                    final targetType = item['target_type'] as String? ?? 'target';
                    final createdAt = item['created_at'] as String? ?? '';
                    final metadata = item['metadata'] as Map<String, dynamic>?;

                    return Container(
                      margin: const EdgeInsets.only(bottom: 10),
                      padding: const EdgeInsets.all(14),
                      decoration: BoxDecoration(
                        color: const Color(0xFF0D172A),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: const Color(0xFF1E293B)),
                      ),
                      child: Row(
                        children: [
                          Container(
                            padding: const EdgeInsets.all(8),
                            decoration: BoxDecoration(
                              color: const Color(0xFF00F0FF).withValues(alpha: 0.12),
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: const Icon(Icons.security, size: 20, color: Color(0xFF00F0FF)),
                          ),
                          const SizedBox(width: 14),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    Text(
                                      action,
                                      style: const TextStyle(
                                        fontSize: 14,
                                        fontWeight: FontWeight.bold,
                                        color: Colors.white,
                                      ),
                                    ),
                                    const SizedBox(width: 10),
                                    Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                      decoration: BoxDecoration(
                                        color: const Color(0xFF1E293B),
                                        borderRadius: BorderRadius.circular(4),
                                      ),
                                      child: Text(
                                        actorType.toUpperCase(),
                                        style: const TextStyle(fontSize: 10, color: Color(0xFF38BDF8), fontWeight: FontWeight.bold),
                                      ),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  'Mục tiêu: $targetType · Thời gian: $createdAt',
                                  style: const TextStyle(fontSize: 12, color: AppTheme.textMutedDark),
                                ),
                              ],
                            ),
                          ),
                          if (metadata != null && metadata.isNotEmpty)
                            OutlinedButton.icon(
                              onPressed: () {
                                _showMetadataDialog(context, metadata);
                              },
                              style: OutlinedButton.styleFrom(
                                foregroundColor: const Color(0xFF38BDF8),
                                side: const BorderSide(color: Color(0xFF1E293B)),
                                minimumSize: const Size(64, 36),
                                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(100)),
                                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                              ),
                              icon: const Icon(Icons.code, size: 14),
                              label: const Text('Chi tiết JSON', style: TextStyle(fontSize: 11)),
                            ),
                        ],
                      ),
                    );
                  },
                );
              }),
            ),
          ],
        ),
      ),
    );
  }

  void _showMetadataDialog(BuildContext context, Map<String, dynamic> metadata) {
    Get.dialog(
      Dialog(
        backgroundColor: const Color(0xFF0D172A),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(14),
          side: const BorderSide(color: Color(0xFF1E293B)),
        ),
        child: Padding(
          padding: const EdgeInsets.all(20.0),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text(
                    'Metadata Payload',
                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close, color: Colors.white),
                    onPressed: () => Get.back(),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFF070C18),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: const Color(0xFF1E293B)),
                ),
                child: Text(
                  const JsonEncoder.withIndent('  ').convert(metadata),
                  style: const TextStyle(fontFamily: 'monospace', fontSize: 12, color: Color(0xFF00F0FF)),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
