import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../controllers/prompt_registry_controller.dart';

class PromptRegistryView extends StatelessWidget {
  const PromptRegistryView({super.key});

  @override
  Widget build(BuildContext context) {
    final controller = Get.put(PromptRegistryController());

    return Scaffold(
      backgroundColor: const Color(0xFF060A14),
      body: Obx(() {
        if (controller.isLoading.value) {
          return const Center(child: CircularProgressIndicator());
        }
        final grouped = <String, List<Map<String, dynamic>>>{};
        for (final prompt in controller.prompts) {
          grouped.putIfAbsent(prompt['domain'] as String, () => []).add(prompt);
        }
        final domains = grouped.keys.toList()..sort();
        return ListView(
          padding: const EdgeInsets.all(16),
          children: [
            for (final domain in domains)
              ExpansionTile(
                title: Text(domain, style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.white)),
                initiallyExpanded: true,
                children: [
                  for (final prompt in grouped[domain]!)
                    ListTile(
                      title: Text(prompt['name'] as String, style: const TextStyle(color: Colors.white70)),
                      subtitle: Wrap(
                        spacing: 8,
                        children: [
                          if (prompt['is_overridden'] == true) const Chip(label: Text('Đã tuỳ chỉnh')),
                          if (prompt['is_wired'] != true) const Chip(label: Text('Chưa có tính năng AI dùng')),
                        ],
                      ),
                      onTap: () => _openDetail(context, controller, domain, prompt['name'] as String),
                    ),
                ],
              ),
          ],
        );
      }),
    );
  }

  Future<void> _openDetail(
    BuildContext context,
    PromptRegistryController controller,
    String domain,
    String name,
  ) async {
    final detail = await controller.loadDetail(domain, name);
    final textController = TextEditingController(text: detail['content'] as String? ?? '');
    final revisions = (detail['revisions'] as List?) ?? [];

    if (!context.mounted) return;
    await showDialog(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text('$domain/$name'),
        content: SizedBox(
          width: 480,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: textController,
                maxLines: 10,
                enabled: controller.isOwner.value,
                decoration: const InputDecoration(border: OutlineInputBorder()),
              ),
              const SizedBox(height: 12),
              Text('Lịch sử: ${revisions.length} phiên bản', style: Theme.of(dialogContext).textTheme.bodySmall),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(),
            child: const Text('Đóng'),
          ),
          if (controller.isOwner.value) ...[
            TextButton(
              onPressed: () async {
                await controller.resetPrompt(domain, name);
                if (dialogContext.mounted) Navigator.of(dialogContext).pop();
              },
              child: const Text('Đặt lại mặc định'),
            ),
            FilledButton(
              onPressed: () async {
                await controller.savePrompt(domain, name, textController.text);
                if (dialogContext.mounted) Navigator.of(dialogContext).pop();
              },
              child: const Text('Lưu'),
            ),
          ],
        ],
      ),
    );
  }
}
