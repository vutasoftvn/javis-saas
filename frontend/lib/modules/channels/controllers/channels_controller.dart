import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../data/services/channels_service.dart';
import '../../../data/services/outbox_service.dart';

class ChannelsController extends GetxController {
  final ChannelsService _channelsService = ChannelsService();
  final OutboxService _outboxService = OutboxService();

  final currentTab = 0.obs;
  final isLoading = false.obs;
  final isSavingTelegram = false.obs;
  final isTestingTelegram = false.obs;
  final isSavingZalo = false.obs;
  final isTestingZalo = false.obs;

  // Outbox state
  final outboxItems = <dynamic>[].obs;
  final isLoadingOutbox = false.obs;

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
    loadOutbox();
  }

  @override
  void onClose() {
    telegramTokenController.dispose();
    telegramChatIdsController.dispose();
    zaloTokenController.dispose();
    zaloChatIdsController.dispose();
    super.onClose();
  }

  void setTab(int index) {
    currentTab.value = index;
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

  Future<void> loadOutbox() async {
    isLoadingOutbox.value = true;
    try {
      final items = await _outboxService.getOutboxItems();
      outboxItems.assignAll(items);
    } finally {
      isLoadingOutbox.value = false;
    }
  }

  Future<void> retryOutbox(String outboxId) async {
    final res = await _outboxService.retryOutbox(outboxId);
    if (res != null) {
      Get.snackbar(
        'Đã gửi lại',
        'Tác vụ Outbox $outboxId đang được xử lý phát tin.',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: const Color(0xFF0F172A),
        colorText: Colors.white,
      );
      await loadOutbox();
    }
  }

  Future<void> processOutboxBatch() async {
    final res = await _outboxService.processBatch();
    if (res != null) {
      Get.snackbar(
        'Hoàn tất xử lý hàng đợi',
        'Đã phát ${res['success_count']} tin nhắn thành công.',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: const Color(0xFF0F172A),
        colorText: Colors.white,
      );
      await loadOutbox();
    }
  }

  Future<Map<String, dynamic>?> testTelegramDirect() async {
    final token = telegramTokenController.text.trim();
    if (token.isEmpty) {
      return {'status': 'error', 'message': 'Vui lòng nhập Bot Token trước'};
    }
    return await _outboxService.testTelegram(token);
  }

  Future<Map<String, dynamic>?> testZaloDirect() async {
    final token = zaloTokenController.text.trim();
    if (token.isEmpty) {
      return {'status': 'error', 'message': 'Vui lòng nhập Zalo App Secret / Token trước'};
    }
    return await _outboxService.testZalo('zalo_app_default', token);
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
          res['message'] ?? 'Đã lưu và kích hoạt Telegram Bot',
          snackPosition: SnackPosition.BOTTOM,
          backgroundColor: Colors.green.withValues(alpha: 0.9),
          colorText: Colors.white,
        );
      } else {
        final errMsg = res['message'] ?? 'Lưu thất bại. Vui lòng kiểm tra lại token.';
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
        Get.snackbar(
          'Lỗi thử nghiệm',
          res['message'] ?? 'Gửi thử nghiệm thất bại.',
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
        final errMsg = res['message'] ?? 'Lưu thất bại. Vui lòng kiểm tra lại token Zalo.';
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
        Get.snackbar(
          'Lỗi thử nghiệm',
          res['message'] ?? 'Gửi thử nghiệm thất bại.',
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
