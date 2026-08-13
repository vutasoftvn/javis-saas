import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/chatbots_controller.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/theme/glassmorphism.dart';

class ChatbotsView extends GetView<ChatbotsController> {
  const ChatbotsView({super.key});

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<ChatbotsController>()) {
      Get.put(ChatbotsController());
    }

    return Scaffold(
      backgroundColor: Colors.transparent,
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(28.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Top Header: Title & Action
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    const Icon(
                      Icons.headset_mic_rounded,
                      color: AppTheme.primaryLight,
                      size: 28,
                    ),
                    const SizedBox(width: 12),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: const [
                        Text(
                          'Chatbot',
                          style: TextStyle(
                            fontSize: 24,
                            fontWeight: FontWeight.bold,
                            color: AppTheme.textDark,
                          ),
                        ),
                        SizedBox(height: 2),
                        Text(
                          'Bot chuyên trách trả lời khách qua Telegram & Zalo',
                          style: TextStyle(
                            fontSize: 14,
                            color: AppTheme.textMutedDark,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
                ElevatedButton.icon(
                  onPressed: () => _openBotFormDialog(context, null),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.primary,
                    foregroundColor: const Color(0xFF04070E),
                    minimumSize: const Size(64, 44),
                    padding: const EdgeInsets.symmetric(
                      horizontal: 18,
                      vertical: 12,
                    ),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(100),
                    ),
                  ),
                  icon: const Icon(Icons.add_rounded, size: 20),
                  label: const Text(
                    'Bot mới',
                    style: TextStyle(fontWeight: FontWeight.bold),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 24),

            // Search Bar
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
              decoration: BoxDecoration(
                color: AppTheme.surfaceDark.withValues(alpha: 0.6),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
              ),
              child: TextField(
                onChanged: (val) => controller.searchQuery.value = val.trim(),
                style: const TextStyle(color: AppTheme.textDark, fontSize: 14),
                decoration: const InputDecoration(
                  icon: Icon(
                    Icons.search_rounded,
                    color: AppTheme.textMutedDark,
                    size: 20,
                  ),
                  hintText: 'Tìm bot theo tên hoặc username...',
                  hintStyle: TextStyle(
                    color: AppTheme.textMutedDark,
                    fontSize: 14,
                  ),
                  border: InputBorder.none,
                ),
              ),
            ),
            const SizedBox(height: 16),

            // Intro Explanatory Banner (Matching javis-os)
            Glassmorphism(
              blur: 15,
              opacity: 0.1,
              color: AppTheme.surfaceDark,
              borderRadius: BorderRadius.circular(12),
              child: Container(
                width: double.infinity,
                padding: const EdgeInsets.all(18),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: Colors.white.withValues(alpha: 0.05),
                  ),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Bot của workspace. Mỗi bot là một Agent trong workspace này, đem ra trả lời người ngoài qua một bot nhắn tin riêng trên Telegram hoặc Zalo. Bot làm theo đúng quy định trong file Agent.',
                      style: TextStyle(
                        fontSize: 13,
                        color: AppTheme.textMutedDark.withValues(alpha: 0.9),
                        height: 1.5,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      'Mặc định nó chỉ đọc được workspace này: không ghi, không gọi nguồn dữ liệu, không có lệnh quản trị. Hàng rào giữ nguyên ở MỌI mức: bot không thấy workspace khác và không chạy được lệnh máy.',
                      style: TextStyle(
                        fontSize: 13,
                        color: AppTheme.textMutedDark.withValues(alpha: 0.7),
                        height: 1.5,
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 24),

            // Channel Filter Chips
            Obx(() {
              final tgCount = controller.chatbots
                  .where(
                    (b) =>
                        (b['channel'] ?? '').toString().toLowerCase() ==
                        'telegram',
                  )
                  .length;
              final zaloCount = controller.chatbots
                  .where(
                    (b) =>
                        (b['channel'] ?? '').toString().toLowerCase() == 'zalo',
                  )
                  .length;
              final totalCount = controller.chatbots.length;

              return SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: [
                    _buildFilterChip('Tất cả', '', totalCount),
                    const SizedBox(width: 8),
                    _buildFilterChip(
                      'Telegram',
                      'telegram',
                      tgCount,
                      icon: Icons.send_rounded,
                    ),
                    const SizedBox(width: 8),
                    _buildFilterChip(
                      'Zalo',
                      'zalo',
                      zaloCount,
                      icon: Icons.chat_bubble_outline_rounded,
                    ),
                  ],
                ),
              );
            }),
            const SizedBox(height: 24),

            // Chatbots Grid / Cards List
            Obx(() {
              if (controller.isLoading.value) {
                return const Padding(
                  padding: EdgeInsets.symmetric(vertical: 40),
                  child: Center(child: CircularProgressIndicator()),
                );
              }

              final bots = controller.filteredChatbots;

              if (bots.isEmpty) {
                return _buildEmptyState(context);
              }

              return LayoutBuilder(
                builder: (context, constraints) {
                  final crossAxisCount = constraints.maxWidth > 900 ? 2 : 1;
                  return GridView.builder(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisCount: crossAxisCount,
                      crossAxisSpacing: 16,
                      mainAxisSpacing: 16,
                      mainAxisExtent: 250,
                    ),
                    itemCount: bots.length,
                    itemBuilder: (context, index) {
                      final bot = bots[index] as Map<String, dynamic>;
                      return _buildBotCard(context, bot);
                    },
                  );
                },
              );
            }),
          ],
        ),
      ),
    );
  }

  Widget _buildFilterChip(
    String label,
    String value,
    int count, {
    IconData? icon,
  }) {
    final isSelected = controller.selectedChannelFilter.value == value;
    return ChoiceChip(
      avatar: icon != null
          ? Icon(
              icon,
              size: 14,
              color: isSelected
                  ? AppTheme.primaryLight
                  : AppTheme.textMutedDark,
            )
          : null,
      label: Text('$label ($count)'),
      selected: isSelected,
      selectedColor: AppTheme.primary.withValues(alpha: 0.3),
      backgroundColor: AppTheme.surfaceDark.withValues(alpha: 0.5),
      labelStyle: TextStyle(
        color: isSelected ? AppTheme.primaryLight : AppTheme.textMutedDark,
        fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
        fontSize: 13,
      ),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(20),
        side: BorderSide(
          color: isSelected
              ? AppTheme.primaryLight.withValues(alpha: 0.5)
              : Colors.white.withValues(alpha: 0.05),
        ),
      ),
      onSelected: (selected) {
        if (selected) {
          controller.selectedChannelFilter.value = value;
        }
      },
    );
  }

  Widget _buildEmptyState(BuildContext context) {
    return Center(
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(vertical: 48, horizontal: 24),
        decoration: BoxDecoration(
          color: AppTheme.surfaceDark.withValues(alpha: 0.3),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.white.withValues(alpha: 0.05)),
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppTheme.primary.withValues(alpha: 0.1),
                shape: BoxShape.circle,
              ),
              child: const Icon(
                Icons.smart_toy_outlined,
                size: 48,
                color: AppTheme.primaryLight,
              ),
            ),
            const SizedBox(height: 20),
            const Text(
              'Chưa có bot nào',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
                color: AppTheme.textDark,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Tạo một bot để Agent của bạn đứng ra trả lời người ngoài. Bot mới luôn ở trạng thái tắt, bạn tự bật sau khi đã nhắn thử.',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 14,
                color: AppTheme.textMutedDark.withValues(alpha: 0.8),
                height: 1.4,
              ),
            ),
            const SizedBox(height: 24),
            ElevatedButton.icon(
              onPressed: () => _openBotFormDialog(context, null),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.primary,
                foregroundColor: const Color(0xFF04070E),
                padding: const EdgeInsets.symmetric(
                  horizontal: 20,
                  vertical: 12,
                ),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(10),
                ),
              ),
              icon: const Icon(Icons.add_rounded, size: 18),
              label: const Text(
                'Tạo bot đầu tiên',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildBotCard(BuildContext context, Map<String, dynamic> bot) {
    final channel = (bot['channel'] ?? 'telegram').toString().toLowerCase();
    final isEnabled = bot['is_enabled'] == true || bot['status'] == 'running';
    final botName = bot['name'] ?? '${channel.toUpperCase()} Bot';
    final botUsername = (bot['bot_username'] ?? '').toString();
    final allowedChatIds = (bot['allowed_chat_ids'] ?? '').toString();
    final isZalo = channel == 'zalo';

    return Glassmorphism(
      blur: 20,
      opacity: 0.15,
      color: AppTheme.surfaceDark,
      borderRadius: BorderRadius.circular(16),
      child: Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header: Icon + Name + Status Indicator
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: isZalo
                        ? Colors.blue.withValues(alpha: 0.2)
                        : const Color(0xFF0088CC).withValues(alpha: 0.2),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Icon(
                    isZalo
                        ? Icons.chat_bubble_outline_rounded
                        : Icons.send_rounded,
                    color: isZalo ? Colors.blueAccent : const Color(0xFF0088CC),
                    size: 22,
                  ),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        botName,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                          color: AppTheme.textDark,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Row(
                        children: [
                          Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 6,
                              vertical: 2,
                            ),
                            decoration: BoxDecoration(
                              color: isZalo
                                  ? Colors.blue.withValues(alpha: 0.15)
                                  : const Color(
                                      0xFF0088CC,
                                    ).withValues(alpha: 0.15),
                              borderRadius: BorderRadius.circular(6),
                            ),
                            child: Text(
                              isZalo ? 'ZALO BOT' : 'TELEGRAM',
                              style: TextStyle(
                                fontSize: 10,
                                fontWeight: FontWeight.bold,
                                color: isZalo
                                    ? Colors.blueAccent
                                    : const Color(0xFF0088CC),
                              ),
                            ),
                          ),
                          if (botUsername.isNotEmpty) ...[
                            const SizedBox(width: 8),
                            Text(
                              isZalo ? botUsername : '@$botUsername',
                              style: const TextStyle(
                                fontSize: 12,
                                color: AppTheme.textMutedDark,
                              ),
                            ),
                          ],
                        ],
                      ),
                    ],
                  ),
                ),

                // Status Badge Dot
                Row(
                  children: [
                    Container(
                      width: 8,
                      height: 8,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: isEnabled
                            ? AppTheme.success
                            : AppTheme.textMutedDark,
                      ),
                    ),
                    const SizedBox(width: 6),
                    Text(
                      isEnabled ? 'Đang chạy' : 'Đã tắt',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                        color: isEnabled
                            ? AppTheme.success
                            : AppTheme.textMutedDark,
                      ),
                    ),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 14),

            // Meta Info: Permissions & Allowed Chat IDs
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.03),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                children: const [
                  Icon(
                    Icons.remove_red_eye_outlined,
                    size: 14,
                    color: AppTheme.textMutedDark,
                  ),
                  SizedBox(width: 6),
                  Text(
                    'Mức Chỉ đọc - bot chỉ đọc workspace này rồi trả lời',
                    style: TextStyle(
                      fontSize: 12,
                      color: AppTheme.textMutedDark,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 8),
            Text(
              allowedChatIds.isNotEmpty
                  ? 'Chat ID cho phép: $allowedChatIds'
                  : 'Chưa cấu hình Chat ID được phép; bot sẽ không phản hồi',
              style: TextStyle(
                fontSize: 12,
                color: allowedChatIds.isNotEmpty
                    ? Colors.blueAccent
                    : AppTheme.textMutedDark.withValues(alpha: 0.7),
              ),
            ),
            const Spacer(),

            // Actions Bar
            Row(
              children: [
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: () => controller.toggleBot(bot),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: isEnabled
                          ? AppTheme.surfaceDark
                          : AppTheme.primary.withValues(alpha: 0.2),
                      foregroundColor: isEnabled
                          ? AppTheme.textDark
                          : AppTheme.primaryLight,
                      minimumSize: const Size(64, 40),
                      padding: const EdgeInsets.symmetric(vertical: 10),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(100),
                        side: BorderSide(
                          color: isEnabled
                              ? Colors.white.withValues(alpha: 0.1)
                              : AppTheme.primary.withValues(alpha: 0.4),
                        ),
                      ),
                    ),
                    icon: Icon(
                      isEnabled
                          ? Icons.pause_circle_outline_rounded
                          : Icons.play_arrow_rounded,
                      size: 16,
                    ),
                    label: Text(
                      isEnabled ? 'Tắt bot' : 'Bật bot',
                      style: const TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                IconButton(
                  icon: const Icon(
                    Icons.send_outlined,
                    color: Colors.blueAccent,
                    size: 20,
                  ),
                  tooltip: 'Thử nghiệm gửi tin nhắn',
                  onPressed: () => controller.testBot(bot),
                ),
                IconButton(
                  icon: const Icon(
                    Icons.settings_outlined,
                    color: AppTheme.textMutedDark,
                    size: 20,
                  ),
                  tooltip: 'Sửa cấu hình Token',
                  onPressed: () => _openBotFormDialog(context, bot),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  // --- Modal Form: [+ Bot mới / Cấu hình Bot] ---
  void _openBotFormDialog(BuildContext context, Map<String, dynamic>? bot) {
    final isEdit = bot != null;
    final channelRx = (bot?['channel'] ?? 'zalo').toString().toLowerCase().obs;
    final tokenCtrl = TextEditingController(
      text: (bot?['bot_token'] ?? '').toString(),
    );
    final chatIdsCtrl = TextEditingController(
      text: (bot?['allowed_chat_ids'] ?? '').toString(),
    );
    final isEnabledRx =
        (bot?['is_enabled'] == true || bot?['status'] == 'running').obs;

    Get.dialog(
      AlertDialog(
        backgroundColor: const Color(0xFF0F172A),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: BorderSide(color: Colors.white.withValues(alpha: 0.1)),
        ),
        title: Row(
          children: [
            const Icon(
              Icons.smart_toy_outlined,
              color: AppTheme.primaryLight,
              size: 24,
            ),
            const SizedBox(width: 10),
            Text(
              isEdit ? 'Cấu hình Chatbot' : 'Thêm Bot mới',
              style: const TextStyle(
                color: Colors.white,
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
        ),
        content: SizedBox(
          width: 440,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Segmented Channel Picker
              const Text(
                'Chọn kênh Bot:',
                style: TextStyle(color: AppTheme.textMutedDark, fontSize: 13),
              ),
              const SizedBox(height: 8),
              Obx(() {
                return Row(
                  children: [
                    Expanded(
                      child: ChoiceChip(
                        avatar: const Icon(
                          Icons.chat_bubble_outline_rounded,
                          size: 16,
                          color: Colors.blueAccent,
                        ),
                        label: const Center(child: Text('Zalo Bot')),
                        selected: channelRx.value == 'zalo',
                        selectedColor: Colors.blue.withValues(alpha: 0.3),
                        backgroundColor: AppTheme.surfaceDark,
                        labelStyle: TextStyle(
                          color: channelRx.value == 'zalo'
                              ? Colors.blueAccent
                              : AppTheme.textMutedDark,
                          fontWeight: FontWeight.bold,
                        ),
                        onSelected: isEdit
                            ? null
                            : (_) => channelRx.value = 'zalo',
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: ChoiceChip(
                        avatar: const Icon(
                          Icons.send_rounded,
                          size: 16,
                          color: Color(0xFF0088CC),
                        ),
                        label: const Center(child: Text('Telegram')),
                        selected: channelRx.value == 'telegram',
                        selectedColor: const Color(
                          0xFF0088CC,
                        ).withValues(alpha: 0.3),
                        backgroundColor: AppTheme.surfaceDark,
                        labelStyle: TextStyle(
                          color: channelRx.value == 'telegram'
                              ? const Color(0xFF0088CC)
                              : AppTheme.textMutedDark,
                          fontWeight: FontWeight.bold,
                        ),
                        onSelected: isEdit
                            ? null
                            : (_) => channelRx.value = 'telegram',
                      ),
                    ),
                  ],
                );
              }),
              const SizedBox(height: 20),

              // Bot Token Field
              Obx(() {
                final isZalo = channelRx.value == 'zalo';
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      isZalo
                          ? 'Bot Access Token (Zalo Bot Manager):'
                          : 'Bot Token Telegram (từ @BotFather):',
                      style: const TextStyle(
                        color: AppTheme.textDark,
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 6),
                    TextField(
                      controller: tokenCtrl,
                      style: const TextStyle(color: Colors.white, fontSize: 14),
                      decoration: InputDecoration(
                        hintText: isZalo
                            ? 'Ví dụ: YxpIzY...'
                            : 'Ví dụ: 123456789:ABCdef...',
                        hintStyle: const TextStyle(
                          color: AppTheme.textMutedDark,
                          fontSize: 13,
                        ),
                        filled: true,
                        fillColor: AppTheme.surfaceDark,
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(10),
                          borderSide: BorderSide.none,
                        ),
                      ),
                    ),
                  ],
                );
              }),
              const SizedBox(height: 16),

              // Allowed Chat IDs Field
              const Text(
                'Allowed Chat IDs (Bắt buộc để bot phản hồi):',
                style: TextStyle(
                  color: AppTheme.textDark,
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 6),
              TextField(
                controller: chatIdsCtrl,
                style: const TextStyle(color: Colors.white, fontSize: 14),
                decoration: InputDecoration(
                  hintText: 'Ví dụ: 123456789, 987654321',
                  hintStyle: const TextStyle(
                    color: AppTheme.textMutedDark,
                    fontSize: 13,
                  ),
                  filled: true,
                  fillColor: AppTheme.surfaceDark,
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(10),
                    borderSide: BorderSide.none,
                  ),
                ),
              ),
              const SizedBox(height: 16),

              // Enable Switch
              Obx(() {
                return Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text(
                      'Bật bot trả lời tự động:',
                      style: TextStyle(color: AppTheme.textDark, fontSize: 14),
                    ),
                    Switch(
                      value: isEnabledRx.value,
                      onChanged: (val) => isEnabledRx.value = val,
                      activeThumbColor: AppTheme.success,
                    ),
                  ],
                );
              }),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Get.back(),
            child: const Text(
              'Hủy',
              style: TextStyle(color: AppTheme.textMutedDark),
            ),
          ),
          Obx(() {
            return ElevatedButton(
              onPressed: controller.isSaving.value
                  ? null
                  : () {
                      controller.saveBotConfig(
                        channel: channelRx.value,
                        token: tokenCtrl.text,
                        allowedChatIds: chatIdsCtrl.text,
                        isEnabled: isEnabledRx.value,
                      );
                    },
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.primary,
                foregroundColor: const Color(0xFF04070E),
              ),
              child: controller.isSaving.value
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Text('Lưu bot'),
            );
          }),
        ],
      ),
    );
  }
}
