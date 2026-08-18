import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/theme/app_theme.dart';
import '../controllers/ai_team_controller.dart';

class AiTeamSkillToolHubDialog {
  static void show(BuildContext context, AiTeamController controller) {
    final selectedTab = RxInt(0);

    showDialog(
      context: context,
      builder: (ctx) {
        return Dialog(
          backgroundColor: AppTheme.surfaceDarkElevated,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
            side: const BorderSide(color: AppTheme.borderDark),
          ),
          insetPadding:
              const EdgeInsets.symmetric(horizontal: 30, vertical: 24),
          child: Container(
            width: 850,
            constraints: const BoxConstraints(maxHeight: 750),
            child: Column(
              children: [
                // Header
                Container(
                  padding: const EdgeInsets.all(18),
                  decoration: const BoxDecoration(
                    border:
                        Border(bottom: BorderSide(color: AppTheme.borderDark)),
                  ),
                  child: Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(8),
                        decoration: BoxDecoration(
                          color:
                              const Color(0xFF6366F1).withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: const Icon(Icons.hub_rounded,
                            color: Color(0xFF818CF8), size: 22),
                      ),
                      const SizedBox(width: 12),
                      const Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Kho Kỹ năng & Cổng Công cụ Mở rộng (Skill & Tool Hub)',
                            style: TextStyle(
                                fontSize: 16,
                                fontWeight: FontWeight.bold,
                                color: AppTheme.textDark),
                          ),
                          SizedBox(height: 2),
                          Text(
                            'Quản lý quy trình SOP (SKILL.md), kết nối Webhook APIs và phân quyền cho AI Workforce',
                            style: TextStyle(
                                fontSize: 12, color: AppTheme.textMutedDark),
                          ),
                        ],
                      ),
                      const Spacer(),
                      IconButton(
                        icon: const Icon(Icons.close,
                            color: AppTheme.textMutedDark, size: 20),
                        onPressed: () => Navigator.of(ctx).pop(),
                      ),
                    ],
                  ),
                ),

                // Tabs Selector
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 18, vertical: 10),
                  color: AppTheme.surfaceDark,
                  child: Row(
                    children: [
                      Obx(() => ChoiceChip(
                            label: const Text('Kho Kỹ năng SOP (SKILL.md)',
                                style: TextStyle(
                                    fontSize: 13, fontWeight: FontWeight.bold)),
                            selected: selectedTab.value == 0,
                            selectedColor:
                                AppTheme.primary.withValues(alpha: 0.2),
                            checkmarkColor: AppTheme.primary,
                            onSelected: (val) => selectedTab.value = 0,
                          )),
                      const SizedBox(width: 8),
                      Obx(() => ChoiceChip(
                            label: const Text('Cổng Công cụ & Webhook APIs',
                                style: TextStyle(
                                    fontSize: 13, fontWeight: FontWeight.bold)),
                            selected: selectedTab.value == 1,
                            selectedColor:
                                const Color(0xFF6366F1).withValues(alpha: 0.2),
                            checkmarkColor: const Color(0xFF818CF8),
                            onSelected: (val) => selectedTab.value = 1,
                          )),
                      const Spacer(),
                      Obx(() {
                        if (selectedTab.value == 0) {
                          return ElevatedButton.icon(
                            style: ElevatedButton.styleFrom(
                              backgroundColor: AppTheme.primary,
                              foregroundColor: Colors.black,
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 12, vertical: 8),
                            ),
                            onPressed: () =>
                                _showUploadSkillDialog(context, controller),
                            icon:
                                const Icon(Icons.upload_file_rounded, size: 15),
                            label: const Text('+ Nạp SKILL.md / Tạo SOP',
                                style: TextStyle(
                                    fontSize: 12, fontWeight: FontWeight.bold)),
                          );
                        } else {
                          return ElevatedButton.icon(
                            style: ElevatedButton.styleFrom(
                              backgroundColor: const Color(0xFF6366F1),
                              foregroundColor: Colors.white,
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 12, vertical: 8),
                            ),
                            onPressed: () => _showCreateWebhookToolDialog(
                                context, controller),
                            icon: const Icon(Icons.webhook_rounded, size: 15),
                            label: const Text('+ Thêm Webhook Tool',
                                style: TextStyle(
                                    fontSize: 12, fontWeight: FontWeight.bold)),
                          );
                        }
                      }),
                    ],
                  ),
                ),

                // Content
                Expanded(
                  child: Obx(() {
                    if (selectedTab.value == 0) {
                      final skills = controller.availableSkills;
                      if (skills.isEmpty) {
                        return const Center(
                          child: Text('Chưa có Kỹ năng nào được nạp.',
                              style: TextStyle(color: AppTheme.textMutedDark)),
                        );
                      }
                      return ListView.separated(
                        padding: const EdgeInsets.all(18),
                        itemCount: skills.length,
                        separatorBuilder: (c, i) => const SizedBox(height: 10),
                        itemBuilder: (c, i) {
                          final s = skills[i];
                          final id = s['id'] ?? '';
                          final name = s['name'] ?? id;
                          final dept = s['department'] ?? 'General';
                          final desc = s['description'] ?? '';
                          final tools = (s['required_tools'] as List?)
                                  ?.map((e) => e.toString())
                                  .toList() ??
                              [];

                          return Container(
                            padding: const EdgeInsets.all(14),
                            decoration: BoxDecoration(
                              color: AppTheme.surfaceDarkLighter,
                              borderRadius: BorderRadius.circular(10),
                              border: Border.all(color: AppTheme.borderDark),
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    const Icon(Icons.psychology_rounded,
                                        size: 18, color: AppTheme.primary),
                                    const SizedBox(width: 8),
                                    Text(name,
                                        style: const TextStyle(
                                            fontWeight: FontWeight.bold,
                                            fontSize: 14,
                                            color: AppTheme.textDark)),
                                    const SizedBox(width: 8),
                                    Container(
                                      padding: const EdgeInsets.symmetric(
                                          horizontal: 6, vertical: 2),
                                      decoration: BoxDecoration(
                                        color: AppTheme.primary
                                            .withValues(alpha: 0.12),
                                        borderRadius: BorderRadius.circular(4),
                                      ),
                                      child: Text(dept,
                                          style: const TextStyle(
                                              fontSize: 10.5,
                                              color: AppTheme.primary,
                                              fontWeight: FontWeight.bold)),
                                    ),
                                    const Spacer(),
                                    Text('v${s['version'] ?? '1.0'}',
                                        style: const TextStyle(
                                            fontSize: 11,
                                            color: AppTheme.textMutedDark)),
                                  ],
                                ),
                                if (desc.isNotEmpty) ...[
                                  const SizedBox(height: 6),
                                  Text(desc,
                                      style: const TextStyle(
                                          fontSize: 12.5,
                                          color: AppTheme.textMutedDark)),
                                ],
                                if (tools.isNotEmpty) ...[
                                  const SizedBox(height: 8),
                                  Wrap(
                                    spacing: 6,
                                    children: tools
                                        .map((t) => Chip(
                                              label: Text(t,
                                                  style: const TextStyle(
                                                      fontSize: 10.5,
                                                      fontFamily:
                                                          'monospace')),
                                              backgroundColor: AppTheme
                                                  .surfaceDarkElevated,
                                              padding: EdgeInsets.zero,
                                            ))
                                        .toList(),
                                  ),
                                ],
                              ],
                            ),
                          );
                        },
                      );
                    } else {
                      final tools = controller.availableTools;
                      if (tools.isEmpty) {
                        return const Center(
                          child: Text(
                              'Chưa có công cụ mở rộng nào trong Registry.',
                              style: TextStyle(color: AppTheme.textMutedDark)),
                        );
                      }
                      return ListView.separated(
                        padding: const EdgeInsets.all(18),
                        itemCount: tools.length,
                        separatorBuilder: (c, i) => const SizedBox(height: 10),
                        itemBuilder: (c, i) {
                          final t = tools[i];
                          final key = t['key'] ?? '';
                          final name = t['name'] ?? key;
                          final desc = t['description'] ?? '';
                          final transport = t['transport'] ?? 'local';

                          return Container(
                            padding: const EdgeInsets.all(14),
                            decoration: BoxDecoration(
                              color: AppTheme.surfaceDarkLighter,
                              borderRadius: BorderRadius.circular(10),
                              border: Border.all(color: AppTheme.borderDark),
                            ),
                            child: Row(
                              children: [
                                Container(
                                  padding: const EdgeInsets.all(8),
                                  decoration: BoxDecoration(
                                    color: const Color(0xFF6366F1)
                                        .withValues(alpha: 0.15),
                                    borderRadius: BorderRadius.circular(8),
                                  ),
                                  child: const Icon(Icons.bolt_rounded,
                                      color: Color(0xFF818CF8), size: 18),
                                ),
                                const SizedBox(width: 12),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Row(
                                        children: [
                                          Text(name,
                                              style: const TextStyle(
                                                  fontWeight: FontWeight.bold,
                                                  fontSize: 13.5,
                                                  color: AppTheme.textDark)),
                                          const SizedBox(width: 8),
                                          Container(
                                            padding: const EdgeInsets.symmetric(
                                                horizontal: 6, vertical: 2),
                                            decoration: BoxDecoration(
                                              color:
                                                  AppTheme.surfaceDarkElevated,
                                              borderRadius:
                                                  BorderRadius.circular(4),
                                              border: Border.all(
                                                  color: AppTheme.borderDark),
                                            ),
                                            child: Text(
                                                transport
                                                    .toString()
                                                    .toUpperCase(),
                                                style: const TextStyle(
                                                    fontSize: 10,
                                                    color: Color(0xFFA5B4FC),
                                                    fontWeight:
                                                        FontWeight.bold)),
                                          ),
                                        ],
                                      ),
                                      const SizedBox(height: 2),
                                      Text('$key · $desc',
                                          style: const TextStyle(
                                              fontSize: 12,
                                              color: AppTheme.textMutedDark)),
                                    ],
                                  ),
                                ),
                              ],
                            ),
                          );
                        },
                      );
                    }
                  }),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  static void _showUploadSkillDialog(
      BuildContext context, AiTeamController controller) {
    final contentController = TextEditingController(
      text: '---\n'
          'id: custom_sop_skill\n'
          'name: Kỹ Năng Quy Trình Nghiệp Vụ Mới\n'
          'department: Marketing\n'
          'version: 1.0.0\n'
          'description: Hướng dẫn chi tiết các bước xử lý tác vụ.\n'
          'required_tools:\n'
          '  - google.search\n'
          '  - tasks.create\n'
          '---\n\n'
          '# HƯỚNG DẪN QUY TRÌNH THỰC THI (SOP)\n\n'
          '## Bước 1: Tiếp nhận yêu cầu\n'
          '...\n\n'
          '## Bước 2: Kiểm tra dữ liệu\n'
          '...\n',
    );

    Get.defaultDialog(
      title: 'Nạp File Kỹ Năng (SKILL.md)',
      titleStyle: const TextStyle(
          fontSize: 16, fontWeight: FontWeight.bold, color: AppTheme.textDark),
      backgroundColor: AppTheme.surfaceDarkElevated,
      contentPadding: const EdgeInsets.all(20),
      content: SizedBox(
        width: 550,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Dán nội dung SKILL.md (gồm YAML Frontmatter và Markdown SOP) để kích hoạt Kỹ năng cho hệ thống:',
              style: TextStyle(fontSize: 12.5, color: AppTheme.textMutedDark),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: contentController,
              maxLines: 10,
              style: const TextStyle(
                  fontSize: 12,
                  fontFamily: 'monospace',
                  color: AppTheme.textDark),
              decoration: InputDecoration(
                filled: true,
                fillColor: AppTheme.surfaceDarkLighter,
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
              ),
            ),
          ],
        ),
      ),
      confirm: ElevatedButton(
        style: ElevatedButton.styleFrom(
            backgroundColor: AppTheme.primary, foregroundColor: Colors.black),
        onPressed: () async {
          final content = contentController.text.trim();
          if (content.isNotEmpty) {
            Get.back();
            await controller.uploadCustomSkill(content);
          }
        },
        child: const Text('Kích hoạt Kỹ năng'),
      ),
      cancel: OutlinedButton(
        style: OutlinedButton.styleFrom(foregroundColor: AppTheme.textMutedDark),
        onPressed: () => Get.back(),
        child: const Text('Hủy'),
      ),
    );
  }

  static void _showCreateWebhookToolDialog(
      BuildContext context, AiTeamController controller) {
    final nameController = TextEditingController();
    final keyController = TextEditingController();
    final urlController = TextEditingController();
    final methodController = RxString('POST');

    Get.defaultDialog(
      title: 'Thêm Webhook API Tool',
      titleStyle: const TextStyle(
          fontSize: 16, fontWeight: FontWeight.bold, color: AppTheme.textDark),
      backgroundColor: AppTheme.surfaceDarkElevated,
      contentPadding: const EdgeInsets.all(20),
      content: SizedBox(
        width: 500,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            TextField(
              controller: nameController,
              style: const TextStyle(color: AppTheme.textDark, fontSize: 13),
              decoration: InputDecoration(
                labelText: 'Tên Công cụ *',
                hintText: 'vd: Gửi đơn hàng sang CRM',
                labelStyle: const TextStyle(color: AppTheme.primary),
                filled: true,
                fillColor: AppTheme.surfaceDarkLighter,
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
              ),
            ),
            const SizedBox(height: 10),
            TextField(
              controller: keyController,
              style: const TextStyle(
                  color: AppTheme.textDark,
                  fontSize: 13,
                  fontFamily: 'monospace'),
              decoration: InputDecoration(
                labelText: 'Tool Key *',
                hintText: 'vd: webhook.crm_order',
                labelStyle: const TextStyle(color: Color(0xFF818CF8)),
                filled: true,
                fillColor: AppTheme.surfaceDarkLighter,
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
              ),
            ),
            const SizedBox(height: 10),
            TextField(
              controller: urlController,
              style: const TextStyle(
                  color: AppTheme.textDark,
                  fontSize: 13,
                  fontFamily: 'monospace'),
              decoration: InputDecoration(
                labelText: 'Webhook URL Endpoint *',
                hintText: 'https://api.yourdomain.com/webhook/v1',
                labelStyle: const TextStyle(color: AppTheme.primary),
                filled: true,
                fillColor: AppTheme.surfaceDarkLighter,
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
              ),
            ),
          ],
        ),
      ),
      confirm: ElevatedButton(
        style: ElevatedButton.styleFrom(
            backgroundColor: const Color(0xFF6366F1),
            foregroundColor: Colors.white),
        onPressed: () async {
          final name = nameController.text.trim();
          var key = keyController.text.trim();
          final url = urlController.text.trim();
          if (name.isEmpty || url.isEmpty) {
            Get.snackbar('Thiếu dữ liệu', 'Vui lòng nhập Tên và URL Webhook');
            return;
          }
          if (key.isEmpty) {
            key =
                'webhook.${name.toLowerCase().replaceAll(RegExp(r'[^a-z0-9]'), '_')}';
          }
          Get.back();
          await controller.createWebhookTool({
            'key': key,
            'name': name,
            'webhook_url': url,
            'http_method': methodController.value,
          });
        },
        child: const Text('Tạo Webhook Tool'),
      ),
      cancel: OutlinedButton(
        style: OutlinedButton.styleFrom(foregroundColor: AppTheme.textMutedDark),
        onPressed: () => Get.back(),
        child: const Text('Hủy'),
      ),
    );
  }
}
