import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/profile_controller.dart';
import '../../../core/theme/app_theme.dart';

class ProfileView extends GetView<ProfileController> {
  const ProfileView({super.key});

  static const _accent = AppTheme.primary;
  static const _bg = AppTheme.backgroundDark;
  static const _card = AppTheme.surfaceDark;
  static const _muted = AppTheme.textMutedDark;
  static const _border = AppTheme.borderDark;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: _bg,
      appBar: AppBar(
        backgroundColor: _bg,
        elevation: 0,
        title: const Text('Hồ sơ của tôi', style: TextStyle(color: Colors.white)),
        iconTheme: const IconThemeData(color: Colors.white),
      ),
      body: Obx(() {
        if (controller.isLoading.value) {
          return const Center(child: CircularProgressIndicator(color: _accent));
        }

        return SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 480),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Center(
                  child: Container(
                    width: 72,
                    height: 72,
                    decoration: BoxDecoration(
                      color: _accent.withValues(alpha: 0.12),
                      shape: BoxShape.circle,
                      border: Border.all(color: _accent.withValues(alpha: 0.4)),
                    ),
                    child: const Icon(Icons.person, size: 36, color: _accent),
                  ),
                ),
                const SizedBox(height: 12),
                Center(
                  child: Text(
                    controller.displayName.value.isNotEmpty ? controller.displayName.value : 'Chưa đặt tên',
                    style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
                  ),
                ),
                if (controller.role.value != null)
                  Center(
                    child: Padding(
                      padding: const EdgeInsets.only(top: 4),
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                        decoration: BoxDecoration(
                          color: _accent.withValues(alpha: 0.1),
                          borderRadius: BorderRadius.circular(20),
                          border: Border.all(color: _accent.withValues(alpha: 0.3)),
                        ),
                        child: Text(
                          controller.role.value!,
                          style: const TextStyle(color: _accent, fontSize: 11, fontWeight: FontWeight.w600),
                        ),
                      ),
                    ),
                  ),
                const SizedBox(height: 24),

                Obx(() => controller.errorMessage.value.isNotEmpty
                    ? _MessageBanner(text: controller.errorMessage.value, isError: true)
                    : const SizedBox.shrink()),
                Obx(() => controller.successMessage.value.isNotEmpty
                    ? _MessageBanner(text: controller.successMessage.value, isError: false)
                    : const SizedBox.shrink()),

                _SectionCard(
                  title: 'Email',
                  child: Row(
                    children: [
                      const Icon(Icons.email_outlined, color: _muted, size: 18),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          controller.email.value,
                          style: const TextStyle(color: Colors.white, fontSize: 14),
                        ),
                      ),
                      const Icon(Icons.lock_outline, color: _muted, size: 16),
                    ],
                  ),
                ),
                const SizedBox(height: 16),

                _SectionCard(
                  title: 'Họ và tên',
                  child: Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: controller.displayNameController,
                          style: const TextStyle(color: Colors.white, fontSize: 14),
                          decoration: const InputDecoration(
                            border: InputBorder.none,
                            isDense: true,
                          ),
                        ),
                      ),
                      Obx(() => controller.isSaving.value
                          ? const SizedBox(
                              width: 18,
                              height: 18,
                              child: CircularProgressIndicator(strokeWidth: 2, color: _accent),
                            )
                          : IconButton(
                              icon: const Icon(Icons.check_circle_outline, color: _accent, size: 20),
                              onPressed: controller.saveDisplayName,
                              tooltip: 'Lưu tên',
                            )),
                    ],
                  ),
                ),
                const SizedBox(height: 16),

                _SectionCard(
                  title: 'Số điện thoại',
                  child: Obx(() {
                    final hasPhone = controller.phone.value != null && controller.phone.value!.isNotEmpty;
                    if (!hasPhone && !controller.isEditingPhone.value) {
                      return Row(
                        children: [
                          const Expanded(
                            child: Text(
                              'Chưa cập nhật số điện thoại',
                              style: TextStyle(color: _muted, fontSize: 13, fontStyle: FontStyle.italic),
                            ),
                          ),
                          TextButton.icon(
                            onPressed: () => controller.isEditingPhone.value = true,
                            icon: const Icon(Icons.add, size: 16, color: _accent),
                            label: const Text('Thêm', style: TextStyle(color: _accent, fontSize: 13)),
                          ),
                        ],
                      );
                    }

                    if (hasPhone && !controller.isEditingPhone.value) {
                      return Row(
                        children: [
                          const Icon(Icons.phone_outlined, color: _muted, size: 18),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Text(
                              controller.phone.value!,
                              style: const TextStyle(color: Colors.white, fontSize: 14),
                            ),
                          ),
                          IconButton(
                            icon: const Icon(Icons.edit_outlined, color: _muted, size: 18),
                            onPressed: () => controller.isEditingPhone.value = true,
                            tooltip: 'Sửa',
                          ),
                        ],
                      );
                    }

                    return Row(
                      children: [
                        Expanded(
                          child: TextField(
                            controller: controller.phoneController,
                            keyboardType: TextInputType.phone,
                            autofocus: true,
                            style: const TextStyle(color: Colors.white, fontSize: 14),
                            decoration: const InputDecoration(
                              border: InputBorder.none,
                              isDense: true,
                              hintText: 'Ví dụ: 0912345678',
                              hintStyle: TextStyle(color: AppTheme.textDimDark, fontSize: 12),
                            ),
                          ),
                        ),
                        Obx(() => controller.isSaving.value
                            ? const SizedBox(
                                width: 18,
                                height: 18,
                                child: CircularProgressIndicator(strokeWidth: 2, color: _accent),
                              )
                            : IconButton(
                                icon: const Icon(Icons.check_circle_outline, color: _accent, size: 20),
                                onPressed: controller.savePhone,
                                tooltip: 'Lưu số điện thoại',
                              )),
                      ],
                    );
                  }),
                ),
                const SizedBox(height: 32),

                OutlinedButton.icon(
                  onPressed: controller.logout,
                  icon: const Icon(Icons.logout, size: 18, color: AppTheme.accentLight),
                  label: const Text('Đăng xuất', style: TextStyle(color: AppTheme.accentLight)),
                  style: OutlinedButton.styleFrom(
                    side: const BorderSide(color: AppTheme.accentLight),
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(100)),
                  ),
                ),
              ],
            ),
          ),
        );
      }),
    );
  }
}

class _SectionCard extends StatelessWidget {
  final String title;
  final Widget child;

  const _SectionCard({required this.title, required this.child});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: ProfileView._card.withValues(alpha: 0.85),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: ProfileView._border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: const TextStyle(color: ProfileView._muted, fontSize: 11, fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 6),
          child,
        ],
      ),
    );
  }
}

class _MessageBanner extends StatelessWidget {
  final String text;
  final bool isError;

  const _MessageBanner({required this.text, required this.isError});

  @override
  Widget build(BuildContext context) {
    final color = isError ? AppTheme.accentLight : AppTheme.success;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      margin: const EdgeInsets.only(bottom: 16),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withValues(alpha: 0.5)),
      ),
      child: Row(
        children: [
          Icon(isError ? Icons.error_outline : Icons.check_circle_outline, size: 18, color: color),
          const SizedBox(width: 10),
          Expanded(child: Text(text, style: TextStyle(color: color, fontSize: 13))),
        ],
      ),
    );
  }
}
