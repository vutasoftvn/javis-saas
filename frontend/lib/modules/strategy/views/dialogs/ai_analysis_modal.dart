import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/widgets/app_modal_dialog.dart';
import '../../controllers/strategy_controller.dart';

class AiAnalysisModal {
  static void show(BuildContext context, StrategyController controller, {String? initialProjectId}) {
    String? selectedProjId = initialProjectId;
    final focusController = TextEditingController();
    bool clearExisting = true;
    int pestelCount = 3;
    int swotCount = 3;
    int towsCount = 2;

    AppModalDialog.show(
      context: context,
      title: 'Phân tích Chiến lược Tự động AI',
      subtitle: 'Kết hợp Tầm nhìn, Sứ mệnh, Giá trị cốt lõi và Dự án để sinh PESTEL, SWOT & TOWS theo cấu hình tùy chọn.',
      icon: Icons.auto_awesome_rounded,
      maxWidth: 680,
      content: StatefulBuilder(
        builder: (context, setState) {
          final vision = controller.foundationVision.value.isNotEmpty
              ? controller.foundationVision.value
              : 'Trở thành nền tảng số hóa quản trị và tự động hóa AI hàng đầu';
          final mission = controller.foundationMission.value.isNotEmpty
              ? controller.foundationMission.value
              : 'Hỗ trợ doanh nghiệp tối ưu năng suất và vận hành thông minh';
          final coreValues = controller.foundationCoreValues;

          return SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: const Color(0xFF1E1B4B).withValues(alpha: 0.5),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: const Color(0xFF4F46E5).withValues(alpha: 0.3)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Row(
                        children: [
                          Icon(Icons.hub_rounded, size: 16, color: Color(0xFF818CF8)),
                          SizedBox(width: 8),
                          Text(
                            'Nền tảng Chiến lược từ Foundation:',
                            style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Color(0xFF818CF8)),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Text('• Tầm nhìn: $vision', style: const TextStyle(fontSize: 12, color: Colors.white70)),
                      const SizedBox(height: 4),
                      Text('• Sứ mệnh: $mission', style: const TextStyle(fontSize: 12, color: Colors.white70)),
                      if (coreValues.isNotEmpty) ...[
                        const SizedBox(height: 4),
                        Text(
                          '• Giá trị cốt lõi: ${coreValues.map((v) => v['title'] ?? '').where((t) => t.isNotEmpty).join(' | ')}',
                          style: const TextStyle(fontSize: 12, color: Colors.white70),
                        ),
                      ],
                    ],
                  ),
                ),
                const SizedBox(height: 20),
                const Text(
                  'Chọn Dự án Chiến lược (Strategic Project):',
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.white),
                ),
                const SizedBox(height: 8),
                DropdownButtonFormField<String?>(
                  initialValue: selectedProjId,
                  dropdownColor: AppTheme.surfaceDark,
                  decoration: const InputDecoration(
                    labelText: 'Dự án áp dụng',
                    hintText: 'Chọn dự án cần phân tích chuyên sâu',
                    prefixIcon: Icon(Icons.rocket_launch_outlined, size: 18),
                  ),
                  items: [
                    const DropdownMenuItem<String?>(
                      value: null,
                      child: Text('🌐 Toàn bộ doanh nghiệp / Tổng thể (Enterprise-wide)'),
                    ),
                    ...controller.projects.map(
                      (p) => DropdownMenuItem<String?>(
                        value: p['id'].toString(),
                        child: Text('🚀 ${p['title']} (${p['phase'] ?? 'Khởi động'})'),
                      ),
                    ),
                  ],
                  onChanged: (v) => setState(() => selectedProjId = v),
                ),
                const SizedBox(height: 16),
                const Text(
                  'Cấu hình số lượng mục phân tích sinh ra:',
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.white),
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Expanded(
                      child: DropdownButtonFormField<int>(
                        initialValue: pestelCount,
                        isExpanded: true,
                        dropdownColor: AppTheme.surfaceDark,
                        decoration: const InputDecoration(
                          labelText: 'PESTEL',
                          contentPadding: EdgeInsets.symmetric(horizontal: 8, vertical: 8),
                        ),
                        items: const [
                          DropdownMenuItem(value: 1, child: Text('1 (Nhanh)', style: TextStyle(fontSize: 11))),
                          DropdownMenuItem(value: 2, child: Text('2 (Vừa)', style: TextStyle(fontSize: 11))),
                          DropdownMenuItem(value: 3, child: Text('3 (Chi tiết)', style: TextStyle(fontSize: 11))),
                        ],
                        onChanged: (v) {
                          if (v != null) setState(() => pestelCount = v);
                        },
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: DropdownButtonFormField<int>(
                        initialValue: swotCount,
                        isExpanded: true,
                        dropdownColor: AppTheme.surfaceDark,
                        decoration: const InputDecoration(
                          labelText: 'SWOT',
                          contentPadding: EdgeInsets.symmetric(horizontal: 8, vertical: 8),
                        ),
                        items: const [
                          DropdownMenuItem(value: 1, child: Text('1 (Nhanh)', style: TextStyle(fontSize: 11))),
                          DropdownMenuItem(value: 2, child: Text('2 (Vừa)', style: TextStyle(fontSize: 11))),
                          DropdownMenuItem(value: 3, child: Text('3 (Chi tiết)', style: TextStyle(fontSize: 11))),
                        ],
                        onChanged: (v) {
                          if (v != null) setState(() => swotCount = v);
                        },
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: DropdownButtonFormField<int>(
                        initialValue: towsCount,
                        isExpanded: true,
                        dropdownColor: AppTheme.surfaceDark,
                        decoration: const InputDecoration(
                          labelText: 'TOWS',
                          contentPadding: EdgeInsets.symmetric(horizontal: 8, vertical: 8),
                        ),
                        items: const [
                          DropdownMenuItem(value: 1, child: Text('1 (Nhanh)', style: TextStyle(fontSize: 11))),
                          DropdownMenuItem(value: 2, child: Text('2 (Vừa)', style: TextStyle(fontSize: 11))),
                          DropdownMenuItem(value: 3, child: Text('3 (Chi tiết)', style: TextStyle(fontSize: 11))),
                        ],
                        onChanged: (v) {
                          if (v != null) setState(() => towsCount = v);
                        },
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                TextField(
                  controller: focusController,
                  maxLines: 2,
                  decoration: const InputDecoration(
                    labelText: 'Định hướng & Trọng tâm Bổ sung (Tùy chọn)',
                    hintText: 'Ví dụ: Đánh giá cơ hội thị trường SaaS B2B, mở rộng tệp khách hàng khối sản xuất...',
                    prefixIcon: Icon(Icons.lightbulb_outline_rounded, size: 18),
                    alignLabelWithHint: true,
                  ),
                ),
                const SizedBox(height: 16),
                Material(
                  color: Colors.transparent,
                  child: SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    title: const Text('Ghi đè (thay thế) các phân tích hiện tại', style: TextStyle(fontSize: 13, color: Colors.white)),
                    subtitle: const Text('Xóa dữ liệu cũ để tránh trùng lặp thẻ phân tích', style: TextStyle(fontSize: 11, color: AppTheme.textMutedDark)),
                    value: clearExisting,
                    activeThumbColor: AppTheme.primary,
                    activeTrackColor: AppTheme.primary.withValues(alpha: 0.5),
                    onChanged: (val) => setState(() => clearExisting = val),
                  ),
                ),
              ],
            ),
          );
        },
      ),
      actions: [
        TextButton.icon(
          onPressed: () {
            Get.back();
            showPromptConfigModal(context, controller);
          },
          icon: const Icon(Icons.tune_rounded, size: 16, color: AppTheme.primary),
          label: const Text('Tùy chỉnh Prompt', style: TextStyle(color: AppTheme.primary)),
        ),
        const Spacer(),
        TextButton(
          onPressed: () => Get.back(),
          child: const Text('Huỷ', style: TextStyle(color: Colors.white60)),
        ),
        const SizedBox(width: 12),
        ElevatedButton.icon(
          onPressed: () {
            final focus = focusController.text.trim();
            Get.back();
            controller.generateAiAnalysis(
              projectId: selectedProjId,
              focusArea: focus.isNotEmpty ? focus : null,
              clearExisting: clearExisting,
              pestelItemsPerFactor: pestelCount,
              swotItemsPerCategory: swotCount,
              towsItemsPerQuadrant: towsCount,
            );
          },
          icon: const Icon(Icons.auto_awesome_rounded, size: 16),
          label: const Text('Bắt đầu Phân tích AI'),
          style: ElevatedButton.styleFrom(
            backgroundColor: AppTheme.primary,
            foregroundColor: const Color(0xFF04070E),
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
          ),
        ),
      ],
    );
  }

  static void showPromptConfigModal(BuildContext context, StrategyController controller) async {
    final promptData = await controller.getPromptTemplate();
    final templateText = promptData['template_content']?.toString() ?? '';
    final promptController = TextEditingController(text: templateText);
    bool isCustomized = promptData['is_customized'] == true;

    if (!context.mounted) return;

    AppModalDialog.show(
      context: context,
      title: 'Cấu hình System Prompt AI',
      subtitle: 'Prompt mẫu đã được tự động lưu và đồng bộ cho Workspace hiện tại.',
      icon: Icons.tune_rounded,
      maxWidth: 720,
      content: StatefulBuilder(
        builder: (context, setState) {
          return SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AppTheme.primary.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.info_outline_rounded, size: 16, color: AppTheme.primary),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          isCustomized
                              ? 'Prompt này đã được tùy chỉnh cho Workspace.'
                              : 'Đang dùng Prompt chuẩn của hệ thống.',
                          style: const TextStyle(fontSize: 12, color: Colors.white70),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: promptController,
                  maxLines: 12,
                  style: const TextStyle(fontSize: 12, fontFamily: 'monospace', color: Colors.white),
                  decoration: const InputDecoration(
                    labelText: 'Nội dung Prompt Mẫu',
                    border: OutlineInputBorder(),
                  ),
                ),
              ],
            ),
          );
        },
      ),
      actions: [
        if (isCustomized)
          TextButton(
            onPressed: () async {
              await controller.resetPromptTemplate();
              Get.back();
            },
            child: const Text('Khôi phục Mặc định', style: TextStyle(color: Colors.orangeAccent)),
          ),
        const Spacer(),
        TextButton(
          onPressed: () => Get.back(),
          child: const Text('Hủy', style: TextStyle(color: Colors.white60)),
        ),
        ElevatedButton(
          onPressed: () async {
            final content = promptController.text.trim();
            if (content.isNotEmpty) {
              await controller.updatePromptTemplate(templateContent: content);
            }
            Get.back();
          },
          child: const Text('Lưu Prompt'),
        ),
      ],
    );
  }
}
