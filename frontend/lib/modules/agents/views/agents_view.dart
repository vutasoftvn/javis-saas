import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/agents_controller.dart';
import 'widgets/agent_activity_timeline_widget.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/theme/glassmorphism.dart';
import '../../../core/widgets/floating_app_bar.dart';

class AgentsView extends GetView<AgentsController> {
  const AgentsView({super.key});

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<AgentsController>()) {
      Get.put(AgentsController());
    }

    return Container(
      color: Colors.transparent,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          JavisFloatingAppBar(
            title: 'Quản lý Agents AI',
            subtitle: 'Thiết lập các vai trò chuyên môn và prompt tự động',
            actions: [
              Container(
                decoration: const BoxDecoration(
                  color: AppTheme.primary,
                  shape: BoxShape.circle,
                ),
                child: IconButton(
                  tooltip: 'Thêm Agent',
                  icon: const Icon(Icons.add, color: Colors.white, size: 20),
                  onPressed: () => _showAddAgentDialog(context),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),

          // Content
          Expanded(
            child: Obx(() {
              if (controller.isLoading.value) {
                return const Center(child: CircularProgressIndicator());
              }

              return SingleChildScrollView(
                padding: const EdgeInsets.all(24),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    if (controller.agents.isEmpty)
                      Center(
                        child: Padding(
                          padding: const EdgeInsets.symmetric(vertical: 40),
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Icon(
                                Icons.smart_toy_outlined,
                                size: 64,
                                color: AppTheme.textMutedDark.withValues(alpha: 0.5),
                              ),
                              const SizedBox(height: 16),
                              const Text(
                                'Chưa có Agent nào',
                                style: TextStyle(
                                  color: AppTheme.textMutedDark,
                                  fontSize: 16,
                                ),
                              ),
                            ],
                          ),
                        ),
                      )
                    else
                      GridView.builder(
                        shrinkWrap: true,
                        physics: const NeverScrollableScrollPhysics(),
                        gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                          maxCrossAxisExtent: 400,
                          mainAxisExtent: 220,
                          crossAxisSpacing: 24,
                          mainAxisSpacing: 24,
                        ),
                        itemCount: controller.agents.length,
                        itemBuilder: (context, index) {
                          final agent = controller.agents[index];
                          return _buildAgentCard(context, agent);
                        },
                      ),
                    const SizedBox(height: 32),
                    AgentActivityTimelineWidget(
                      events: controller.activityEvents,
                      onRefresh: controller.loadActivity,
                    ),
                  ],
                ),
              );
            }),
          ),
        ],
      ),
    );
  }

  Widget _buildAgentCard(BuildContext context, Map<String, dynamic> agent) {
    return Glassmorphism(
      blur: 20,
      opacity: 0.15,
      color: AppTheme.surfaceDark,
      borderRadius: BorderRadius.circular(16),
      child: Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.white.withValues(alpha: 0.05)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: AppTheme.primary.withValues(alpha: 0.2),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: const Icon(
                        Icons.smart_toy,
                        color: AppTheme.primaryLight,
                        size: 24,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          agent['name'] ?? 'Không tên',
                          style: const TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                            color: AppTheme.textDark,
                          ),
                        ),
                        Text(
                          '@${agent['slug']}',
                          style: const TextStyle(
                            fontSize: 12,
                            color: AppTheme.primaryLight,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
                PopupMenuButton<String>(
                  icon: const Icon(
                    Icons.more_vert,
                    color: AppTheme.textMutedDark,
                  ),
                  color: AppTheme.surfaceDark,
                  onSelected: (value) {
                    if (value == 'delete') {
                      _confirmDelete(context, agent['id']);
                    } else if (value == 'edit') {
                      _showEditAgentDialog(context, agent);
                    }
                  },
                  itemBuilder: (context) => [
                    const PopupMenuItem(
                      value: 'edit',
                      child: Text(
                        'Chỉnh sửa',
                        style: TextStyle(color: AppTheme.textDark),
                      ),
                    ),
                    const PopupMenuItem(
                      value: 'delete',
                      child: Text(
                        'Xóa',
                        style: TextStyle(color: AppTheme.error),
                      ),
                    ),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 16),
            Expanded(
              child: Text(
                agent['description'] ?? 'Không có mô tả',
                style: const TextStyle(
                  color: AppTheme.textMutedDark,
                  fontSize: 14,
                ),
                maxLines: 3,
                overflow: TextOverflow.ellipsis,
              ),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                if (agent['provider'] != null)
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 8,
                      vertical: 4,
                    ),
                    decoration: BoxDecoration(
                      color: AppTheme.backgroundDark,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      '${agent['provider']} / ${agent['model']}',
                      style: const TextStyle(
                        fontSize: 10,
                        color: AppTheme.textMutedDark,
                      ),
                    ),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  void _showEditAgentDialog(BuildContext context, Map<String, dynamic> agent) {
    final nameController = TextEditingController(
      text: '${agent['name'] ?? ''}',
    );
    final slugController = TextEditingController(
      text: '${agent['slug'] ?? ''}',
    );
    final descController = TextEditingController(
      text: '${agent['description'] ?? ''}',
    );
    final promptController = TextEditingController(
      text: '${agent['system_prompt'] ?? ''}',
    );
    final providerController = TextEditingController(
      text: '${agent['provider'] ?? ''}',
    );
    final modelController = TextEditingController(
      text: '${agent['model'] ?? ''}',
    );

    Get.dialog(
      AlertDialog(
        backgroundColor: AppTheme.surfaceDark,
        title: const Text('Chỉnh sửa Agent'),
        content: SizedBox(
          width: 400,
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                  controller: nameController,
                  decoration: const InputDecoration(labelText: 'Tên Agent'),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: slugController,
                  decoration: const InputDecoration(
                    labelText: 'Slug (viết liền không dấu)',
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: descController,
                  decoration: const InputDecoration(labelText: 'Mô tả'),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: promptController,
                  decoration: const InputDecoration(labelText: 'System Prompt'),
                  maxLines: 3,
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: providerController,
                        decoration: const InputDecoration(
                          labelText: 'Provider',
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: TextField(
                        controller: modelController,
                        decoration: const InputDecoration(labelText: 'Model'),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
        actions: [
          TextButton(
            onPressed: Get.back,
            child: const Text(
              'Hủy',
              style: TextStyle(color: AppTheme.textMutedDark),
            ),
          ),
          ElevatedButton(
            onPressed: () {
              if (nameController.text.trim().isEmpty ||
                  slugController.text.trim().isEmpty) {
                Get.snackbar('Lỗi', 'Vui lòng nhập tên và slug');
                return;
              }
              controller.updateAgent('${agent['id']}', {
                'name': nameController.text.trim(),
                'slug': slugController.text.trim(),
                'description': descController.text.trim(),
                'system_prompt': promptController.text.trim(),
                'provider': providerController.text.trim(),
                'model': modelController.text.trim(),
              });
              Get.back();
            },
            child: const Text('Lưu thay đổi'),
          ),
        ],
      ),
    );
  }

  void _showAddAgentDialog(BuildContext context) {
    final nameController = TextEditingController();
    final slugController = TextEditingController();
    final descController = TextEditingController();
    final promptController = TextEditingController();
    final providerController = TextEditingController(text: 'openai');
    final modelController = TextEditingController(text: 'gpt-4o');

    Get.dialog(
      AlertDialog(
        backgroundColor: AppTheme.surfaceDark,
        title: const Text('Thêm Agent mới'),
        content: SizedBox(
          width: 400,
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                  controller: nameController,
                  decoration: const InputDecoration(
                    labelText: 'Tên Agent',
                    hintText: 'VD: Lập trình viên AI',
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: slugController,
                  decoration: const InputDecoration(
                    labelText: 'Slug (viết liền không dấu)',
                    hintText: 'coder-agent',
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: descController,
                  decoration: const InputDecoration(labelText: 'Mô tả'),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: promptController,
                  decoration: const InputDecoration(labelText: 'System Prompt'),
                  maxLines: 3,
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: providerController,
                        decoration: const InputDecoration(
                          labelText: 'Provider (VD: openai)',
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: TextField(
                        controller: modelController,
                        decoration: const InputDecoration(
                          labelText: 'Model (VD: gpt-4o)',
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Get.back(),
            child: const Text(
              'Hủy',
              style: TextStyle(color: AppTheme.textMutedDark),
            ),
          ),
          ElevatedButton(
            onPressed: () {
              if (nameController.text.isEmpty || slugController.text.isEmpty) {
                Get.snackbar('Lỗi', 'Vui lòng nhập tên và slug');
                return;
              }
              controller.createAgent({
                'name': nameController.text,
                'slug': slugController.text,
                'description': descController.text.isNotEmpty
                    ? descController.text
                    : null,
                'system_prompt': promptController.text.isNotEmpty
                    ? promptController.text
                    : null,
                'provider': providerController.text.isNotEmpty
                    ? providerController.text
                    : null,
                'model': modelController.text.isNotEmpty
                    ? modelController.text
                    : null,
              });
              Get.back();
            },
            child: const Text('Tạo mới'),
          ),
        ],
      ),
    );
  }

  void _confirmDelete(BuildContext context, String agentId) {
    Get.dialog(
      AlertDialog(
        backgroundColor: AppTheme.surfaceDark,
        title: const Text('Xác nhận xóa'),
        content: const Text('Bạn có chắc chắn muốn xóa Agent này?'),
        actions: [
          TextButton(
            onPressed: () => Get.back(),
            child: const Text(
              'Hủy',
              style: TextStyle(color: AppTheme.textMutedDark),
            ),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: AppTheme.error),
            onPressed: () {
              controller.deleteAgent(agentId);
              Get.back();
            },
            child: const Text('Xóa'),
          ),
        ],
      ),
    );
  }
}
