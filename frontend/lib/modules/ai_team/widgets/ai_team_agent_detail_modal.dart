import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:get/get.dart';
import '../../../../core/theme/app_theme.dart';
import '../controllers/ai_team_controller.dart';
import 'ai_team_helpers.dart';

class AiTeamAgentDetailModal {
  static void show(
    BuildContext context,
    Map<String, dynamic> agent,
    AiTeamController controller,
  ) {
    final agentKey = (agent['key'] ?? '').toString();
    final name = agent['name'] ?? agentKey;
    final role = agent['role_title'] ?? agent['role'] ?? 'Specialist';
    final dept = agent['department'] ?? 'general';
    final promptKey = AiTeamHelpers.getAgentPromptKey(agent);
    final initialPrompt = agent['system_prompt']?.toString() ??
        AiTeamHelpers.getAgentDefaultPromptContent(promptKey, name, role);
    final promptController = TextEditingController(text: initialPrompt);
    final promptTextObs = RxString(initialPrompt);
    final isEditingPrompt = RxBool(false);
    final selectedProfile = RxString(
        (agent['default_model_profile'] ?? agent['model_name'] ?? 'reasoning')
            .toString());
    final currentTools =
        RxList<String>(AiTeamHelpers.getAgentToolsList(agent));

    showGeneralDialog(
      context: context,
      barrierDismissible: true,
      barrierLabel: 'AgentSidebar',
      barrierColor: Colors.black.withValues(alpha: 0.55),
      transitionDuration: const Duration(milliseconds: 240),
      pageBuilder: (ctx, anim1, anim2) {
        final screenWidth = MediaQuery.of(ctx).size.width;
        final sidebarWidth = screenWidth > 600 ? 520.0 : screenWidth * 0.95;

        return Align(
          alignment: Alignment.centerRight,
          child: Material(
            color: Colors.transparent,
            child: Container(
              width: sidebarWidth,
              height: double.infinity,
              decoration: BoxDecoration(
                color: AppTheme.surfaceDark,
                border: const Border(
                  left: BorderSide(color: AppTheme.borderDark, width: 1.5),
                ),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: 0.6),
                    blurRadius: 30,
                    offset: const Offset(-8, 0),
                  ),
                ],
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // 1. Sidebar Header
                  Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 18, vertical: 16),
                    decoration: const BoxDecoration(
                      border:
                          Border(bottom: BorderSide(color: AppTheme.borderDark)),
                    ),
                    child: Row(
                      children: [
                        Container(
                          width: 40,
                          height: 40,
                          decoration: BoxDecoration(
                            color: AppTheme.primary.withValues(alpha: 0.15),
                            borderRadius: BorderRadius.circular(10),
                            border: Border.all(
                                color: AppTheme.primary.withValues(alpha: 0.3)),
                          ),
                          child: Center(
                            child: Icon(
                                AiTeamHelpers.getDepartmentIcon(dept),
                                color: AppTheme.primary,
                                size: 20),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                children: [
                                  Expanded(
                                    child: Text(
                                      name,
                                      style: const TextStyle(
                                        fontSize: 15.5,
                                        fontWeight: FontWeight.bold,
                                        color: AppTheme.textDark,
                                      ),
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                  ),
                                  const SizedBox(width: 8),
                                  Container(
                                    padding: const EdgeInsets.symmetric(
                                        horizontal: 7, vertical: 2),
                                    decoration: BoxDecoration(
                                      color: AppTheme.primary
                                          .withValues(alpha: 0.15),
                                      borderRadius: BorderRadius.circular(6),
                                      border: Border.all(
                                          color: AppTheme.primary
                                              .withValues(alpha: 0.3)),
                                    ),
                                    child: Text(
                                      AiTeamHelpers.translateDepartment(dept),
                                      style: const TextStyle(
                                        fontSize: 10.5,
                                        fontWeight: FontWeight.bold,
                                        color: AppTheme.primary,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 2),
                              Text(
                                role,
                                style: const TextStyle(
                                    fontSize: 12,
                                    color: AppTheme.textMutedDark),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(width: 6),
                        IconButton(
                          icon: const Icon(Icons.close,
                              color: AppTheme.textMutedDark, size: 20),
                          onPressed: () => Navigator.of(ctx).pop(),
                          tooltip: 'Đóng',
                        ),
                      ],
                    ),
                  ),

                  // 2. Sidebar Body
                  Expanded(
                    child: SingleChildScrollView(
                      physics: const ClampingScrollPhysics(),
                      padding: const EdgeInsets.all(18),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          // Section: System Prompt
                          Row(
                            children: [
                              const Icon(Icons.terminal_rounded,
                                  size: 17, color: Color(0xFF818CF8)),
                              const SizedBox(width: 8),
                              const Text(
                                'System Prompt & Chỉ đạo',
                                style: TextStyle(
                                  fontSize: 13.5,
                                  fontWeight: FontWeight.bold,
                                  color: AppTheme.textDark,
                                ),
                              ),
                              const Spacer(),
                              Obx(() => InkWell(
                                    onTap: () {
                                      if (isEditingPrompt.value) {
                                        promptTextObs.value =
                                            promptController.text;
                                      }
                                      isEditingPrompt.value =
                                          !isEditingPrompt.value;
                                    },
                                    borderRadius: BorderRadius.circular(6),
                                    child: Container(
                                      padding: const EdgeInsets.symmetric(
                                          horizontal: 7, vertical: 3),
                                      decoration: BoxDecoration(
                                        color: isEditingPrompt.value
                                            ? AppTheme.primary
                                                .withValues(alpha: 0.15)
                                            : AppTheme.surfaceDarkElevated,
                                        borderRadius: BorderRadius.circular(6),
                                        border: Border.all(
                                          color: isEditingPrompt.value
                                              ? AppTheme.primary
                                              : AppTheme.borderDark,
                                        ),
                                      ),
                                      child: Row(
                                        mainAxisSize: MainAxisSize.min,
                                        children: [
                                          Icon(
                                            isEditingPrompt.value
                                                ? Icons.visibility_rounded
                                                : Icons.edit_rounded,
                                            size: 12,
                                            color: isEditingPrompt.value
                                                ? AppTheme.primary
                                                : AppTheme.textMutedDark,
                                          ),
                                          const SizedBox(width: 4),
                                          Text(
                                            isEditingPrompt.value
                                                ? 'Xem định dạng'
                                                : 'Chỉnh sửa',
                                            style: TextStyle(
                                              fontSize: 11,
                                              fontWeight: FontWeight.bold,
                                              color: isEditingPrompt.value
                                                  ? AppTheme.primary
                                                  : AppTheme.textMutedDark,
                                            ),
                                          ),
                                        ],
                                      ),
                                    ),
                                  )),
                              const SizedBox(width: 6),
                              Container(
                                padding: const EdgeInsets.symmetric(
                                    horizontal: 7, vertical: 3),
                                decoration: BoxDecoration(
                                  color: const Color(0xFF818CF8)
                                      .withValues(alpha: 0.12),
                                  borderRadius: BorderRadius.circular(6),
                                  border: Border.all(
                                      color: const Color(0xFF818CF8)
                                          .withValues(alpha: 0.3)),
                                ),
                                child: Text(
                                  promptKey,
                                  style: const TextStyle(
                                    fontSize: 10.5,
                                    fontWeight: FontWeight.bold,
                                    color: Color(0xFFA5B4FC),
                                    fontFamily: 'monospace',
                                  ),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 8),

                          // Prompt Content
                          Obx(() {
                            if (isEditingPrompt.value) {
                              return Container(
                                decoration: BoxDecoration(
                                  color: AppTheme.surfaceDarkLighter,
                                  borderRadius: BorderRadius.circular(10),
                                  border: Border.all(
                                      color: AppTheme.primary
                                          .withValues(alpha: 0.5)),
                                ),
                                child: TextField(
                                  controller: promptController,
                                  maxLines: null,
                                  minLines: 6,
                                  onChanged: (val) =>
                                      promptTextObs.value = val,
                                  style: const TextStyle(
                                    fontSize: 12.5,
                                    fontFamily: 'monospace',
                                    color: AppTheme.textDark,
                                    height: 1.4,
                                  ),
                                  decoration: const InputDecoration(
                                    contentPadding: EdgeInsets.all(12),
                                    border: InputBorder.none,
                                    hintText:
                                        'Nhập nội dung System Prompt định dạng Markdown...',
                                    hintStyle:
                                        TextStyle(color: AppTheme.textDimDark),
                                  ),
                                ),
                              );
                            }

                            return Container(
                              width: double.infinity,
                              padding: const EdgeInsets.all(12),
                              decoration: BoxDecoration(
                                color: AppTheme.surfaceDarkLighter,
                                borderRadius: BorderRadius.circular(10),
                                border: Border.all(color: AppTheme.borderDark),
                              ),
                              child: MarkdownBody(
                                data: promptTextObs.value,
                                selectable: true,
                                styleSheet: MarkdownStyleSheet(
                                  p: const TextStyle(
                                      fontSize: 12.5,
                                      color: AppTheme.textDark,
                                      height: 1.45),
                                  h1: const TextStyle(
                                      fontSize: 13.5,
                                      fontWeight: FontWeight.bold,
                                      color: AppTheme.primary,
                                      height: 1.3),
                                  h2: const TextStyle(
                                      fontSize: 13,
                                      fontWeight: FontWeight.bold,
                                      color: Color(0xFFA5B4FC),
                                      height: 1.3),
                                  h3: const TextStyle(
                                      fontSize: 12.5,
                                      fontWeight: FontWeight.bold,
                                      color: AppTheme.textDark),
                                  listBullet: const TextStyle(
                                      color: AppTheme.primary, fontSize: 12.5),
                                  strong: const TextStyle(
                                      fontWeight: FontWeight.bold,
                                      color: Colors.white),
                                  code: TextStyle(
                                    color: const Color(0xFF38BDF8),
                                    backgroundColor:
                                        AppTheme.surfaceDarkElevated,
                                    fontFamily: 'monospace',
                                    fontSize: 11.5,
                                  ),
                                  blockquote: const TextStyle(
                                      color: AppTheme.textMutedDark,
                                      fontStyle: FontStyle.italic),
                                  blockquoteDecoration: BoxDecoration(
                                    color: AppTheme.surfaceDarkElevated,
                                    borderRadius: BorderRadius.circular(6),
                                    border: const Border(
                                        left: BorderSide(
                                            color: AppTheme.primary,
                                            width: 3)),
                                  ),
                                ),
                              ),
                            );
                          }),
                          const SizedBox(height: 16),

                          // Section: Tools & Skills
                          Row(
                            children: [
                              const Icon(Icons.bolt_rounded,
                                  size: 17, color: AppTheme.primary),
                              const SizedBox(width: 8),
                              const Text(
                                'Kỹ năng & Tool Gateway được cấp phép',
                                style: TextStyle(
                                  fontSize: 13.5,
                                  fontWeight: FontWeight.bold,
                                  color: AppTheme.textDark,
                                ),
                              ),
                              const Spacer(),
                              InkWell(
                                onTap: () => _showToolPickerModal(
                                    context, currentTools, controller),
                                borderRadius: BorderRadius.circular(6),
                                child: Container(
                                  padding: const EdgeInsets.symmetric(
                                      horizontal: 8, vertical: 4),
                                  decoration: BoxDecoration(
                                    color: AppTheme.primary
                                        .withValues(alpha: 0.15),
                                    borderRadius: BorderRadius.circular(6),
                                    border: Border.all(
                                        color: AppTheme.primary
                                            .withValues(alpha: 0.4)),
                                  ),
                                  child: const Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Icon(Icons.add_rounded,
                                          size: 13, color: AppTheme.primary),
                                      SizedBox(width: 4),
                                      Text(
                                        'Quản lý Tools',
                                        style: TextStyle(
                                          fontSize: 11,
                                          fontWeight: FontWeight.bold,
                                          color: AppTheme.primary,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 8),
                          Obx(() => Wrap(
                                spacing: 6,
                                runSpacing: 6,
                                children: currentTools.map((tool) {
                                  return Container(
                                    padding: const EdgeInsets.symmetric(
                                        horizontal: 8, vertical: 5),
                                    decoration: BoxDecoration(
                                      color: AppTheme.surfaceDarkElevated,
                                      borderRadius: BorderRadius.circular(6),
                                      border:
                                          Border.all(color: AppTheme.borderDark),
                                    ),
                                    child: Row(
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        const Icon(Icons.check_circle_rounded,
                                            size: 13, color: AppTheme.success),
                                        const SizedBox(width: 5),
                                        Text(
                                          tool,
                                          style: const TextStyle(
                                            fontSize: 11.5,
                                            fontFamily: 'monospace',
                                            color: AppTheme.textDark,
                                          ),
                                        ),
                                        const SizedBox(width: 4),
                                        InkWell(
                                          onTap: () =>
                                              currentTools.remove(tool),
                                          child: const Icon(Icons.close,
                                              size: 12,
                                              color: AppTheme.textMutedDark),
                                        ),
                                      ],
                                    ),
                                  );
                                }).toList(),
                              )),
                          const SizedBox(height: 16),

                          // Section: Model Profile & Risk
                          Row(
                            children: [
                              const Icon(Icons.memory_rounded,
                                  size: 17, color: Color(0xFF38BDF8)),
                              const SizedBox(width: 8),
                              const Text(
                                'Cấu hình Runtime & Mô hình AI',
                                style: TextStyle(
                                  fontSize: 13.5,
                                  fontWeight: FontWeight.bold,
                                  color: AppTheme.textDark,
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 8),
                          Obx(() => Row(
                                children: [
                                  _buildProfileOption(
                                    title: 'Tư duy sâu',
                                    subtitle: 'Gemini 2.5 Pro',
                                    selected:
                                        selectedProfile.value == 'reasoning',
                                    onTap: () =>
                                        selectedProfile.value = 'reasoning',
                                  ),
                                  const SizedBox(width: 8),
                                  _buildProfileOption(
                                    title: 'Tốc độ cao',
                                    subtitle: 'Gemini 2.5 Flash',
                                    selected: selectedProfile.value == 'fast',
                                    onTap: () => selectedProfile.value = 'fast',
                                  ),
                                  const SizedBox(width: 8),
                                  _buildProfileOption(
                                    title: 'Lập trình',
                                    subtitle: 'Claude 3.7 Sonnet',
                                    selected: selectedProfile.value == 'coding',
                                    onTap: () =>
                                        selectedProfile.value = 'coding',
                                  ),
                                ],
                              )),
                        ],
                      ),
                    ),
                  ),

                  // 3. Sidebar Footer Actions
                  Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 18, vertical: 14),
                    decoration: const BoxDecoration(
                      border:
                          Border(top: BorderSide(color: AppTheme.borderDark)),
                    ),
                    child: Row(
                      children: [
                        if (agent['is_system'] == false) ...[
                          IconButton(
                            icon: const Icon(Icons.delete_outline,
                                color: AppTheme.error, size: 20),
                            tooltip: 'Xóa Agent này',
                            onPressed: () {
                              Navigator.of(ctx).pop();
                              showDeleteAgentConfirmDialog(
                                  context, agent, controller);
                            },
                          ),
                          const SizedBox(width: 4),
                        ],
                        OutlinedButton.icon(
                          style: OutlinedButton.styleFrom(
                            foregroundColor: const Color(0xFF818CF8),
                            side: const BorderSide(color: Color(0xFF6366F1)),
                            padding: const EdgeInsets.symmetric(
                                horizontal: 12, vertical: 10),
                          ),
                          onPressed: () {
                            Navigator.of(ctx).pop();
                            showCloneAgentDialog(context, agent, controller);
                          },
                          icon: const Icon(Icons.copy_rounded, size: 15),
                          label: const Text('Nhân bản',
                              style: TextStyle(fontSize: 12)),
                        ),
                        const Spacer(),
                        OutlinedButton(
                          style: OutlinedButton.styleFrom(
                            foregroundColor: AppTheme.textMutedDark,
                            side: const BorderSide(color: AppTheme.borderDark),
                            padding: const EdgeInsets.symmetric(
                                horizontal: 16, vertical: 10),
                          ),
                          onPressed: () => Navigator.of(ctx).pop(),
                          child: const Text('Đóng'),
                        ),
                        const SizedBox(width: 10),
                        ElevatedButton.icon(
                          style: ElevatedButton.styleFrom(
                            backgroundColor: AppTheme.primary,
                            foregroundColor: Colors.black,
                            padding: const EdgeInsets.symmetric(
                                horizontal: 18, vertical: 10),
                          ),
                          onPressed: () async {
                            await controller.updateAgentDetails(
                              agentKey: agentKey,
                              promptKey: promptKey,
                              promptContent: promptController.text,
                              modelProfile: selectedProfile.value,
                              tools: currentTools,
                            );
                            if (ctx.mounted) {
                              Navigator.of(ctx).pop();
                            }
                            Get.snackbar(
                              'Đã lưu thay đổi',
                              'Cấu hình và System Prompt của $name đã được cập nhật thành công.',
                              snackPosition: SnackPosition.BOTTOM,
                              backgroundColor:
                                  const Color(0xFF10B981).withValues(alpha: 0.9),
                              colorText: Colors.white,
                              duration: const Duration(seconds: 3),
                            );
                          },
                          icon: const Icon(Icons.save_rounded, size: 16),
                          label: const Text('Lưu thay đổi',
                              style: TextStyle(fontWeight: FontWeight.bold)),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
      transitionBuilder: (ctx, anim1, anim2, child) {
        return SlideTransition(
          position: Tween<Offset>(
            begin: const Offset(1.0, 0.0),
            end: Offset.zero,
          ).animate(
            CurvedAnimation(
              parent: anim1,
              curve: Curves.easeOutCubic,
            ),
          ),
          child: child,
        );
      },
    );
  }

  static void showCloneAgentDialog(
    BuildContext context,
    Map<String, dynamic> agent,
    AiTeamController controller,
  ) {
    final nameController =
        TextEditingController(text: '${agent['name']} (Bản sao)');
    final sourceKey = (agent['key'] ?? '').toString();

    Get.defaultDialog(
      title: 'Nhân bản Nhân sự AI',
      titleStyle: const TextStyle(
          fontSize: 16, fontWeight: FontWeight.bold, color: AppTheme.textDark),
      backgroundColor: AppTheme.surfaceDarkElevated,
      contentPadding: const EdgeInsets.all(20),
      content: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Tạo một nhân sự AI mới kế thừa toàn bộ cấu hình, kỹ năng và System Prompt từ "$sourceKey":',
            style: const TextStyle(fontSize: 13, color: AppTheme.textMutedDark),
          ),
          const SizedBox(height: 14),
          TextField(
            controller: nameController,
            style: const TextStyle(color: AppTheme.textDark, fontSize: 13.5),
            decoration: InputDecoration(
              labelText: 'Tên Nhân sự mới',
              labelStyle: const TextStyle(color: AppTheme.primary),
              filled: true,
              fillColor: AppTheme.surfaceDarkLighter,
              border:
                  OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
            ),
          ),
        ],
      ),
      confirm: ElevatedButton(
        style: ElevatedButton.styleFrom(
            backgroundColor: AppTheme.primary, foregroundColor: Colors.black),
        onPressed: () async {
          final newName = nameController.text.trim();
          if (newName.isNotEmpty) {
            Get.back();
            await controller.cloneAgent(sourceKey, newName);
          }
        },
        child: const Text('Nhân bản ngay'),
      ),
      cancel: OutlinedButton(
        style: OutlinedButton.styleFrom(foregroundColor: AppTheme.textMutedDark),
        onPressed: () => Get.back(),
        child: const Text('Hủy'),
      ),
    );
  }

  static void showDeleteAgentConfirmDialog(
    BuildContext context,
    Map<String, dynamic> agent,
    AiTeamController controller,
  ) {
    final name = agent['name'] ?? agent['key'];
    final keyOrId = agent['id'] ?? agent['key'];

    Get.defaultDialog(
      title: 'Xác nhận xóa Agent',
      titleStyle: const TextStyle(
          fontSize: 16, fontWeight: FontWeight.bold, color: AppTheme.error),
      backgroundColor: AppTheme.surfaceDarkElevated,
      contentPadding: const EdgeInsets.all(20),
      content: Text(
        'Bạn có chắc chắn muốn xóa vĩnh viễn nhân sự AI "$name"? Hành động này sẽ gỡ bỏ Agent khỏi Control Plane và sơ đồ tổ chức.',
        style:
            const TextStyle(fontSize: 13, color: AppTheme.textDark, height: 1.4),
      ),
      confirm: ElevatedButton(
        style: ElevatedButton.styleFrom(
            backgroundColor: AppTheme.error, foregroundColor: Colors.white),
        onPressed: () async {
          Get.back();
          await controller.deleteCustomAgent(keyOrId, name);
        },
        child: const Text('Xác nhận xóa'),
      ),
      cancel: OutlinedButton(
        style: OutlinedButton.styleFrom(foregroundColor: AppTheme.textMutedDark),
        onPressed: () => Get.back(),
        child: const Text('Hủy'),
      ),
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
