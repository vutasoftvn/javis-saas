import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../data/services/channels_service.dart';

class ChannelsController extends GetxController {
  final ChannelsService _channelsService = ChannelsService();

  final isLoading = false.obs;
  final isSavingTelegram = false.obs;
  final isTestingTelegram = false.obs;
  final isSavingZalo = false.obs;
  final isTestingZalo = false.obs;

  // Telegram state
  final telegramEnabled = false.obs;
  final telegramTokenController = TextEditingController();
  final telegramChatIdsController = TextEditingController();
  final telegramObscureToken = true.obs;
  final telegramStatus = 'off'.obs;
  final telegramBotUsername = ''.obs;
  final telegramErrorMsg = ''.obs;

  // Zalo state
  final zaloEnabled = false.obs;
  final zaloTokenController = TextEditingController();
  final zaloChatIdsController = TextEditingController();
  final zaloObscureToken = true.obs;
  final zaloStatus = 'off'.obs;
  final zaloErrorMsg = ''.obs;

  @override
  void onInit() {
    super.onInit();
    loadChannels();
  }

  @override
  void onClose() {
    telegramTokenController.dispose();
    telegramChatIdsController.dispose();
    zaloTokenController.dispose();
    zaloChatIdsController.dispose();
    super.onClose();
  }

  Future<void> loadChannels() async {
    isLoading.value = true;
    try {
      final res = await _channelsService.getChannelsConfig();
      if (res.isNotEmpty) {
        if (res.containsKey('telegram')) {
          final tg = res['telegram'] as Map<String, dynamic>;
          telegramEnabled.value = tg['is_enabled'] ?? false;
          telegramTokenController.text = tg['bot_token'] ?? '';
          telegramChatIdsController.text = tg['allowed_chat_ids'] ?? '';
          telegramStatus.value = tg['status'] ?? 'off';
          telegramBotUsername.value = tg['bot_username'] ?? '';
          telegramErrorMsg.value = tg['last_error'] ?? '';
        }

        if (res.containsKey('zalo')) {
          final zl = res['zalo'] as Map<String, dynamic>;
          zaloEnabled.value = zl['is_enabled'] ?? false;
          zaloTokenController.text = zl['bot_token'] ?? '';
          zaloChatIdsController.text = zl['allowed_chat_ids'] ?? '';
          zaloStatus.value = zl['status'] ?? 'off';
          zaloErrorMsg.value = zl['last_error'] ?? '';
        }
      }
    } catch (e) {
      Get.snackbar(
        'Lỗi',
        'Không thể nạp cấu hình kênh: $e',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: Colors.red.withValues(alpha: 0.8),
        colorText: Colors.white,
      );
    } finally {
      isLoading.value = false;
    }
  }

  Future<void> saveTelegram() async {
    isSavingTelegram.value = true;
    telegramEnabled.value = true;
    try {
      final res = await _channelsService.saveTelegramChannel(
        isEnabled: telegramEnabled.value,
        botToken: telegramTokenController.text.trim(),
        allowedChatIds: telegramChatIdsController.text.trim(),
      );

      if (res['status'] == 'success') {
        telegramStatus.value = 'running';
        if (res.containsKey('bot_username') &&
            (res['bot_username'] as String).isNotEmpty) {
          telegramBotUsername.value = res['bot_username'] ?? '';
        }
        Get.snackbar(
          'Thành công',
          res['message'] ?? 'Đã lưu và bật cấu hình Telegram thành công',
          snackPosition: SnackPosition.BOTTOM,
          backgroundColor: Colors.green.withValues(alpha: 0.9),
          colorText: Colors.white,
        );
      } else {
        final errMsg =
            res['message'] ?? 'Lưu thất bại. Vui lòng kiểm tra lại token.';
        Get.snackbar(
          'Lỗi lưu Telegram',
          errMsg,
          snackPosition: SnackPosition.BOTTOM,
          backgroundColor: Colors.orange.withValues(alpha: 0.9),
          colorText: Colors.white,
        );
      }
    } catch (e) {
      Get.snackbar(
        'Lỗi',
        'Lưu Telegram thất bại: $e',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: Colors.red.withValues(alpha: 0.8),
        colorText: Colors.white,
      );
    } finally {
      isSavingTelegram.value = false;
    }
  }

