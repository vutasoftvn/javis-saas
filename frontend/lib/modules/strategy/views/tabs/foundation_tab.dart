import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../controllers/foundation_controller.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/widgets/app_modal_dialog.dart';
import '../widgets/core_value_card.dart';
import '../widgets/revision_status_badge.dart';

class FoundationTab extends GetView<FoundationController> {
  const FoundationTab({super.key});

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<FoundationController>()) {
      Get.put(FoundationController());
    }

    return Obx(() {
      if (controller.isLoading.value) {
        return const Center(
          child: CircularProgressIndicator(color: AppTheme.primaryLight),
        );
      }

      final canvases = controller.canvases;

      return SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 28),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (controller.errorMessage.value != null) _buildErrorBanner(),
            _buildCanvasHeader(context),
            if (canvases.isNotEmpty) const SizedBox(height: 32),
            if (controller.currentRevision.value != null) ...[
              _buildFoundationSection(),
              const SizedBox(height: 36),
              _buildReviewActions(context),
            ],
            if (canvases.isEmpty)
              const SizedBox.shrink(),
          ],
        ),
      );
    });
  }

  Widget _buildErrorBanner() {
    return Container(
      margin: const EdgeInsets.only(bottom: 20),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.accent.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.accent.withValues(alpha: 0.4)),
      ),
      child: Row(
        children: [
          const Icon(Icons.error_outline_rounded, color: AppTheme.accentLight, size: 20),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              controller.errorMessage.value ?? '',
              style: const TextStyle(color: AppTheme.accentLight, fontSize: 14),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCanvasHeader(BuildContext context) {
    final canvases = controller.canvases;
    final selected = controller.selectedCanvas.value;

    if (canvases.isEmpty) {
      return const SizedBox.shrink();
    }

    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDark.withValues(alpha: 0.6),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    if (canvases.length > 1)
                      DropdownButton<String>(
                        value: selected?['id'],
                        dropdownColor: AppTheme.surfaceDark,
                        underline: const SizedBox.shrink(),
                        icon: const Icon(Icons.keyboard_arrow_down_rounded, color: Colors.white70),
                        style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: Colors.white),
                        items: canvases.map<DropdownMenuItem<String>>((c) {
                          return DropdownMenuItem<String>(
                            value: c['id'],
                            child: Text(c['name'] ?? 'Canvas'),
                          );
                        }).toList(),
                        onChanged: (id) {
                          if (id != null) controller.selectCanvas(id);
                        },
                      )
                    else
                      Text(
                        selected?['name'] ?? 'Company Strategy',
                        style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: Colors.white),
                      ),
                    const SizedBox(width: 12),
                    if (selected != null) ...[
                      IconButton(
                        onPressed: () => _showEditCanvasDialog(context, selected),
                        icon: const Icon(Icons.edit_outlined, size: 18, color: Colors.white70),
                        splashRadius: 18,
                        tooltip: 'Sửa Canvas',
                      ),
                      IconButton(
                        onPressed: () => _showDeleteCanvasDialog(context, selected),
                        icon: const Icon(Icons.delete_outline_rounded, size: 18, color: AppTheme.accentLight),
                        splashRadius: 18,
                        tooltip: 'Xóa Canvas',
                      ),
                    ],
                    const SizedBox(width: 8),
                    if (controller.currentRevision.value != null)
                      RevisionStatusBadge(status: controller.currentRevision.value!['status'])
                    else
                      const Text('Chưa có Revision', style: TextStyle(color: AppTheme.textMutedDark)),
                  ],
                ),
                if (selected?['description'] != null && (selected!['description'] as String).isNotEmpty) ...[
                  const SizedBox(height: 6),
                  Text(
                    selected['description'],
                    style: TextStyle(color: Colors.white.withValues(alpha: 0.7), fontSize: 13),
                  ),
                ],
              ],
            ),
          ),
          Wrap(
            spacing: 12,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              if (controller.currentRevision.value == null ||
                  controller.currentRevision.value!['status'] == 'approved' ||
                  controller.currentRevision.value!['status'] == 'superseded')
                ElevatedButton.icon(
                  onPressed: controller.isSaving.value ? null : controller.createNewRevision,
                  icon: const Icon(Icons.edit_note_rounded, size: 18),
                  label: const Text('Tạo Revision mới'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.primary,
                    foregroundColor: const Color(0xFF04070E),
                    padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(100)),
                  ),
                ),
              // Icon-only FAB for New Canvas
              Container(
                decoration: BoxDecoration(
                  gradient: AppTheme.primaryGradient,
                  borderRadius: BorderRadius.circular(12),
                  boxShadow: [
                    BoxShadow(
                      color: AppTheme.primary.withValues(alpha: 0.35),
                      blurRadius: 10,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                child: IconButton(
                  onPressed: () => showCreateCanvasDialog(context, controller),
                  icon: const Icon(Icons.add_rounded, color: Color(0xFF04070E), size: 22),
                  tooltip: 'Tạo Canvas mới',
                  splashRadius: 24,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  void _showEditCanvasDialog(BuildContext context, Map<String, dynamic> canvas) {
    final nameController = TextEditingController(text: canvas['name'] ?? '');
    final descController = TextEditingController(text: canvas['description'] ?? '');

    AppModalDialog.show(
      context: context,
      title: 'Chỉnh Sửa Strategy Canvas',
      subtitle: 'Cập nhật tên và mô tả định hướng hoạt động',
      icon: Icons.edit_note_rounded,
      maxWidth: 620,
      content: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Tên Strategy Canvas',
            style: TextStyle(color: AppTheme.textMutedDark, fontSize: 12, fontWeight: FontWeight.w500),
          ),
          const SizedBox(height: 6),
          TextField(
            controller: nameController,
            decoration: const InputDecoration(
              hintText: 'Nhập tên Strategy Canvas...',
              prefixIcon: Icon(Icons.label_outline_rounded, size: 20),
            ),
          ),
          const SizedBox(height: 16),
          const Text(
            'Mô tả công ty / Định hướng sản phẩm',
            style: TextStyle(color: AppTheme.textMutedDark, fontSize: 12, fontWeight: FontWeight.w500),
          ),
          const SizedBox(height: 6),
          TextField(
            controller: descController,
            maxLines: 4,
            decoration: const InputDecoration(
              hintText: 'Mô tả tổng quan về công ty...',
              prefixIcon: Padding(
                padding: EdgeInsets.only(bottom: 60),
                child: Icon(Icons.description_outlined, size: 20),
              ),
            ),
          ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Get.back(),
          child: const Text('Huỷ', style: TextStyle(color: Colors.white60)),
        ),
        const SizedBox(width: 12),
        ElevatedButton(
          onPressed: () {
            final name = nameController.text.trim();
            if (name.isEmpty) return;
            controller.updateCanvas(
              canvas['id'],
              name,
              description: descController.text.trim(),
            );
            Get.back();
          },
          style: ElevatedButton.styleFrom(
            backgroundColor: AppTheme.primary,
            foregroundColor: const Color(0xFF04070E),
          ),
          child: const Text('Lưu thay đổi'),
        ),
      ],
    );
  }

  void _showDeleteCanvasDialog(BuildContext context, Map<String, dynamic> canvas) {
    AppModalDialog.show(
      context: context,
      title: 'Xóa Strategy Canvas',
      subtitle: 'Hành động này sẽ xóa vĩnh viễn Canvas và toàn bộ Revision liên quan',
      icon: Icons.warning_amber_rounded,
      iconColor: AppTheme.accentLight,
      maxWidth: 520,
      content: Text(
        'Bạn có chắc chắn muốn xóa Strategy Canvas "${canvas['name']}" không?',
        style: const TextStyle(color: Colors.white70, fontSize: 14, height: 1.4),
      ),
      actions: [
        TextButton(
          onPressed: () => Get.back(),
          child: const Text('Huỷ', style: TextStyle(color: Colors.white60)),
        ),
        const SizedBox(width: 12),
        ElevatedButton(
          onPressed: () {
            controller.deleteCanvas(canvas['id']);
            Get.back();
          },
          style: ElevatedButton.styleFrom(backgroundColor: AppTheme.accent),
          child: const Text('Xác nhận Xóa'),
        ),
      ],
    );
  }

  static void showCreateCanvasDialog(BuildContext context, FoundationController controller) {
    final nameController = TextEditingController(text: 'Company Strategic Canvas');
    final descController = TextEditingController();

    AppModalDialog.show(
      context: context,
      title: 'Tạo Strategy Canvas',
      subtitle: 'Khởi tạo container chiến lược với tự động sinh Foundation bằng AI',
      icon: Icons.dashboard_customize_rounded,
      maxWidth: 640,
      content: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Tên Strategy Canvas',
            style: TextStyle(color: AppTheme.textMutedDark, fontSize: 12, fontWeight: FontWeight.w500),
          ),
          const SizedBox(height: 6),
          TextField(
            controller: nameController,
            decoration: const InputDecoration(
              hintText: 'Ví dụ: Kế hoạch Chiến lược 2026',
              prefixIcon: Icon(Icons.label_outline_rounded, size: 20),
            ),
          ),
          const SizedBox(height: 16),
          const Text(
            'Mô tả công ty / Định hướng sản phẩm',
            style: TextStyle(color: AppTheme.textMutedDark, fontSize: 12, fontWeight: FontWeight.w500),
          ),
          const SizedBox(height: 6),
          TextField(
            controller: descController,
            decoration: const InputDecoration(
              hintText: 'Nhập thông tin tổng quan công ty để AI tự động tạo đề xuất 1 Vision, 1 Mission và 3 Core Values...',
              prefixIcon: Padding(
                padding: EdgeInsets.only(bottom: 60),
                child: Icon(Icons.auto_awesome_rounded, color: AppTheme.primaryLight, size: 20),
              ),
            ),
            maxLines: 4,
          ),
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: AppTheme.primary.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: AppTheme.primary.withValues(alpha: 0.25)),
            ),
            child: const Row(
              children: [
                Icon(Icons.tips_and_updates_rounded, color: AppTheme.primaryLight, size: 18),
                SizedBox(width: 10),
                Expanded(
                  child: Text(
                    'AI sẽ phân tích mô tả này để tự động thiết lập Vision, Mission và 3 giá trị cốt lõi.',
                    style: TextStyle(fontSize: 12, color: Colors.white70),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Get.back(),
          child: const Text('Huỷ', style: TextStyle(color: Colors.white60)),
        ),
        const SizedBox(width: 12),
        ElevatedButton(
          onPressed: () {
            final name = nameController.text.trim();
            if (name.isEmpty) return;
            final desc = descController.text.trim();
            controller.createCanvas(
              name,
              description: desc.isNotEmpty ? desc : null,
            );
            Get.back();
          },
          style: ElevatedButton.styleFrom(
            backgroundColor: AppTheme.primary,
            foregroundColor: const Color(0xFF04070E),
          ),
          child: const Text('Tạo Canvas'),
        ),
      ],
    );
  }

  Widget _buildFoundationSection() {
    final readOnly = !controller.canEdit;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Row(
              children: [
                Icon(Icons.foundation_rounded, color: AppTheme.primaryLight, size: 22),
                SizedBox(width: 10),
                Text(
                  'Foundation: 1 Vision · 1 Mission · 3 Core Values',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white),
                ),
              ],
            ),
            if (!readOnly)
              Wrap(
                spacing: 10,
                children: [
                  ElevatedButton.icon(
                    onPressed: controller.isGeneratingAi.value ? null : controller.generateAiFoundation,
                    icon: controller.isGeneratingAi.value
                        ? const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(color: Color(0xFF04070E), strokeWidth: 2),
                          )
                        : const Icon(Icons.auto_awesome_rounded, size: 18),
                    label: Text(controller.isGeneratingAi.value ? 'Đang tạo...' : 'AI Gợi ý Foundation'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppTheme.secondary,
                      foregroundColor: const Color(0xFF04070E),
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                    ),
                  ),
                  ElevatedButton.icon(
                    onPressed: controller.isSaving.value ? null : controller.saveFoundation,
                    icon: const Icon(Icons.save_rounded, size: 18),
                    label: const Text('Lưu Foundation'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppTheme.primary,
                      foregroundColor: const Color(0xFF04070E),
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                    ),
                  ),
                ],
              ),
          ],
        ),
        const SizedBox(height: 20),
        const Row(
          children: [
            Icon(Icons.visibility_rounded, size: 16, color: AppTheme.primaryLight),
            SizedBox(width: 8),
            Text(
              'Tầm nhìn',
              style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: Colors.white),
            ),
            SizedBox(width: 6),
            Text(
              '(Vision: 20-500 ký tự)',
              style: TextStyle(fontSize: 12, color: AppTheme.textMutedDark),
            ),
          ],
        ),
        const SizedBox(height: 8),
        TextField(
          controller: controller.visionController,
          readOnly: readOnly,
          maxLength: 500,
          maxLines: 2,
          decoration: const InputDecoration(
            hintText: 'Mục tiêu tối thượng và hình ảnh công ty trong tương lai...',
          ),
        ),
        const SizedBox(height: 16),
        const Row(
          children: [
            Icon(Icons.track_changes_rounded, size: 16, color: AppTheme.primaryLight),
            SizedBox(width: 8),
            Text(
              'Sứ mệnh',
              style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: Colors.white),
            ),
            SizedBox(width: 6),
            Text(
              '(Mission: 20-500 ký tự)',
              style: TextStyle(fontSize: 12, color: AppTheme.textMutedDark),
            ),
          ],
        ),
        const SizedBox(height: 8),
        TextField(
          controller: controller.missionController,
          readOnly: readOnly,
          maxLength: 500,
          maxLines: 2,
          decoration: const InputDecoration(
            hintText: 'Lý do công ty tồn tại và giá trị đem lại cho khách hàng hàng ngày...',
          ),
        ),
        const SizedBox(height: 24),
        LayoutBuilder(
          builder: (context, constraints) {
            if (constraints.maxWidth >= 900) {
              return IntrinsicHeight(
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: List.generate(
                    3,
                    (i) => Expanded(
                      child: Padding(
                        padding: EdgeInsets.only(right: i < 2 ? 16.0 : 0.0),
                        child: CoreValueCard(
                          slotNo: i + 1,
                          titleController: controller.valueTitleControllers[i],
                          descriptionController: controller.valueDescriptionControllers[i],
                          decisionRuleController: controller.valueDecisionRuleControllers[i],
                          readOnly: readOnly,
                        ),
                      ),
                    ),
                  ),
                ),
              );
            } else {
              return Column(
                children: List.generate(
                  3,
                  (i) => Padding(
                    padding: EdgeInsets.only(bottom: i < 2 ? 16.0 : 0.0),
                    child: CoreValueCard(
                      slotNo: i + 1,
                      titleController: controller.valueTitleControllers[i],
                      descriptionController: controller.valueDescriptionControllers[i],
                      decisionRuleController: controller.valueDecisionRuleControllers[i],
                      readOnly: readOnly,
                    ),
                  ),
                ),
              );
            }
          },
        ),
      ],
    );
  }

  Widget _buildReviewActions(BuildContext context) {
    final revision = controller.currentRevision.value;
    if (revision == null) return const SizedBox.shrink();
    final status = revision['status'];

    return Wrap(
      spacing: 16,
      runSpacing: 12,
      children: [
        if (status == 'draft' || status == 'changes_requested')
          ElevatedButton.icon(
            onPressed: controller.isSaving.value ? null : controller.submitReview,
            icon: const Icon(Icons.send_rounded, size: 18),
            label: const Text('Gửi duyệt Revision'),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppTheme.primary,
              foregroundColor: const Color(0xFF04070E),
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
            ),
          ),
        if (status == 'in_review') ...[
          Tooltip(
            message: controller.canApprove ? '' : 'Chỉ Founder/Admin được phê duyệt',
            child: ElevatedButton.icon(
              onPressed: controller.canApprove && !controller.isSaving.value ? controller.approveRevision : null,
              icon: const Icon(Icons.verified_rounded, size: 18),
              label: const Text('Phê duyệt Revision'),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.success,
                foregroundColor: const Color(0xFF04070E),
                padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
              ),
            ),
          ),
          OutlinedButton.icon(
            onPressed: controller.isSaving.value ? null : () => _showRequestChangesDialog(context),
            icon: const Icon(Icons.replay_rounded, size: 18),
            label: const Text('Yêu cầu chỉnh sửa'),
            style: OutlinedButton.styleFrom(
              foregroundColor: AppTheme.accentLight,
              side: BorderSide(color: AppTheme.accentLight.withValues(alpha: 0.5)),
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
            ),
          ),
        ],
      ],
    );
  }

  void _showRequestChangesDialog(BuildContext context) {
    final reasonController = TextEditingController();

    AppModalDialog.show(
      context: context,
      title: 'Yêu cầu chỉnh sửa Revision',
      subtitle: 'Nêu rõ các nội dung cần cập nhật trước khi phê duyệt',
      icon: Icons.feedback_outlined,
      maxWidth: 580,
      content: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Lý do yêu cầu sửa đổi',
            style: TextStyle(color: AppTheme.textMutedDark, fontSize: 12, fontWeight: FontWeight.w500),
          ),
          const SizedBox(height: 6),
          TextField(
            controller: reasonController,
            maxLines: 4,
            decoration: const InputDecoration(
              hintText: 'Nhập chi tiết các điểm cần sửa trong Vision, Mission hoặc Core Values...',
            ),
          ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Get.back(),
          child: const Text('Huỷ', style: TextStyle(color: Colors.white60)),
        ),
        const SizedBox(width: 12),
        ElevatedButton(
          onPressed: () {
            final reason = reasonController.text.trim();
            if (reason.isEmpty) return;
            controller.requestChanges(reason);
            Get.back();
          },
          style: ElevatedButton.styleFrom(backgroundColor: AppTheme.accent),
          child: const Text('Gửi yêu cầu'),
        ),
      ],
    );
  }
}
