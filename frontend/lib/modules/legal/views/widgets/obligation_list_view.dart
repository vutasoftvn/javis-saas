import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../controllers/legal_obligation_controller.dart';

class ObligationListView extends StatelessWidget {
  const ObligationListView({super.key});

  Future<String?> _promptEvidence(BuildContext context) async {
    final controller = TextEditingController();
    return showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF0F172A),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        title: const Text('Đính kèm bằng chứng hoàn thành', style: TextStyle(color: Colors.white, fontSize: 16)),
        content: TextField(
          controller: controller,
          maxLines: 2,
          style: const TextStyle(color: Colors.white, fontSize: 14),
          decoration: const InputDecoration(
            hintText: 'Nhập URI hoặc mã tài liệu chứng minh (bắt buộc)...',
            hintStyle: TextStyle(color: Color(0xFF64748B), fontSize: 13),
            filled: true,
            fillColor: Color(0xFF1E293B),
            border: OutlineInputBorder(),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(null),
            child: const Text('Huỷ', style: TextStyle(color: Color(0xFF94A3B8))),
          ),
          ElevatedButton(
            onPressed: () {
              final text = controller.text.trim();
              if (text.isNotEmpty) Navigator.of(ctx).pop(text);
            },
            style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF10B981)),
            child: const Text('Xác nhận', style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final controller = Get.put(LegalObligationController());

    return Obx(() {
      if (controller.isLoading.value && controller.instances.isEmpty) {
        return const Center(child: CircularProgressIndicator());
      }

      if (controller.instances.isEmpty) {
        return Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text('Không có nghĩa vụ pháp lý nào', style: TextStyle(color: Color(0xFF94A3B8))),
              const SizedBox(height: 12),
              ElevatedButton(
                onPressed: () => controller.loadInstances(),
                child: const Text('Tải lại'),
              ),
            ],
          ),
        );
      }

      return ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: controller.instances.length,
        itemBuilder: (ctx, index) {
          final item = controller.instances[index];
          final id = item['id']?.toString() ?? '';
          final title = item['title']?.toString() ?? 'Nghĩa vụ';
          final status = item['status']?.toString() ?? 'OPEN';
          final periodKey = item['periodKey']?.toString() ?? item['period_key']?.toString();
          final dueDate = item['dueDate']?.toString() ?? item['due_date']?.toString();
          final isOpen = status == 'OPEN';
          final isInProgress = status == 'IN_PROGRESS';
          final isFulfilled = status == 'FULFILLED';

          return Container(
            margin: const EdgeInsets.only(bottom: 12),
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: const Color(0xFF1E293B),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: isFulfilled
                    ? const Color(0xFF10B981).withValues(alpha: 0.3)
                    : (isInProgress ? const Color(0xFF38BDF8).withValues(alpha: 0.3) : const Color(0xFF334155)),
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Expanded(
                      child: Text(
                        title,
                        style: const TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.bold),
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: isFulfilled
                            ? const Color(0xFF10B981).withValues(alpha: 0.2)
                            : (isInProgress ? const Color(0xFF38BDF8).withValues(alpha: 0.2) : const Color(0xFF64748B).withValues(alpha: 0.2)),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        status,
                        style: TextStyle(
                          color: isFulfilled
                              ? const Color(0xFF10B981)
                              : (isInProgress ? const Color(0xFF38BDF8) : const Color(0xFF94A3B8)),
                          fontSize: 11,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                if (periodKey != null && periodKey.isNotEmpty)
                  Text('Kỳ áp dụng: $periodKey', style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 12)),
                if (dueDate != null && dueDate.isNotEmpty)
                  Text('Hạn chót: $dueDate', style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 12)),
                const SizedBox(height: 12),
                Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    if (isOpen)
                      ElevatedButton(
                        onPressed: () => controller.startObligation(id),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF3B82F6),
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                        ),
                        child: const Text('Bắt đầu thực hiện', style: TextStyle(color: Colors.white, fontSize: 12)),
                      ),
                    if (isInProgress)
                      ElevatedButton(
                        onPressed: () async {
                          final evidence = await _promptEvidence(context);
                          if (evidence != null && evidence.isNotEmpty) {
                            await controller.fulfillObligationWithEvidence(
                              id,
                              evidenceRefs: [evidence],
                            );
                          }
                        },
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF10B981),
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                        ),
                        child: const Text('Hoàn thành (Kèm chứng từ)', style: TextStyle(color: Colors.white, fontSize: 12)),
                      ),
                    if (isFulfilled)
                      const Row(
                        children: [
                          Icon(Icons.check_circle, color: Color(0xFF10B981), size: 16),
                          SizedBox(width: 4),
                          Text('Đã hoàn thành', style: TextStyle(color: Color(0xFF10B981), fontSize: 12)),
                        ],
                      ),
                  ],
                ),
              ],
            ),
          );
        },
      );
    });
  }
}