  Future<void> testTelegram() async {
    isTestingTelegram.value = true;
    try {
      // 1. Tự động lưu & bật bot Telegram trước khi gửi test
      final saveRes = await _channelsService.saveTelegramChannel(
        isEnabled: true,
        botToken: telegramTokenController.text.trim(),
        allowedChatIds: telegramChatIdsController.text.trim(),
      );

      if (saveRes['status'] != 'success') {
        Get.snackbar(
          'Lỗi thử nghiệm',
          saveRes['message'] ?? 'Không thể lưu token Telegram',
          snackPosition: SnackPosition.BOTTOM,
          backgroundColor: Colors.orange.withValues(alpha: 0.9),
          colorText: Colors.white,
        );
        return;
      }

      telegramEnabled.value = true;
      telegramStatus.value = 'running';

      await loadChannels();

      final res = await _channelsService.testTelegramChannel();
      if (res['status'] == 'success') {
        Get.snackbar(
          'Thử nghiệm thành công',
          res['message'] ?? 'Đã gửi tin thử nghiệm tới Telegram',
          snackPosition: SnackPosition.BOTTOM,
          backgroundColor: Colors.blue.withValues(alpha: 0.9),
          colorText: Colors.white,
        );
      } else {
        final errMsg =
            res['message'] ??
            'Gửi thử nghiệm thất bại. Vui lòng kiểm tra Chat ID & Token';
        Get.snackbar(
          'Lỗi thử nghiệm',
          errMsg,
          snackPosition: SnackPosition.BOTTOM,
          backgroundColor: Colors.orange.withValues(alpha: 0.9),
          colorText: Colors.white,
        );
      }
    } catch (e) {
      Get.snackbar(
        'Lỗi',
        'Không gửi được tin thử nghiệm: $e',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: Colors.red.withValues(alpha: 0.8),
        colorText: Colors.white,
      );
    } finally {
      isTestingTelegram.value = false;
    }
  }

  Future<void> saveZalo() async {
    isSavingZalo.value = true;
    zaloEnabled.value = true;
    try {
      final res = await _channelsService.saveZaloChannel(
        isEnabled: zaloEnabled.value,
        botToken: zaloTokenController.text.trim(),
        allowedChatIds: zaloChatIdsController.text.trim(),
      );

      if (res['status'] == 'success') {
        zaloStatus.value = 'running';
        Get.snackbar(
          'Thành công',
          res['message'] ?? 'Đã lưu và bật cấu hình Zalo thành công',
          snackPosition: SnackPosition.BOTTOM,
          backgroundColor: Colors.green.withValues(alpha: 0.9),
          colorText: Colors.white,
        );
      } else {
        final errMsg =
            res['message'] ?? 'Lưu thất bại. Vui lòng kiểm tra lại token Zalo.';
        Get.snackbar(
          'Lỗi lưu Zalo',
          errMsg,
          snackPosition: SnackPosition.BOTTOM,
          backgroundColor: Colors.orange.withValues(alpha: 0.9),
          colorText: Colors.white,
        );
      }
    } catch (e) {
      Get.snackbar(
        'Lỗi',
        'Lưu Zalo thất bại: $e',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: Colors.red.withValues(alpha: 0.8),
        colorText: Colors.white,
      );
    } finally {
      isSavingZalo.value = false;
    }
  }

  Future<void> testZalo() async {
    isTestingZalo.value = true;
    try {
      // 1. Tự động lưu & bật bot Zalo trước khi test
      final saveRes = await _channelsService.saveZaloChannel(
        isEnabled: true,
        botToken: zaloTokenController.text.trim(),
        allowedChatIds: zaloChatIdsController.text.trim(),
      );

      if (saveRes['status'] != 'success') {
        Get.snackbar(
          'Lỗi thử nghiệm',
          saveRes['message'] ?? 'Không thể lưu token Zalo',
          snackPosition: SnackPosition.BOTTOM,
          backgroundColor: Colors.orange.withValues(alpha: 0.9),
          colorText: Colors.white,
        );
        return;
      }

      zaloEnabled.value = true;
      zaloStatus.value = 'running';

      // 2. Load lại để đồng bộ cấu hình đã lưu
      await loadChannels();

      // 3. Tiến hành gửi test
      final res = await _channelsService.testZaloChannel();
      if (res['status'] == 'success') {
        Get.snackbar(
          'Thử nghiệm thành công',
          res['message'] ?? 'Đã gửi tin thử nghiệm tới Zalo',
          snackPosition: SnackPosition.BOTTOM,
          backgroundColor: Colors.blue.withValues(alpha: 0.9),
          colorText: Colors.white,
        );
      } else {
        final errMsg = res['message'] ?? 'Gửi thử nghiệm thất bại.';
        Get.snackbar(
          'Lỗi thử nghiệm',
          errMsg,
          snackPosition: SnackPosition.BOTTOM,
          backgroundColor: Colors.orange.withValues(alpha: 0.9),
          colorText: Colors.white,
        );
      }
    } catch (e) {
      Get.snackbar(
        'Lỗi',
        'Không gửi được tin thử nghiệm: $e',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: Colors.red.withValues(alpha: 0.8),
        colorText: Colors.white,
      );
    } finally {
      isTestingZalo.value = false;
    }
  }
}
