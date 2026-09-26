import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../core/localization/locale_controller.dart';
import '../../../core/localization/supported_locale.dart';
import '../../../core/routing/app_routes.dart';
import '../../../core/session/session_controller.dart';
import '../../../core/theme/app_theme.dart';
import '../../auth/views/widgets/auth_language_switcher.dart';
import '../../hologram_hub/controllers/founder_command_center_controller.dart';
import '../../strategy/services/strategy_service.dart';
import '../widgets/p0_core_setup_banner.dart';

/// Màn tạo project đầu tiên khi workspace chưa có project nào.
/// Thay cho luồng kickoff/stage-gate framework cũ — chỉ nhận title + mô tả;
/// lifecycle stage khởi tạo mặc định `P0_DISCOVERY` ở backend và được chuyển
/// thủ công qua màn Project Operating Loop.
class CreateFirstProjectView extends StatefulWidget {
  const CreateFirstProjectView({super.key});

  @override
  State<CreateFirstProjectView> createState() => _CreateFirstProjectViewState();
}

class _CreateFirstProjectViewState extends State<CreateFirstProjectView> {
  final _title = TextEditingController();
  final _description = TextEditingController();
  bool _submitting = false;
  String? _error;

  @override
  void dispose() {
    _title.dispose();
    _description.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final isEn = _isEnglish();
    final title = _title.text.trim();
    final description = _description.text.trim();

    if (title.isEmpty) {
      setState(() => _error = isEn ? 'Please enter a project name' : 'Vui lòng nhập tên project');
      return;
    }
    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      final strategyService = StrategyService();
      final project = await strategyService.createBasicProject(
        title: title,
        description: description.isNotEmpty ? description : null,
      );

      // Cập nhật trạng thái projectsList cho FounderCommandCenterController
      // để ProjectSetupGuardMiddleware không đẩy ngược lại /projects/new.
      if (Get.isRegistered<FounderCommandCenterController>()) {
        final fcc = Get.find<FounderCommandCenterController>();
        try {
          await fcc.loadDashboardData();
        } catch (e) {
          debugPrint('[CreateFirstProjectView] fcc.loadDashboardData error: $e');
          fcc.projectsList.assignAll([project]);
          fcc.hasProjects.value = true;
          fcc.projectsLoadedOnce.value = true;
        }
      }

      final createdId = project['id']?.toString() ?? '';
      final createdTitle = project['title']?.toString() ?? title;

      if (createdId.isNotEmpty) {
        // Project đã tạo nhưng P0 Core chưa hội tụ ⇒ màn phân tích hiện banner sửa.
        final p0Flag = isP0CoreBootstrapIncomplete(project) ? '&p0CoreIncomplete=1' : '';
        Get.offAllNamed(
          '${AppRoutes.projectAnalysisFor(createdId)}?title=${Uri.encodeComponent(createdTitle)}$p0Flag',
        );
      } else {
        Get.offAllNamed(AppRoutes.hub);
      }
    } catch (e) {
      setState(() {
        _submitting = false;
        _error = e.toString();
      });
    }
  }

  bool _isEnglish() {
    if (Get.isRegistered<LocaleController>()) {
      return Get.find<LocaleController>().current.value == SupportedLocale.enUS;
    }
    return Get.locale?.languageCode == 'en';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.backgroundDark,
      body: Container(
        decoration: const BoxDecoration(
          gradient: AppTheme.backgroundRadialGradient,
        ),
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 480),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  _buildFormCard(context),
                  const SizedBox(height: 20),
                  _buildFooter(context),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildFormCard(BuildContext context) {
    Widget cardContent(bool isEn) {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 36),
        decoration: BoxDecoration(
          color: AppTheme.surfaceDark.withValues(alpha: 0.88),
          borderRadius: BorderRadius.circular(18),
          border: Border.all(
            color: AppTheme.primary.withValues(alpha: 0.25),
            width: 1.2,
          ),
          boxShadow: [
            BoxShadow(
              color: AppTheme.primary.withValues(alpha: 0.08),
              blurRadius: 32,
              offset: const Offset(0, 8),
            ),
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.45),
              blurRadius: 24,
              offset: const Offset(0, 10),
            ),
          ],
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Icon Header
            Center(
              child: Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: AppTheme.primary.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(
                    color: AppTheme.primary.withValues(alpha: 0.35),
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: AppTheme.primary.withValues(alpha: 0.2),
                      blurRadius: 18,
                    ),
                  ],
                ),
                child: const Icon(
                  Icons.rocket_launch_rounded,
                  size: 36,
                  color: AppTheme.primary,
                ),
              ),
            ),
            const SizedBox(height: 20),

            // Title inside the Card
            Text(
              isEn ? 'Create your first project' : 'Tạo project đầu tiên',
              textAlign: TextAlign.center,
              style: const TextStyle(
                fontSize: 22,
                fontWeight: FontWeight.w700,
                letterSpacing: -0.4,
                color: Colors.white,
              ),
            ),
            const SizedBox(height: 8),

            // Subtitle
            Text(
              isEn
                  ? 'Every workspace begins with a project. Name yours to start collaborating with AI agents.'
                  : 'Mỗi workspace bắt đầu với một dự án. Đặt tên dự án để bắt đầu làm việc cùng các AI agent.',
              textAlign: TextAlign.center,
              style: const TextStyle(
                fontSize: 13.5,
                color: AppTheme.textMutedDark,
                height: 1.4,
              ),
            ),
            const SizedBox(height: 28),

            // Form Fields
            TextField(
              controller: _title,
              autofocus: true,
              textInputAction: TextInputAction.next,
              style: const TextStyle(color: Colors.white, fontSize: 14),
              decoration: InputDecoration(
                labelText: isEn ? 'Project name' : 'Tên project',
                hintText: isEn ? 'e.g. Acme Core Platform' : 'VD: Nền tảng SaaS COSA',
                prefixIcon: const Icon(Icons.folder_outlined, size: 20, color: AppTheme.textMutedDark),
              ),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _description,
              maxLines: 3,
              textInputAction: TextInputAction.done,
              onSubmitted: (_) => _submit(),
              style: const TextStyle(color: Colors.white, fontSize: 14),
              decoration: InputDecoration(
                labelText: isEn ? 'Description (optional)' : 'Mô tả (tuỳ chọn)',
                hintText: isEn ? 'Briefly describe your project...' : 'Mô tả ngắn gọn về dự án...',
                alignLabelWithHint: true,
                prefixIcon: const Padding(
                  padding: EdgeInsets.only(bottom: 42),
                  child: Icon(Icons.notes_rounded, size: 20, color: AppTheme.textMutedDark),
                ),
              ),
            ),

            if (_error != null) ...[
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                decoration: BoxDecoration(
                  color: AppTheme.accent.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(
                    color: AppTheme.accent.withValues(alpha: 0.6),
                  ),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.error_outline, size: 18, color: AppTheme.accent),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        _error!,
                        style: const TextStyle(color: AppTheme.accentLight, fontSize: 13),
                      ),
                    ),
                  ],
                ),
              ),
            ],

            const SizedBox(height: 24),

            // Submit Button
            SizedBox(
              height: 48,
              child: ElevatedButton(
                onPressed: _submitting ? null : _submit,
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.primary,
                  foregroundColor: const Color(0xFF04070E),
                  disabledBackgroundColor: AppTheme.primary.withValues(alpha: 0.35),
                  elevation: 0,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(10),
                  ),
                  textStyle: const TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                child: _submitting
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(
                          strokeWidth: 2.2,
                          color: Color(0xFF04070E),
                        ),
                      )
                    : Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          const Icon(Icons.add_rounded, size: 20),
                          const SizedBox(width: 8),
                          Text(isEn ? 'Create project' : 'Tạo project'),
                        ],
                      ),
              ),
            ),
          ],
        ),
      );
    }

    if (Get.isRegistered<LocaleController>()) {
      return Obx(() {
        final lc = Get.find<LocaleController>();
        final isEn = lc.current.value == SupportedLocale.enUS;
        return cardContent(isEn);
      });
    }

    return cardContent(_isEnglish());
  }

  Widget _buildFooter(BuildContext context) {
    Widget footerContent(bool isEn) {
      return Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const AuthLanguageSwitcher(),
          if (Get.isRegistered<SessionController>()) ...[
            const SizedBox(width: 16),
            TextButton.icon(
              onPressed: () => Get.find<SessionController>().logout(),
              icon: const Icon(Icons.logout_rounded, size: 16, color: AppTheme.textMutedDark),
              label: Text(
                isEn ? 'Log out' : 'Đăng xuất',
                style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 13),
              ),
            ),
          ],
        ],
      );
    }

    if (Get.isRegistered<LocaleController>()) {
      return Obx(() {
        final lc = Get.find<LocaleController>();
        final isEn = lc.current.value == SupportedLocale.enUS;
        return footerContent(isEn);
      });
    }

    return footerContent(_isEnglish());
  }
}
