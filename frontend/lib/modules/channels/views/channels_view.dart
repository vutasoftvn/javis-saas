import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/channels_controller.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/floating_app_bar.dart';

class ChannelsView extends GetView<ChannelsController> {
  const ChannelsView({super.key});

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<ChannelsController>()) {
      Get.put(ChannelsController());
    }

    return Container(
      color: Colors.transparent,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // 1. Top Floating AppBar Card
          const JavisFloatingAppBar(
            title: 'Kênh kết nối',
            subtitle: 'Telegram & hơn nữa',
            icon: Icons.send_rounded,
          ),

          // Main scrollable content
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
                    _buildTelegramSection(context),
                    const SizedBox(height: 32),
                    _buildZaloSection(context),
                  ],
                ),
              );
            }),
          ),
        ],
      ),
    );
  }

  // --- TELEGRAM CARD SECTION ---
  Widget _buildTelegramSection(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: const [
            Text(
              'TELEGRAM',
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.bold,
                color: AppTheme.textMutedDark,
                letterSpacing: 1.1,
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        Container(
          decoration: BoxDecoration(
            color: AppTheme.surfaceDark,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: AppTheme.borderDark),
          ),
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Checkbox Toggle: Bật bot Telegram
              Obx(
                () => Row(
                  children: [
                    Checkbox(
                      value: controller.telegramEnabled.value,
                      onChanged: (val) =>
                          controller.telegramEnabled.value = val ?? false,
                      activeColor: AppTheme.primary,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(4),
                      ),
                    ),
                    GestureDetector(
                      onTap: () => controller.telegramEnabled.value =
                          !controller.telegramEnabled.value,
                      child: const Text(
                        'Bật bot Telegram',
                        style: TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w600,
                          color: AppTheme.textDark,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 20),

              // Bot token field
              const Text(
                'Bot token',
                style: TextStyle(
                  fontSize: 14,
                  color: AppTheme.textMutedDark,
                  fontWeight: FontWeight.w500,
                ),
              ),
              const SizedBox(height: 8),
              Obx(
                () => TextField(
                  controller: controller.telegramTokenController,
                  obscureText: controller.telegramObscureToken.value,
                  style: const TextStyle(
                    color: AppTheme.textDark,
                    fontSize: 14,
                  ),
                  decoration: InputDecoration(
                    hintText: 'Ví dụ: 123456:ABC...',
                    suffixIcon: IconButton(
                      icon: Icon(
                        controller.telegramObscureToken.value
                            ? Icons.visibility_off
                            : Icons.visibility,
                        color: AppTheme.textMutedDark,
                      ),
                      onPressed: () => controller.telegramObscureToken.toggle(),
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 20),

              // Chat ID allowed field
              RichText(
                text: const TextSpan(
                  style: TextStyle(fontSize: 14, fontFamily: 'Inter'),
                  children: [
                    TextSpan(
                      text: 'Chat ID được phép dùng ',
                      style: TextStyle(
                        color: AppTheme.textMutedDark,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                    TextSpan(
                      text:
                          '(nhiều ID cách nhau dấu phẩy - mỗi người /start bot rồi thêm ID vào đây)',
                      style: TextStyle(color: Color(0xFF10B981), fontSize: 13),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: controller.telegramChatIdsController,
                style: const TextStyle(color: AppTheme.textDark, fontSize: 14),
                decoration: const InputDecoration(
                  hintText: 'Ví dụ: 123456789, 987654321',
                ),
              ),
              const SizedBox(height: 24),

              // Action buttons: Lưu & Bật / Gửi test
              Row(
                children: [
                  Obx(
                    () => ElevatedButton(
                      onPressed: controller.isSavingTelegram.value
                          ? null
                          : controller.saveTelegram,
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF252F42),
                        foregroundColor: AppTheme.textDark,
                        elevation: 0,
                        side: const BorderSide(color: Color(0xFF334155)),
                        minimumSize: const Size(64, 44),
                        padding: const EdgeInsets.symmetric(
                          horizontal: 20,
                          vertical: 12,
                        ),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(100),
                        ),
                      ),
                      child: controller.isSavingTelegram.value
                          ? const SizedBox(
                              width: 16,
                              height: 16,
                              child: CircularProgressIndicator(
                                strokeWidth: 2,
                                color: Colors.white,
                              ),
                            )
                          : const Text(
                              'Lưu & bật',
                              style: TextStyle(fontWeight: FontWeight.w600),
                            ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Obx(
                    () => OutlinedButton(
                      onPressed: controller.isTestingTelegram.value
                          ? null
                          : controller.testTelegram,
                      style: OutlinedButton.styleFrom(
                        foregroundColor: AppTheme.textDark,
                        side: const BorderSide(color: Color(0xFF334155)),
                        minimumSize: const Size(64, 44),
                        padding: const EdgeInsets.symmetric(
                          horizontal: 20,
                          vertical: 12,
                        ),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(100),
                        ),
                      ),
                      child: controller.isTestingTelegram.value
                          ? const SizedBox(
                              width: 16,
                              height: 16,
                              child: CircularProgressIndicator(
                                strokeWidth: 2,
                                color: Colors.white,
                              ),
                            )
                          : const Text(
                              'Gửi test',
                              style: TextStyle(fontWeight: FontWeight.w600),
                            ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),

              // Status message text
              Obx(() {
                final isEnabled = controller.telegramEnabled.value;
                final botUname = controller.telegramBotUsername.value;
                if (!isEnabled) {
                  return const Text(
                    '○ Bot CHƯA bật - tích \'Bật bot Telegram\' rồi Lưu (test gửi được KHÔNG có nghĩa bot đang nhận tin).',
                    style: TextStyle(
                      color: AppTheme.textMutedDark,
                      fontSize: 13,
                    ),
                  );
                }
                return Text(
                  '● Bot ĐANG BẬT${botUname.isNotEmpty ? " (@$botUname)" : ""}. sẵn sàng nhận tin nhắn từ Telegram.',
                  style: const TextStyle(
                    color: Color(0xFF10B981),
                    fontSize: 13,
                    fontWeight: FontWeight.w500,
                  ),
                );
              }),
            ],
          ),
        ),
      ],
    );
  }

  // --- ZALO CARD SECTION ---
  Widget _buildZaloSection(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Container(
              width: 18,
              height: 18,
              decoration: const BoxDecoration(
                color: Color(0xFF0068FF),
                shape: BoxShape.circle,
              ),
              child: const Center(
                child: Text(
                  'Z',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 11,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ),
            const SizedBox(width: 8),
            const Text(
              'ZALO',
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.bold,
                color: AppTheme.textMutedDark,
                letterSpacing: 1.1,
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        Container(
          decoration: BoxDecoration(
            color: AppTheme.surfaceDark,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: AppTheme.borderDark),
          ),
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Description box
              const Text(
                'Bot Zalo chính thức để hỏi Javis từ điện thoại. Khác Zalo Agent MCP ở trang Kết nối: cái kia đăng nhập chính tài khoản của bạn để Javis thao tác thay bạn, cái này là một danh tính riêng, an toàn, để bạn nhắn cho Javis.',
                style: TextStyle(
                  color: AppTheme.textMutedDark,
                  fontSize: 14,
                  height: 1.4,
                ),
              ),
              const SizedBox(height: 20),

              // Checkbox Toggle: Bật bot Zalo
              Obx(
                () => Row(
                  children: [
                    Checkbox(
                      value: controller.zaloEnabled.value,
                      onChanged: (val) =>
                          controller.zaloEnabled.value = val ?? false,
                      activeColor: const Color(0xFF0068FF),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(4),
                      ),
                    ),
                    GestureDetector(
                      onTap: () => controller.zaloEnabled.value =
                          !controller.zaloEnabled.value,
                      child: const Text(
                        'Bật bot Zalo',
                        style: TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w600,
                          color: AppTheme.textDark,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 20),

              // Bot token field
              const Text(
                'Bot token',
                style: TextStyle(
                  fontSize: 14,
                  color: AppTheme.textMutedDark,
                  fontWeight: FontWeight.w500,
                ),
              ),
              const SizedBox(height: 8),
              Obx(
                () => TextField(
                  controller: controller.zaloTokenController,
                  obscureText: controller.zaloObscureToken.value,
                  style: const TextStyle(
                    color: AppTheme.textDark,
                    fontSize: 14,
                  ),
                  decoration: InputDecoration(
                    hintText: 'Ví dụ: 123456789:abc-xyz',
                    suffixIcon: IconButton(
                      icon: Icon(
                        controller.zaloObscureToken.value
                            ? Icons.visibility_off
                            : Icons.visibility,
                        color: AppTheme.textMutedDark,
                      ),
                      onPressed: () => controller.zaloObscureToken.toggle(),
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 8),

              // Instruction text for Zalo token
              RichText(
                text: const TextSpan(
                  style: TextStyle(
                    fontSize: 13,
                    color: AppTheme.textMutedDark,
                    height: 1.4,
                    fontFamily: 'Inter',
                  ),
                  children: [
                    TextSpan(
                      text: 'Lấy token: mở app Zalo, tìm Official Account ',
                    ),
                    TextSpan(
                      text: 'Zalo Bot Manager',
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                        color: AppTheme.textDark,
                      ),
                    ),
                    TextSpan(text: ', chọn '),
                    TextSpan(
                      text: 'Tạo bot',
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                        color: AppTheme.textDark,
                      ),
                    ),
                    TextSpan(
                      text:
                          '. Tên bot bắt buộc mở đầu bằng chữ "Bot". Token gửi về bằng tin nhắn Zalo.',
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 20),

              // Chat ID allowed field
              RichText(
                text: const TextSpan(
                  style: TextStyle(fontSize: 14, fontFamily: 'Inter'),
                  children: [
                    TextSpan(
                      text: 'Chat ID được phép dùng ',
                      style: TextStyle(
                        color: AppTheme.textMutedDark,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                    TextSpan(
                      text: '(nhập các ID được phép, cách nhau bằng dấu phẩy)',
                      style: TextStyle(color: Color(0xFF10B981), fontSize: 13),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: controller.zaloChatIdsController,
                style: const TextStyle(color: AppTheme.textDark, fontSize: 14),
                decoration: const InputDecoration(
                  hintText: 'Ví dụ: 123456789, 987654321',
                ),
              ),
              const SizedBox(height: 24),

              // Action buttons: Lưu & Bật / Gửi test
              Row(
                children: [
                  Obx(
                    () => ElevatedButton(
                      onPressed: controller.isSavingZalo.value
                          ? null
                          : controller.saveZalo,
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF252F42),
                        foregroundColor: AppTheme.textDark,
                        elevation: 0,
                        side: const BorderSide(color: Color(0xFF334155)),
                        minimumSize: const Size(64, 44),
                        padding: const EdgeInsets.symmetric(
                          horizontal: 20,
                          vertical: 12,
                        ),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(100),
                        ),
                      ),
                      child: controller.isSavingZalo.value
                          ? const SizedBox(
                              width: 16,
                              height: 16,
                              child: CircularProgressIndicator(
                                strokeWidth: 2,
                                color: Colors.white,
                              ),
                            )
                          : const Text(
                              'Lưu & bật',
                              style: TextStyle(fontWeight: FontWeight.w600),
                            ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Obx(
                    () => OutlinedButton(
                      onPressed: controller.isTestingZalo.value
                          ? null
                          : controller.testZalo,
                      style: OutlinedButton.styleFrom(
                        foregroundColor: AppTheme.textDark,
                        side: const BorderSide(color: Color(0xFF334155)),
                        minimumSize: const Size(64, 44),
                        padding: const EdgeInsets.symmetric(
                          horizontal: 20,
                          vertical: 12,
                        ),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(100),
                        ),
                      ),
                      child: controller.isTestingZalo.value
                          ? const SizedBox(
                              width: 16,
                              height: 16,
                              child: CircularProgressIndicator(
                                strokeWidth: 2,
                                color: Colors.white,
                              ),
                            )
                          : const Text(
                              'Gửi test',
                              style: TextStyle(fontWeight: FontWeight.w600),
                            ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),

              // Status message text
              Obx(() {
                final isEnabled = controller.zaloEnabled.value;
                if (!isEnabled) {
                  return const Text(
                    '○ Bot CHƯA bật - tích \'Bật bot Zalo\' rồi Lưu.',
                    style: TextStyle(
                      color: AppTheme.textMutedDark,
                      fontSize: 13,
                    ),
                  );
                }
                return const Text(
                  '● Bot Zalo ĐANG BẬT. Sẵn sàng nhận tin nhắn từ Zalo Bot Manager.',
                  style: TextStyle(
                    color: Color(0xFF10B981),
                    fontSize: 13,
                    fontWeight: FontWeight.w500,
                  ),
                );
              }),
            ],
          ),
        ),
      ],
    );
  }
}
