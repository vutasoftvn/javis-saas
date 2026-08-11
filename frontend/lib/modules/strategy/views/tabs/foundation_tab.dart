import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../controllers/foundation_controller.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/widgets/app_modal_dialog.dart';
import '../widgets/core_value_card.dart';
import '../widgets/revision_status_badge.dart';
import '../widgets/evidence_table.dart';

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

      return SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 28),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (controller.errorMessage.value != null) _buildErrorBanner(),
            _buildCanvasHeader(context),
            const SizedBox(height: 32),
            if (controller.currentRevision.value != null) ...[
              _buildFoundationSection(),
              const SizedBox(height: 36),
              _buildContextBuilderSection(context),
              const SizedBox(height: 36),
              _buildReviewActions(context),
            ],
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
      return Container(
        padding: const EdgeInsets.all(28),
        decoration: BoxDecoration(
          color: AppTheme.surfaceDark.withValues(alpha: 0.5),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: AppTheme.primary.withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(14),
              ),
              child: const Icon(Icons.rocket_launch_rounded, color: AppTheme.primaryLight, size: 28),
            ),
            const SizedBox(width: 20),
            const Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Bắt đầu với Strategy Canvas',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white),
                  ),
                  SizedBox(height: 4),
                  Text(
                    'Khởi tạo khung chiến lược doanh nghiệp với 1 Vision, 1 Mission và 3 Core Values.',
                    style: TextStyle(color: AppTheme.textMutedDark, fontSize: 14),
                  ),
                ],
              ),
            ),
            ElevatedButton.icon(
              onPressed: () => _showCreateCanvasDialog(context),
              icon: const Icon(Icons.add_rounded),
              label: const Text('Tạo Strategy Canvas'),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.primary,
                foregroundColor: const Color(0xFF04070E),
                padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
              ),
            ),
          ],
        ),
      );
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
                  onPressed: () => _showCreateCanvasDialog(context),
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
          TextField(
            controller: nameController,
            decoration: const InputDecoration(
              labelText: 'Tên Strategy Canvas',
              prefixIcon: Icon(Icons.label_outline_rounded, size: 20),
            ),
          ),
          const SizedBox(height: 16),
          TextField(
            controller: descController,
            maxLines: 4,
            decoration: const InputDecoration(
              labelText: 'Mô tả công ty / Định hướng sản phẩm',
              alignLabelWithHint: true,
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

  void _showCreateCanvasDialog(BuildContext context) {
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
          TextField(
            controller: nameController,
            decoration: const InputDecoration(
              labelText: 'Tên Strategy Canvas',
              hintText: 'Ví dụ: Kế hoạch Chiến lược 2026',
              prefixIcon: Icon(Icons.label_outline_rounded, size: 20),
            ),
          ),
          const SizedBox(height: 20),
          TextField(
            controller: descController,
            decoration: const InputDecoration(
              labelText: 'Mô tả công ty / Định hướng sản phẩm',
              hintText: 'Nhập thông tin tổng quan công ty để AI tự động tạo đề xuất 1 Vision, 1 Mission và 3 Core Values...',
              alignLabelWithHint: true,
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
        TextField(
          controller: controller.visionController,
          readOnly: readOnly,
          maxLength: 500,
          maxLines: 2,
          decoration: const InputDecoration(
            labelText: 'Tầm nhìn (Vision: 20-500 ký tự)',
            hintText: 'Mục tiêu tối thượng và hình ảnh công ty trong tương lai...',
            prefixIcon: Icon(Icons.visibility_rounded, size: 20),
          ),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: controller.missionController,
          readOnly: readOnly,
          maxLength: 500,
          maxLines: 2,
          decoration: const InputDecoration(
            labelText: 'Sứ mệnh (Mission: 20-500 ký tự)',
            hintText: 'Lý do công ty tồn tại và giá trị đem lại cho khách hàng hàng ngày...',
            prefixIcon: Icon(Icons.track_changes_rounded, size: 20),
          ),
        ),
        const SizedBox(height: 16),
        GridView.count(
          crossAxisCount: 3,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          crossAxisSpacing: 16,
          mainAxisSpacing: 16,
          childAspectRatio: 0.85,
          children: List.generate(
            3,
            (i) => CoreValueCard(
              slotNo: i + 1,
              titleController: controller.valueTitleControllers[i],
              descriptionController: controller.valueDescriptionControllers[i],
              decisionRuleController: controller.valueDecisionRuleControllers[i],
              readOnly: readOnly,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildContextBuilderSection(BuildContext context) {
    final readOnly = !controller.canEdit;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Row(
          children: [
            Icon(Icons.inventory_2_rounded, color: AppTheme.secondaryLight, size: 22),
            SizedBox(width: 10),
            Text(
              'Project Context Pack',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white),
            ),
          ],
        ),
        const SizedBox(height: 16),
        DefaultTabController(
          length: 3,
          child: Container(
            height: 480,
            decoration: BoxDecoration(
              color: AppTheme.surfaceDark.withValues(alpha: 0.4),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
            ),
            child: Column(
              children: [
                const TabBar(
                  indicatorColor: AppTheme.secondaryLight,
                  labelColor: Colors.white,
                  unselectedLabelColor: Colors.white60,
                  tabs: [
                    Tab(text: 'Bối cảnh kinh doanh (Business Context)'),
                    Tab(text: 'Nguồn lực nội bộ (Internal Resources)'),
                    Tab(text: 'Thư viện Bằng chứng (Evidence)'),
                  ],
                ),
                Expanded(
                  child: TabBarView(
                    children: [
                      Padding(
                        padding: const EdgeInsets.all(20),
                        child: Column(
                          children: [
                            Expanded(
                              child: TextField(
                                controller: controller.businessContextController,
                                readOnly: readOnly,
                                maxLines: 12,
                                decoration: const InputDecoration(
                                  labelText: 'Khách hàng, nỗi đau, sản phẩm, mô hình doanh thu, phạm vi hoạt động',
                                  alignLabelWithHint: true,
                                ),
                              ),
                            ),
                            const SizedBox(height: 12),
                            if (!readOnly)
                              Align(
                                alignment: Alignment.centerRight,
                                child: ElevatedButton.icon(
                                  onPressed: controller.isSaving.value ? null : controller.saveContextPack,
                                  icon: const Icon(Icons.save_rounded, size: 18),
                                  label: const Text('Lưu Context Pack'),
                                  style: ElevatedButton.styleFrom(
                                    backgroundColor: AppTheme.secondary,
                                    foregroundColor: const Color(0xFF04070E),
                                  ),
                                ),
                              ),
                          ],
                        ),
                      ),
                      Padding(
                        padding: const EdgeInsets.all(20),
                        child: Column(
                          children: [
                            Expanded(
                              child: TextField(
                                controller: controller.internalResourcesController,
                                readOnly: readOnly,
                                maxLines: 12,
                                decoration: const InputDecoration(
                                  labelText: 'Thời gian founder, ngân sách/runway, kỹ năng team, stack công nghệ, rào cản',
                                  alignLabelWithHint: true,
                                ),
                              ),
                            ),
                            const SizedBox(height: 12),
                            if (!readOnly)
                              Align(
                                alignment: Alignment.centerRight,
                                child: ElevatedButton.icon(
                                  onPressed: controller.isSaving.value ? null : controller.saveContextPack,
                                  icon: const Icon(Icons.save_rounded, size: 18),
                                  label: const Text('Lưu Context Pack'),
                                  style: ElevatedButton.styleFrom(
                                    backgroundColor: AppTheme.secondary,
                                    foregroundColor: const Color(0xFF04070E),
                                  ),
                                ),
                              ),
                          ],
                        ),
                      ),
                      Padding(
                        padding: const EdgeInsets.all(20),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                const Text('Chọn Evidence đưa vào Context Pack:', style: TextStyle(color: AppTheme.textMutedDark, fontSize: 13)),
                                OutlinedButton.icon(
                                  onPressed: () => _showCreateEvidenceDialog(context),
                                  icon: const Icon(Icons.add_rounded, size: 16),
                                  label: const Text('Thêm nguồn mới'),
                                  style: OutlinedButton.styleFrom(
                                    foregroundColor: AppTheme.secondaryLight,
                                    side: BorderSide(color: AppTheme.secondaryLight.withValues(alpha: 0.5)),
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 12),
                            Expanded(
                              child: SingleChildScrollView(
                                child: EvidenceTable(
                                  evidence: controller.evidenceList,
                                  selectedIds: controller.selectedEvidenceIds,
                                  onToggle: controller.toggleEvidence,
                                ),
                              ),
                            ),
                            const SizedBox(height: 12),
                            if (!readOnly)
                              Align(
                                alignment: Alignment.centerRight,
                                child: ElevatedButton.icon(
                                  onPressed: controller.isSaving.value ? null : controller.linkSelectedEvidence,
                                  icon: const Icon(Icons.link_rounded, size: 18),
                                  label: const Text('Lưu liên kết Evidence'),
                                  style: ElevatedButton.styleFrom(
                                    backgroundColor: AppTheme.secondary,
                                    foregroundColor: const Color(0xFF04070E),
                                  ),
                                ),
                              ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
        if (controller.currentContextPack.value != null && controller.currentContextPack.value!['status'] != 'approved')
          Padding(
            padding: const EdgeInsets.only(top: 16),
            child: Tooltip(
              message: controller.canApprove ? '' : 'Chỉ Founder/Admin được phê duyệt',
              child: ElevatedButton.icon(
                onPressed: controller.canApprove && !controller.isSaving.value ? controller.approveContextPack : null,
                icon: const Icon(Icons.check_circle_rounded, size: 18),
                label: const Text('Phê duyệt Context Pack'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.secondary,
                  foregroundColor: const Color(0xFF04070E),
                ),
              ),
            ),
          ),
      ],
    );
  }

  void _showCreateEvidenceDialog(BuildContext context) {
    final titleController = TextEditingController();
    final summaryController = TextEditingController();
    String sourceType = 'note';
    String reliability = 'medium';

    AppModalDialog.show(
      context: context,
      title: 'Thêm Evidence mới',
      subtitle: 'Lưu trữ tài liệu tham khảo, phỏng vấn, chỉ số thị trường',
      icon: Icons.library_books_rounded,
      maxWidth: 640,
      content: StatefulBuilder(
        builder: (context, setState) => Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            TextField(
              controller: titleController,
              decoration: const InputDecoration(
                labelText: 'Tên nguồn dữ liệu',
                hintText: 'Ví dụ: Phỏng vấn 20 khách hàng B2B Q1',
                prefixIcon: Icon(Icons.title_rounded, size: 20),
              ),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: summaryController,
              maxLines: 3,
              decoration: const InputDecoration(
                labelText: 'Dữ kiện tóm tắt',
                hintText: 'Những thông tin, con số hoặc nhận định quan trọng thu thập được...',
                alignLabelWithHint: true,
              ),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: DropdownButtonFormField<String>(
                    initialValue: sourceType,
                    dropdownColor: AppTheme.surfaceDark,
                    decoration: const InputDecoration(labelText: 'Loại nguồn'),
                    items: const [
                      DropdownMenuItem(value: 'customer_interview', child: Text('Phỏng vấn khách hàng')),
                      DropdownMenuItem(value: 'market_report', child: Text('Báo cáo thị trường')),
                      DropdownMenuItem(value: 'internal_metric', child: Text('Chỉ số nội bộ')),
                      DropdownMenuItem(value: 'regulation', child: Text('Quy định / Pháp lý')),
                      DropdownMenuItem(value: 'competitor', child: Text('Phân tích đối thủ')),
                      DropdownMenuItem(value: 'note', child: Text('Ghi chú tự do')),
                    ],
                    onChanged: (v) => setState(() => sourceType = v ?? 'note'),
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: DropdownButtonFormField<String>(
                    initialValue: reliability,
                    dropdownColor: AppTheme.surfaceDark,
                    decoration: const InputDecoration(labelText: 'Độ tin cậy'),
                    items: const [
                      DropdownMenuItem(value: 'high', child: Text('Cao (High)')),
                      DropdownMenuItem(value: 'medium', child: Text('Trung bình (Medium)')),
                      DropdownMenuItem(value: 'low', child: Text('Thấp (Low)')),
                    ],
                    onChanged: (v) => setState(() => reliability = v ?? 'medium'),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Get.back(),
          child: const Text('Huỷ', style: TextStyle(color: Colors.white60)),
        ),
        const SizedBox(width: 12),
        ElevatedButton(
          onPressed: () {
            final title = titleController.text.trim();
            final summary = summaryController.text.trim();
            if (title.isEmpty || summary.isEmpty) return;
            controller.createEvidence(
              title: title,
              summary: summary,
              sourceType: sourceType,
              reliability: reliability,
            );
            Get.back();
          },
          style: ElevatedButton.styleFrom(
            backgroundColor: AppTheme.primary,
            foregroundColor: const Color(0xFF04070E),
          ),
          child: const Text('Tạo Evidence'),
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
      content: TextField(
        controller: reasonController,
        maxLines: 4,
        decoration: const InputDecoration(
          labelText: 'Lý do yêu cầu sửa đổi',
          hintText: 'Nhập chi tiết các điểm cần sửa trong Vision, Mission hoặc Core Values...',
          alignLabelWithHint: true,
        ),
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
