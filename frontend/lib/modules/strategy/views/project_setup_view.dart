import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../core/theme/app_theme.dart';
import '../controllers/project_setup_controller.dart';
import 'project_kickoff_view.dart';

/// Route `/projects/new` — full-screen, KHÔNG dùng `AppShell` (không sidebar
/// module, không chat dock). Pha `form` -> tạo project; pha `kickoff` -> tái
/// dùng `ProjectKickoffView` 3 bước; activate xong về `/hub`.
class ProjectSetupView extends StatelessWidget {
  const ProjectSetupView({super.key});

  @override
  Widget build(BuildContext context) {
    final controller = Get.isRegistered<ProjectSetupController>()
        ? Get.find<ProjectSetupController>()
        : Get.put(ProjectSetupController());

    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: AppTheme.backgroundLinearGradient,
        ),
        child: SafeArea(
          child: Obx(() {
            if (controller.phase.value == ProjectSetupPhase.kickoff) {
              final id = controller.createdProjectId.value ?? '';
              // FIX 2 (final review) — `ProjectKickoffView` không có nút đăng
              // xuất; thêm header mỏng chứa lối thoát để Founder không bị kẹt.
              return Column(
                children: [
                  _EscapeHatchRow(controller: controller),
                  Expanded(
                    child: ProjectKickoffView(
                      key: ValueKey('setup_kickoff_$id'),
                      projectId: id,
                      onBack: controller.onKickoffBack,
                      onActivated: controller.onKickoffActivated,
                      onOpenAdvancedRoadmap: controller.onOpenAdvancedRoadmap,
                    ),
                  ),
                ],
              );
            }
            return _ProjectSetupForm(controller: controller);
          }),
        ),
      ),
    );
  }
}

class _ProjectSetupForm extends StatefulWidget {
  const _ProjectSetupForm({required this.controller});
  final ProjectSetupController controller;

  @override
  State<_ProjectSetupForm> createState() => _ProjectSetupFormState();
}

class _ProjectSetupFormState extends State<_ProjectSetupForm> {
  final _title = TextEditingController();
  final _desc = TextEditingController();

  @override
  void dispose() {
    _title.dispose();
    _desc.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final c = widget.controller;
    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 520),
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Text(
                'Tạo dự án',
                style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: Colors.white),
              ),
              const SizedBox(height: 4),
              Text(
                'Đặt tên và mô tả ngắn về vấn đề. COSA sẽ đề xuất vòng đầu ở bước sau.',
                style: TextStyle(fontSize: 13, color: Colors.white.withValues(alpha: 0.7)),
              ),
              const SizedBox(height: 20),
              TextField(
                key: const ValueKey('project_setup_title_field'),
                controller: _title,
                style: const TextStyle(color: Colors.white),
                decoration: const InputDecoration(labelText: 'Tên dự án'),
              ),
              const SizedBox(height: 12),
              TextField(
                key: const ValueKey('project_setup_desc_field'),
                controller: _desc,
                minLines: 2,
                maxLines: 4,
                style: const TextStyle(color: Colors.white),
                decoration: const InputDecoration(labelText: 'Mô tả ngắn (tuỳ chọn)'),
              ),
              const SizedBox(height: 8),
              Obx(() => c.formError.value == null
                  ? const SizedBox.shrink()
                  : Padding(
                      padding: const EdgeInsets.only(top: 4),
                      child: Text(c.formError.value!,
                          style: const TextStyle(color: AppTheme.error, fontSize: 13)),
                    )),
              const SizedBox(height: 16),
              Obx(() => ElevatedButton(
                    key: const ValueKey('project_setup_submit_button'),
                    onPressed: c.isSubmitting.value
                        ? null
                        : () => c.submitForm(
                              title: _title.text,
                              description: _desc.text.isEmpty ? null : _desc.text,
                            ),
                    child: Text(c.isSubmitting.value ? 'Đang tạo...' : 'Tạo dự án'),
                  )),
              // FIX 4 (final review) — `isOnboarding` phụ thuộc `projectsList`
              // vốn rỗng cho tới khi FCC tải xong; bọc `Obx` để nút Huỷ xuất
              // hiện ngay khi danh sách project load về (không còn cần rebuild
              // thủ công).
              Obx(() => c.isOnboarding
                  ? const SizedBox.shrink()
                  : Padding(
                      padding: const EdgeInsets.only(top: 8),
                      child: TextButton(
                        key: const ValueKey('project_setup_cancel_button'),
                        onPressed: c.cancel,
                        child: const Text('Huỷ'),
                      ),
                    )),
              // FIX 2 (final review) — lối thoát LUÔN hiển thị (kể cả
              // onboarding): Founder tạo project lỗi liên tục vẫn đăng xuất /
              // đổi workspace được.
              _EscapeHatchRow(controller: c),
            ],
          ),
        ),
      ),
    );
  }
}

/// FIX 2 (final review) — hàng lối thoát dùng chung cho pha `form` và header
/// pha `kickoff` của `/projects/new`. Mọi route guard đều bounce về đây khi
/// `needsProjectSetup`, nên đây phải là nơi Founder rời được nếu bị kẹt.
class _EscapeHatchRow extends StatelessWidget {
  const _EscapeHatchRow({required this.controller});

  final ProjectSetupController controller;

  @override
  Widget build(BuildContext context) {
    // `Wrap` thay vì `Row` để hai nút xuống dòng khi viewport hẹp thay vì
    // tràn ngang (RenderFlex overflow).
    return Wrap(
      alignment: WrapAlignment.center,
      spacing: 8,
      children: [
        TextButton(
          key: const ValueKey('project_setup_logout_button'),
          onPressed: controller.logout,
          child: const Text('Đăng xuất'),
        ),
        TextButton(
          key: const ValueKey('project_setup_switch_workspace_button'),
          onPressed: controller.switchWorkspace,
          child: const Text('Đổi workspace'),
        ),
      ],
    );
  }
}
