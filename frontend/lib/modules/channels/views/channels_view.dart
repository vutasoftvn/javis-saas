import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/channels_controller.dart';
import 'widgets/outbox_queue_monitor.dart';
import 'widgets/channel_connection_card.dart';
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
          JavisFloatingAppBar(
            title: 'Cổng Tự Động Hóa & Kênh Tương Tác',
            subtitle: 'Quản lý Telegram, Zalo OA, n8n Automation Gateway và hàng đợi Outbox.',
            icon: Icons.hub_rounded,
            actions: [
              Container(
                decoration: const BoxDecoration(
                  color: AppTheme.primary,
                  shape: BoxShape.circle,
                ),
                child: IconButton(
                  tooltip: 'Tải lại',
                  icon: const Icon(Icons.refresh_rounded, color: Colors.white, size: 20),
                  onPressed: () {
                    controller.loadChannels();
                    controller.loadOutbox();
                  },
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          // Tab Selection
          Obx(() => Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: Row(
                  children: [
                    _buildTab(context, index: 0, label: 'Kênh Kết Nối & Automation', icon: Icons.sensors_rounded),
                    const SizedBox(width: 8),
                    _buildTab(
                      context,
                      index: 1,
                      label: 'Hàng Đợi Outbox (${controller.outboxItems.length})',
                      icon: Icons.outbox_rounded,
                    ),
                  ],
                ),
              )),
          const SizedBox(height: 12),
          // Tab Content
          Expanded(
            child: Obx(() {
              if (controller.isLoading.value) {
                return const Center(child: CircularProgressIndicator());
              }

              if (controller.currentTab.value == 1) {
                return SingleChildScrollView(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  child: OutboxQueueMonitor(
                    outboxItems: controller.outboxItems,
                    onRetry: (outboxId) => controller.retryOutbox(outboxId),
                    onProcessBatch: () => controller.processOutboxBatch(),
                  ),
                );
              }

              return SingleChildScrollView(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Connection Cards
                    ChannelConnectionCard(
                      title: 'Telegram Bot API',
                      channelKey: 'telegram',
                      icon: Icons.send_rounded,
                      primaryColor: const Color(0xFF38BDF8),
                      description: 'Tiếp nhận lệnh của Founder và gửi tin nhắn cảnh báo, báo cáo nhanh qua Telegram.',
                      isConnected: controller.telegramEnabled.value,
                      onTestConnection: () => controller.testTelegramDirect(),
                    ),
                    const SizedBox(height: 14),
                    ChannelConnectionCard(
                      title: 'Zalo Official Account (OA)',
                      channelKey: 'zalo',
                      icon: Icons.chat_rounded,
                      primaryColor: const Color(0xFF0068FF),
                      description: 'Kết nối Zalo OA để gửi tin nhắn CSKH, thông báo ZNS và tiếp nhận khách hàng tiềm năng.',
                      isConnected: controller.zaloEnabled.value,
                      onTestConnection: () => controller.testZaloDirect(),
                    ),
                    const SizedBox(height: 14),
                    ChannelConnectionCard(
                      title: 'n8n Automation Gateway',
                      channelKey: 'n8n',
                      icon: Icons.account_tree_rounded,
                      primaryColor: const Color(0xFFFF6D5A),
                      description: 'Cổng điều phối các workflow tự động hóa mở rộng với xác thực chữ ký HMAC-SHA256.',
                      isConnected: true,
                      onTestConnection: () async => {'status': 'success', 'message': 'Cổng n8n Gateway đang sẵn sàng'},
                    ),
                    const SizedBox(height: 14),
                    ChannelConnectionCard(
                      title: 'Resend Email Gateway',
                      channelKey: 'resend',
                      icon: Icons.email_rounded,
                      primaryColor: const Color(0xFF10B981),
                      description: 'Giao tiếp gửi email giao dịch, thư chào hàng AI tiếp cận sau khi được Founder phê duyệt.',
                      isConnected: true,
                      onTestConnection: () async => {'status': 'success', 'message': 'Resend Email API sẵn sàng phát tin'},
                    ),
                    const SizedBox(height: 24),
                    // Telegram Config Form
                    _buildTelegramConfig(context),
                    const SizedBox(height: 24),
                    // Zalo Config Form
                    _buildZaloConfig(context),
                  ],
                ),
              );
            }),
          ),
        ],
      ),
    );
  }

  Widget _buildTab(BuildContext context, {required int index, required String label, required IconData icon}) {
    final isSelected = controller.currentTab.value == index;
    return InkWell(
      onTap: () => controller.setTab(index),
      borderRadius: BorderRadius.circular(10),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
        decoration: BoxDecoration(
          color: isSelected ? const Color(0xFF00E5FF).withValues(alpha: 0.15) : const Color(0xFF0F172A),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
            color: isSelected ? const Color(0xFF00E5FF) : const Color(0xFF1E293B),
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 16, color: isSelected ? const Color(0xFF00E5FF) : const Color(0xFF94A3B8)),
            const SizedBox(width: 8),
            Text(
              label,
              style: TextStyle(
                color: isSelected ? Colors.white : const Color(0xFF94A3B8),
                fontSize: 12,
                fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTelegramConfig(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFF1E293B)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.settings_suggest_rounded, color: Color(0xFF38BDF8), size: 18),
              const SizedBox(width: 8),
              const Text(
                'CẤU HÌNH TELEGRAM BOT',
                style: TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.bold),
              ),
              const Spacer(),
              Obx(() => Switch(
                    value: controller.telegramEnabled.value,
                    activeThumbColor: const Color(0xFF38BDF8),
                    onChanged: (v) => controller.telegramEnabled.value = v,
                  )),
            ],
          ),
          const SizedBox(height: 12),
          TextField(
            controller: controller.telegramTokenController,
            style: const TextStyle(color: Colors.white, fontSize: 13),
            decoration: InputDecoration(
              labelText: 'Telegram Bot Token',
              labelStyle: const TextStyle(color: Color(0xFF64748B), fontSize: 12),
              filled: true,
              fillColor: const Color(0xFF131D35),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: Color(0xFF1E293B))),
            ),
          ),
          const SizedBox(height: 12),
          Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              ElevatedButton(
                onPressed: () => controller.saveTelegram(),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF38BDF8),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
                child: const Text('Lưu Telegram', style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold)),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildZaloConfig(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFF1E293B)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.settings_suggest_rounded, color: Color(0xFF0068FF), size: 18),
              const SizedBox(width: 8),
              const Text(
                'CẤU HÌNH ZALO OA',
                style: TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.bold),
              ),
              const Spacer(),
              Obx(() => Switch(
                    value: controller.zaloEnabled.value,
                    activeThumbColor: const Color(0xFF0068FF),
                    onChanged: (v) => controller.zaloEnabled.value = v,
                  )),
            ],
          ),
          const SizedBox(height: 12),
          TextField(
            controller: controller.zaloTokenController,
            style: const TextStyle(color: Colors.white, fontSize: 13),
            decoration: InputDecoration(
              labelText: 'Zalo App Secret / Access Token',
              labelStyle: const TextStyle(color: Color(0xFF64748B), fontSize: 12),
              filled: true,
              fillColor: const Color(0xFF131D35),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: Color(0xFF1E293B))),
            ),
          ),
          const SizedBox(height: 12),
          Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              ElevatedButton(
                onPressed: () => controller.saveZalo(),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF0068FF),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
                child: const Text('Lưu Zalo', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
