import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/theme/app_theme.dart';
import '../controllers/ai_team_controller.dart';
import 'ai_team_helpers.dart';

class AiTeamAgentStudioDialog {
  static void show(
    BuildContext context,
    AiTeamController controller, {
    Map<String, dynamic>? initialAgent,
  }) {
    final isEdit = initialAgent != null;
    final nameController =
        TextEditingController(text: initialAgent?['name'] ?? '');
    final keyController =
        TextEditingController(text: initialAgent?['key'] ?? '');
    final roleController = TextEditingController(
        text: initialAgent?['role_title'] ?? initialAgent?['role'] ?? '');
    final descController =
        TextEditingController(text: initialAgent?['description'] ?? '');
    final promptController = TextEditingController(
      text: initialAgent?['system_prompt'] ??
          'Bạn là một Chuyên viên AI mẫn cán trong doanh nghiệp.\nHãy giải quyết các yêu cầu với tư duy logic, bám sát dữ liệu và mục tiêu kinh doanh.',
    );
    final selectedDept =
        RxString(initialAgent?['department'] ?? 'Marketing');
    final selectedProfile =
        RxString(initialAgent?['default_model_profile'] ?? 'reasoning');
    final selectedRisk = RxInt(initialAgent?['risk_level'] ?? 1);
    final currentTools =
        RxList<String>(AiTeamHelpers.getAgentToolsList(initialAgent ?? {}));

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
              const EdgeInsets.symmetric(horizontal: 40, vertical: 30),
          child: Container(
            width: 750,
            constraints: const BoxConstraints(maxHeight: 700),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Header
                Container(
                  padding: const EdgeInsets.all(20),
                  decoration: const BoxDecoration(
                    border:
                        Border(bottom: BorderSide(color: AppTheme.borderDark)),
                  ),
                  child: Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(8),
                        decoration: BoxDecoration(
                          color: AppTheme.primary.withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: const Icon(Icons.person_add_alt_1_rounded,
                            color: AppTheme.primary, size: 20),
                      ),
                      const SizedBox(width: 12),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            isEdit
                                ? 'Agent Studio: Chỉnh sửa Nhân sự AI'
                                : 'Agent Studio: Tạo Nhân sự AI Mới',
                            style: const TextStyle(
                                fontSize: 16,
                                fontWeight: FontWeight.bold,
                                color: AppTheme.textDark),
                          ),
                          const SizedBox(height: 2),
                          const Text(
                            'Định hình Persona, phạm vi công việc, chỉ đạo thực thi và cấp quyền công cụ',
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

                // Body
                Expanded(
                  child: SingleChildScrollView(
                    padding: const EdgeInsets.all(20),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // Row 1: Name & Key
                        Row(
                          children: [
                            Expanded(
                              flex: 3,
                              child: TextField(
                                controller: nameController,
                                style: const TextStyle(
                                    color: AppTheme.textDark, fontSize: 13.5),
                                decoration: InputDecoration(
                                  labelText: 'Tên Nhân sự AI *',
                                  hintText:
                                      'vd: Chuyên viên TikTok Live Commerce',
                                  labelStyle:
                                      const TextStyle(color: AppTheme.primary),
                                  filled: true,
                                  fillColor: AppTheme.surfaceDarkLighter,
                                  border: OutlineInputBorder(
                                      borderRadius: BorderRadius.circular(8)),
                                ),
                              ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              flex: 2,
                              child: TextField(
                                controller: keyController,
                                style: const TextStyle(
                                    color: AppTheme.textDark,
                                    fontSize: 13.5,
                                    fontFamily: 'monospace'),
                                decoration: InputDecoration(
                                  labelText: 'Mã Key *',
                                  hintText: 'vd: tiktok_agent',
                                  labelStyle: const TextStyle(
                                      color: Color(0xFF818CF8)),
                                  filled: true,
                                  fillColor: AppTheme.surfaceDarkLighter,
                                  border: OutlineInputBorder(
                                      borderRadius: BorderRadius.circular(8)),
                                ),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 14),

                        // Row 2: Role & Department
                        Row(
                          children: [
                            Expanded(
                              child: TextField(
                                controller: roleController,
                                style: const TextStyle(
                                    color: AppTheme.textDark, fontSize: 13.5),
                                decoration: InputDecoration(
                                  labelText: 'Chức danh / Vị trí *',
                                  hintText: 'vd: Senior E-Commerce Specialist',
                                  labelStyle:
                                      const TextStyle(color: AppTheme.primary),
                                  filled: true,
                                  fillColor: AppTheme.surfaceDarkLighter,
                                  border: OutlineInputBorder(
                                      borderRadius: BorderRadius.circular(8)),
                                ),
                              ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Obx(() => DropdownButtonFormField<String>(
                                    initialValue: selectedDept.value,
                                    dropdownColor: AppTheme.surfaceDarkElevated,
                                    style: const TextStyle(
                                        color: AppTheme.textDark,
                                        fontSize: 13.5),
                                    decoration: InputDecoration(
                                      labelText: 'Phòng ban *',
                                      labelStyle: const TextStyle(
                                          color: AppTheme.primary),
                                      filled: true,
                                      fillColor: AppTheme.surfaceDarkLighter,
                                      border: OutlineInputBorder(
                                          borderRadius:
                                              BorderRadius.circular(8)),
                                    ),
                                    items: const [
                                      DropdownMenuItem(
                                          value: 'Executive Office',
                                          child: Text(
                                              'Executive Office (Điều hành)')),
                                      DropdownMenuItem(
                                          value: 'Finance',
                                          child: Text('Finance (Tài chính)')),
                                      DropdownMenuItem(
                                          value: 'Marketing',
                                          child: Text('Marketing & Growth')),
                                      DropdownMenuItem(
                                          value: 'Sales',
                                          child: Text('Sales & CRM')),
                                      DropdownMenuItem(
                                          value: 'Engineering',
                                          child:
                                              Text('Engineering & Tech')),
                                      DropdownMenuItem(
                                          value: 'Operations',
                                          child:
                                              Text('Operations (Vận hành)')),
                                      DropdownMenuItem(
                                          value: 'Legal & Compliance',
                                          child: Text(
                                              'Legal & Compliance (Pháp lý)')),
                                      DropdownMenuItem(
                                          value: 'Human Resources',
                                          child: Text('HR & People')),
                                    ],
                                    onChanged: (val) {
                                      if (val != null) selectedDept.value = val;
                                    },
                                  )),
                            ),
                          ],
                        ),
                        const SizedBox(height: 14),

                        // Row 3: Description
                        TextField(
                          controller: descController,
                          maxLines: 2,
                          style: const TextStyle(
                              color: AppTheme.textDark, fontSize: 13),
                          decoration: InputDecoration(
                            labelText: 'Mô tả vai trò & trách nhiệm',
                            hintText:
                                'Tóm tắt ngắn gọn mục tiêu công việc mà Agent này phụ trách...',
                            labelStyle:
                                const TextStyle(color: AppTheme.primary),
                            filled: true,
                            fillColor: AppTheme.surfaceDarkLighter,
                            border: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(8)),
                          ),
                        ),
                        const SizedBox(height: 16),

                        // System Prompt
                        Row(
                          children: [
                            const Icon(Icons.terminal_rounded,
                                size: 16, color: Color(0xFF818CF8)),
                            const SizedBox(width: 6),
                            const Text(
                              'System Prompt & Chỉ đạo tác vụ (Markdown)',
                              style: TextStyle(
                                  fontSize: 13.5,
                                  fontWeight: FontWeight.bold,
                                  color: AppTheme.textDark),
                            ),
                            const Spacer(),
                            TextButton.icon(
                              onPressed: () {
                                promptController.text =
                                    '# BẠN LÀ CHUYÊN VIÊN AI DOANH NGHIỆP\n\n'
                                    '## 1. MỤC TIÊU VÀ SỨ MỆNH\n'
                                    '- Chịu trách nhiệm thực thi các nhiệm vụ chuyên môn theo tiêu chuẩn cao nhất.\n'
                                    '- Luôn phối hợp dữ liệu với các Agent khác trong Control Plane.\n\n'
                                    '## 2. QUY TRÌNH THỰC THI (SOP)\n'
                                    '1. Tiếp nhận và phân tích ngữ cảnh yêu cầu.\n'
                                    '2. Thu thập dữ liệu từ các công cụ (Tools) được cấp quyền.\n'
                                    '3. Bàn giao kết quả rõ ràng, có căn cứ số liệu.\n';
                              },
                              icon: const Icon(Icons.auto_fix_high_rounded,
                                  size: 14, color: AppTheme.primary),
                              label: const Text('Nạp mẫu Prompt chuẩn',
                                  style: TextStyle(fontSize: 11.5)),
                            ),
                          ],
                        ),
                        const SizedBox(height: 6),
                        TextField(
                          controller: promptController,
                          maxLines: 6,
                          minLines: 4,
                          style: const TextStyle(
                              color: AppTheme.textDark,
                              fontSize: 12.5,
                              fontFamily: 'monospace'),
                          decoration: InputDecoration(
                            hintText: 'Nhập hướng dẫn chi tiết cho Agent...',
                            filled: true,
                            fillColor: AppTheme.surfaceDarkLighter,
                            border: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(8)),
                          ),
                        ),
                        const SizedBox(height: 16),

                        // Model Profile & Risk
                        Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Expanded(
                              flex: 3,
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  const Text('Mô hình AI ưu tiên:',
                                      style: TextStyle(
                                          fontSize: 12.5,
                                          fontWeight: FontWeight.bold,
                                          color: AppTheme.textDark)),
                                  const SizedBox(height: 6),
                                  Obx(() => Row(
                                        children: [
                                          _buildProfileOption(
                                            title: 'Tư duy sâu',
                                            subtitle: 'Gemini 2.5 Pro',
                                            selected: selectedProfile.value ==
                                                'reasoning',
                                            onTap: () => selectedProfile
                                                .value = 'reasoning',
                                          ),
                                          const SizedBox(width: 8),
                                          _buildProfileOption(
                                            title: 'Tốc độ',
                                            subtitle: 'Flash',
                                            selected: selectedProfile.value ==
                                                'fast',
                                            onTap: () =>
                                                selectedProfile.value = 'fast',
                                          ),
                                          const SizedBox(width: 8),
                                          _buildProfileOption(
                                            title: 'Code',
                                            subtitle: 'Claude 3.7',
                                            selected: selectedProfile.value ==
                                                'coding',
                                            onTap: () => selectedProfile
                                                .value = 'coding',
                                          ),
                                        ],
                                      )),
                                ],
                              ),
                            ),
                            const SizedBox(width: 16),
                            Expanded(
                              flex: 2,
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(
                                    children: [
                                      const Text('Cấp phép Tools:',
                                          style: TextStyle(
                                              fontSize: 12.5,
                                              fontWeight: FontWeight.bold,
                                              color: AppTheme.textDark)),
                                      const Spacer(),
                                      TextButton(
                                        onPressed: () => _showToolPickerModal(
                                            context,
                                            currentTools,
                                            controller),
                                        child: const Text('Chọn Tools (+)',
                                            style: TextStyle(fontSize: 11.5)),
                                      ),
                                    ],
                                  ),
                                  Obx(() => Wrap(
                                        spacing: 4,
                                        runSpacing: 4,
                                        children: currentTools
                                            .map((t) => Chip(
                                                  label: Text(t,
                                                      style: const TextStyle(
                                                          fontSize: 10.5,
                                                          fontFamily:
                                                              'monospace')),
                                                  backgroundColor: AppTheme
                                                      .surfaceDarkLighter,
                                                  padding: EdgeInsets.zero,
                                                ))
                                            .toList(),
                                      )),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),

                // Footer
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
                  decoration: const BoxDecoration(
                    border:
                        Border(top: BorderSide(color: AppTheme.borderDark)),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.end,
                    children: [
                      OutlinedButton(
                        style: OutlinedButton.styleFrom(
                          foregroundColor: AppTheme.textMutedDark,
                          side: const BorderSide(color: AppTheme.borderDark),
                        ),
                        onPressed: () => Navigator.of(ctx).pop(),
                        child: const Text('Hủy'),
                      ),
                      const SizedBox(width: 12),
                      ElevatedButton.icon(
                        style: ElevatedButton.styleFrom(
                          backgroundColor: AppTheme.primary,
                          foregroundColor: Colors.black,
                          padding: const EdgeInsets.symmetric(
                              horizontal: 20, vertical: 12),
                        ),
                        onPressed: () async {
                          final name = nameController.text.trim();
                          var key = keyController.text.trim();
                          if (name.isEmpty) {
                            Get.snackbar('Thiếu thông tin',
                                'Vui lòng nhập Tên nhân sự AI');
                            return;
                          }
                          if (key.isEmpty) {
                            key = name
                                .toLowerCase()
                                .replaceAll(RegExp(r'[^a-z0-9]'), '_');
                          }

                          final agentData = {
                            'key': key,
                            'name': name,
                            'role_title': roleController.text.trim().isNotEmpty
                                ? roleController.text.trim()
                                : name,
                            'department': selectedDept.value,
                            'description': descController.text.trim(),
                            'agent_type': 'specialist',
                            'default_model_profile': selectedProfile.value,
                            'system_prompt_key': '$key.system',
                            'risk_level': selectedRisk.value,
                            'status': 'idle',
                            'enabled': true,
                            'config': {
                              'is_system': false,
                              'custom_tools': currentTools.toList(),
                            },
                          };

                          Navigator.of(ctx).pop();
                          await controller.createCustomAgent(agentData);
                        },
                        icon: const Icon(Icons.check_circle_outline, size: 16),
                        label: Text(
                            isEdit
                                ? 'Lưu thay đổi'
                                : 'Bổ nhiệm Nhân sự AI',
                            style:
                                const TextStyle(fontWeight: FontWeight.bold)),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  static void _showToolPickerModal(
    BuildContext context,
    RxList<String> currentTools,
    AiTeamController controller,
  ) {
    showModalBottomSheet(
      context: context,
      backgroundColor: AppTheme.surfaceDarkElevated,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      builder: (ctx) {
        return Container(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Row(
                children: [
                  const Icon(Icons.bolt_rounded,
                      color: AppTheme.primary, size: 20),
                  const SizedBox(width: 8),
                  const Text(
                    'Cấp phép Công cụ (Tool Permissions)',
                    style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                        color: AppTheme.textDark),
                  ),
                  const Spacer(),
                  IconButton(
                    icon: const Icon(Icons.close,
                        size: 20, color: AppTheme.textMutedDark),
                    onPressed: () => Navigator.of(ctx).pop(),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              const Text(
                'Tích chọn các công cụ hệ thống hoặc Webhook mà Agent này được phép gọi khi thực thi nhiệm vụ:',
                style:
                    TextStyle(fontSize: 12.5, color: AppTheme.textMutedDark),
              ),
              const SizedBox(height: 16),
              Flexible(
                child: Obx(() {
                  final allTools = controller.availableTools;
                  if (allTools.isEmpty) {
                    final defaultKeys = [
                      'strategy.read_canvas',
                      'okr.read_overview',
                      'finance.read_summary',
                      'project.read_portfolio',
                      'tasks.list',
                      'tasks.create',
                      'marketing.campaign_list',
                      'sales.lead_list',
                      'google.search',
                      'database.query',
                      'code.analyze',
                      'knowledge.search',
                    ];
                    return Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: defaultKeys.map((key) {
                        final isSelected = currentTools.contains(key);
                        return FilterChip(
                          label: Text(key,
                              style: const TextStyle(
                                  fontSize: 12, fontFamily: 'monospace')),
                          selected: isSelected,
                          selectedColor:
                              AppTheme.primary.withValues(alpha: 0.2),
                          checkmarkColor: AppTheme.primary,
                          onSelected: (selected) {
                            if (selected) {
                              if (!currentTools.contains(key)) {
                                currentTools.add(key);
                              }
                            } else {
                              currentTools.remove(key);
                            }
                          },
                        );
                      }).toList(),
                    );
                  }

                  return ListView.builder(
                    shrinkWrap: true,
                    itemCount: allTools.length,
                    itemBuilder: (context, idx) {
                      final t = allTools[idx];
                      final key = (t['key'] ?? '').toString();
                      final name = t['name'] ?? key;
                      final desc = t['description'] ?? '';
                      final isSelected = currentTools.contains(key);

                      return CheckboxListTile(
                        value: isSelected,
                        activeColor: AppTheme.primary,
                        checkColor: Colors.black,
                        title: Text(name,
                            style: const TextStyle(
                                fontSize: 13.5,
                                fontWeight: FontWeight.w600,
                                color: AppTheme.textDark)),
                        subtitle: Text('$key · $desc',
                            style: const TextStyle(
                                fontSize: 11.5,
                                color: AppTheme.textMutedDark)),
                        onChanged: (bool? val) {
                          if (val == true) {
                            if (!currentTools.contains(key)) {
                              currentTools.add(key);
                            }
                          } else {
                            currentTools.remove(key);
                          }
                        },
                      );
                    },
                  );
                }),
              ),
              const SizedBox(height: 16),
              Align(
                alignment: Alignment.centerRight,
                child: ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.primary,
                    foregroundColor: Colors.black,
                  ),
                  onPressed: () => Navigator.of(ctx).pop(),
                  child: const Text('Xác nhận cấp quyền'),
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  static Widget _buildProfileOption({
    required String title,
    required String subtitle,
    required bool selected,
    required VoidCallback onTap,
  }) {
    return Expanded(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(10),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          decoration: BoxDecoration(
            color: selected
                ? AppTheme.primary.withValues(alpha: 0.15)
                : AppTheme.surfaceDarkLighter,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(
              color: selected ? AppTheme.primary : AppTheme.borderDark,
              width: selected ? 1.5 : 1.0,
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: TextStyle(
                  fontSize: 12.5,
                  fontWeight: FontWeight.bold,
                  color: selected ? AppTheme.primary : AppTheme.textDark,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                subtitle,
                style: const TextStyle(
                    fontSize: 10.5, color: AppTheme.textMutedDark),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
