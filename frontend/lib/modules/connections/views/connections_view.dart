import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/connections_controller.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/theme/glassmorphism.dart';
import '../../../core/widgets/floating_app_bar.dart';

class ConnectionsView extends GetView<ConnectionsController> {
  const ConnectionsView({super.key});

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<ConnectionsController>()) {
      Get.put(ConnectionsController());
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const JavisFloatingAppBar(
          title: 'Kết nối Dữ liệu',
          subtitle: 'Nguồn dữ liệu, công cụ & tích hợp hệ thống',
          icon: Icons.power_rounded,
        ),
        const SizedBox(height: 12),
        Expanded(
          child: SingleChildScrollView(
            padding: EdgeInsets.zero,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: 12),

            // --- SECTION 1: ĐÃ KẾT NỐI ---
            _buildConnectedSection(context),

            const SizedBox(height: 36),

            // --- SECTION 2: KHO KẾT NỐI (CATALOG) ---
            _buildCatalogSection(context),
              ],
            ),
          ),
        ),
      ],
    );
  }

  // --- SECTION 1: ĐÃ KẾT NỐI ---
  Widget _buildConnectedSection(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Obx(() {
          final count = controller.connectors.length;
          return Row(
            children: [
              const Icon(Icons.hub_outlined, color: AppTheme.primaryLight, size: 18),
              const SizedBox(width: 8),
              Text(
                'ĐÃ KẾT NỐI ($count TÀI KHOẢN)',
                style: const TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                  letterSpacing: 0.8,
                  color: AppTheme.textDark,
                ),
              ),
            ],
          );
        }),
        const SizedBox(height: 8),
        Text(
          'Một dịch vụ nối được NHIỀU tài khoản (nhiều shop, nhiều số Zalo...). '
          'Mọi bộ não - Claude Code, ChatGPT/Codex, OpenRouter, API - dùng chung kho này qua trung tâm kết nối của Javis.',
          style: TextStyle(
            fontSize: 13,
            color: AppTheme.textMutedDark.withValues(alpha: 0.8),
            height: 1.4,
          ),
        ),
        const SizedBox(height: 16),

        Obx(() {
          if (controller.isLoading.value) {
            return const Padding(
              padding: EdgeInsets.symmetric(vertical: 20),
              child: Center(child: CircularProgressIndicator()),
            );
          }

          if (controller.connectors.isEmpty) {
            return _buildEmptyConnectedState();
          }

          return ListView.separated(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: controller.connectors.length,
            separatorBuilder: (context, index) => const SizedBox(height: 12),
            itemBuilder: (context, index) {
              final conn = controller.connectors[index];
              return _buildConnectedCard(context, conn);
            },
          );
        }),
      ],
    );
  }

  Widget _buildEmptyConnectedState() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDark.withValues(alpha: 0.3),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.white.withValues(alpha: 0.05)),
      ),
      child: const Text(
        'Chưa có tài khoản nào được kết nối. Bạn hãy bấm "Kết nối" ở danh sách bên dưới để bắt đầu.',
        style: TextStyle(color: AppTheme.textMutedDark, fontSize: 13),
      ),
    );
  }

  Widget _buildConnectedCard(BuildContext context, Map<String, dynamic> conn) {
    final isConnected = conn['status'] == 'connected' || conn['status'] == 'active' || conn['status'] == 'ready';
    return Glassmorphism(
      blur: 15,
      opacity: 0.1,
      color: AppTheme.surfaceDark,
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Colors.white.withValues(alpha: 0.05)),
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: AppTheme.primary.withValues(alpha: 0.2),
                borderRadius: BorderRadius.circular(10),
              ),
              child: const Icon(Icons.extension_rounded, color: AppTheme.primaryLight, size: 24),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    conn['name'] ?? 'Không tên',
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
                        width: 8,
                        height: 8,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: isConnected ? AppTheme.success : AppTheme.error,
                        ),
                      ),
                      const SizedBox(width: 6),
                      Text(
                        isConnected ? 'Đã kết nối' : 'Lỗi kết nối',
                        style: TextStyle(
                          fontSize: 13,
                          color: isConnected ? AppTheme.success : AppTheme.error,
                        ),
                      ),
                      const SizedBox(width: 16),
                      Text(
                        'ID: ${conn['id']}',
                        style: const TextStyle(fontSize: 12, color: AppTheme.textMutedDark),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            IconButton(
              icon: const Icon(Icons.delete_outline_rounded, color: AppTheme.error, size: 20),
              tooltip: 'Ngắt kết nối',
              onPressed: () => _confirmDelete(context, conn['id']),
            ),
          ],
        ),
      ),
    );
  }

  // --- SECTION 2: KHO KẾT NỐI (CATALOG) ---
  Widget _buildCatalogSection(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: const [
            Icon(Icons.storefront_outlined, color: AppTheme.primaryLight, size: 18),
            SizedBox(width: 8),
            Text(
              'KHO KẾT NỐI',
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.bold,
                letterSpacing: 0.8,
                color: AppTheme.textDark,
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),

        // Filter chips
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: Obx(() {
            return Row(
              children: controller.categories.map((cat) {
                final isSelected = controller.selectedCategory.value == cat;
                return Padding(
                  padding: const EdgeInsets.only(right: 8.0),
                  child: ChoiceChip(
                    label: Text(cat),
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
                        controller.selectedCategory.value = cat;
                      }
                    },
                  ),
                );
              }).toList(),
            );
          }),
        ),
        const SizedBox(height: 20),

        // Catalog Grid Cards
        Obx(() {
          final items = controller.filteredCatalog;
          return LayoutBuilder(
            builder: (context, constraints) {
              final crossAxisCount = constraints.maxWidth > 900 ? 3 : (constraints.maxWidth > 600 ? 2 : 1);
              return GridView.builder(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: crossAxisCount,
                  crossAxisSpacing: 16,
                  mainAxisSpacing: 16,
                  mainAxisExtent: 230,
                ),
                itemCount: items.length,
                itemBuilder: (context, index) {
                  return _buildCatalogCard(context, items[index]);
                },
              );
            },
          );
        }),
      ],
    );
  }

  Widget _buildCatalogCard(BuildContext context, Map<String, dynamic> item) {
    final itemId = item['id'] as String;
    final isZaloMcp = itemId == 'zalo_mcp';
    final isGoogle = itemId == 'google_workspace';

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
            // Header: Icon + Title + Badges
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: isZaloMcp
                        ? Colors.blue.withValues(alpha: 0.2)
                        : (isGoogle ? Colors.red.withValues(alpha: 0.2) : AppTheme.primary.withValues(alpha: 0.2)),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Icon(
                    isZaloMcp
                        ? Icons.chat_bubble_outline_rounded
                        : (isGoogle ? Icons.mark_email_read_outlined : Icons.extension_rounded),
                    color: isZaloMcp ? Colors.blueAccent : (isGoogle ? Colors.redAccent : AppTheme.primaryLight),
                    size: 24,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        item['name'] ?? '',
                        style: const TextStyle(
                          fontSize: 15,
                          fontWeight: FontWeight.bold,
                          color: AppTheme.textDark,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Row(
                        children: [
                          _buildBadge(item['auth_badge'] ?? '', Colors.blue.withValues(alpha: 0.2), const Color(0xFF60A5FA)),
                          if (item['is_beta'] == true) ...[
                            const SizedBox(width: 6),
                            _buildBadge('BETA', Colors.purple.withValues(alpha: 0.2), Colors.purpleAccent),
                          ],
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),

            // Description
            Expanded(
              child: Text(
                item['description'] ?? '',
                maxLines: 3,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  fontSize: 13,
                  color: AppTheme.textMutedDark.withValues(alpha: 0.9),
                  height: 1.4,
                ),
              ),
            ),
            const SizedBox(height: 12),

            // Dynamic Action Button: [Kết nối] vs [Đã kết nối / Quản lý]
            Obx(() {
              final isConnected = controller.isCatalogItemConnected(itemId);
              final connectedList = controller.getConnectedAccountsForCatalog(itemId);

              if (isConnected) {
                return SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    onPressed: () => _openManageAccountsDialog(context, item, connectedList),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppTheme.success.withValues(alpha: 0.15),
                      foregroundColor: AppTheme.success,
                      side: BorderSide(color: AppTheme.success.withValues(alpha: 0.5)),
                      minimumSize: const Size(double.infinity, 44),
                      padding: const EdgeInsets.symmetric(vertical: 12),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(100),
                      ),
                    ),
                    icon: const Icon(Icons.check_circle_rounded, size: 18),
                    label: Text(
                      'Đã kết nối (${connectedList.length})',
                      style: const TextStyle(fontWeight: FontWeight.bold),
                    ),
                  ),
                );
              }

              return SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  onPressed: () {
                    if (isZaloMcp) {
                      _openZaloQrDialog(context);
                    } else if (isGoogle) {
                      _openGoogleWorkspaceDialog(context);
                    } else {
                      Get.snackbar('Thông báo', 'Tính năng kết nối ${item['name']} đang được kích hoạt qua hệ thống MCP.');
                    }
                  },
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.surfaceDark.withValues(alpha: 0.8),
                    foregroundColor: AppTheme.textDark,
                    side: BorderSide(color: Colors.white.withValues(alpha: 0.15)),
                    minimumSize: const Size(double.infinity, 44),
                    padding: const EdgeInsets.symmetric(vertical: 12),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(100),
                    ),
                  ),
                  icon: Icon(isZaloMcp ? Icons.qr_code_scanner_rounded : (isGoogle ? Icons.mail_outline_rounded : Icons.link_rounded), size: 18),
                  label: const Text('Kết nối', style: TextStyle(fontWeight: FontWeight.bold)),
                ),
              );
            }),
          ],
        ),
      ),
    );
  }

  Widget _buildBadge(String text, Color bg, Color textCol) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        text,
        style: TextStyle(
          fontSize: 10,
          fontWeight: FontWeight.bold,
          color: textCol,
        ),
      ),
    );
  }

  // --- Zalo QR Dialog ---
  void _openZaloQrDialog(BuildContext context) {
    controller.startZaloQrFlow();

    Get.dialog(
      PopScope(
        canPop: true,
        onPopInvokedWithResult: (didPop, result) {
          if (didPop) {
            controller.cancelZaloQr();
          }
        },
        child: AlertDialog(
          backgroundColor: const Color(0xFF0F172A),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
            side: BorderSide(color: Colors.white.withValues(alpha: 0.1)),
          ),
          title: Row(
            children: const [
              Icon(Icons.qr_code_scanner_rounded, color: Colors.blueAccent, size: 24),
              SizedBox(width: 10),
              Text(
                'Quét QR kết nối Zalo Agent MCP',
                style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
              ),
            ],
          ),
          content: SizedBox(
            width: 360,
            child: Obx(() {
              if (controller.isQrStarting.value) {
                return const SizedBox(
                  height: 240,
                  child: Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        CircularProgressIndicator(),
                        SizedBox(height: 16),
                        Text('Đang khởi tạo máy chủ Zalo MCP...', style: TextStyle(color: AppTheme.textMutedDark, fontSize: 13)),
                      ],
                    ),
                  ),
                );
              }

              if (controller.qrError.value.isNotEmpty) {
                return SizedBox(
                  height: 220,
                  child: Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(Icons.error_outline_rounded, color: AppTheme.error, size: 48),
                        const SizedBox(height: 12),
                        Text(
                          controller.qrError.value,
                          textAlign: TextAlign.center,
                          style: const TextStyle(color: AppTheme.error, fontSize: 14),
                        ),
                        const SizedBox(height: 16),
                        ElevatedButton.icon(
                          onPressed: () => controller.startZaloQrFlow(),
                          icon: const Icon(Icons.refresh_rounded, size: 16),
                          label: const Text('Thử lại'),
                        ),
                      ],
                    ),
                  ),
                );
              }

              final qrData = controller.qrDataUrl.value;
              return Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Text(
                    'Mở ứng dụng Zalo trên điện thoại ➔ Chọn Quét mã QR để xác thực:',
                    style: TextStyle(color: AppTheme.textMutedDark, fontSize: 13),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 16),
                  Container(
                    width: 220,
                    height: 220,
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: qrData.isNotEmpty
                        ? Image.memory(
                            base64Decode(qrData.split(',').last),
                            fit: BoxFit.contain,
                          )
                        : const Center(
                            child: CircularProgressIndicator(),
                          ),
                  ),
                  const SizedBox(height: 16),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: const [
                      SizedBox(
                        width: 14,
                        height: 14,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      ),
                      SizedBox(width: 10),
                      Text(
                        'Đang chờ bạn quét mã trên Zalo...',
                        style: TextStyle(color: Colors.blueAccent, fontSize: 13),
                      ),
                    ],
                  ),
                ],
              );
            }),
          ),
          actions: [
            TextButton(
              onPressed: () {
                controller.cancelZaloQr();
                Get.back();
              },
              child: const Text('Hủy', style: TextStyle(color: AppTheme.textMutedDark)),
            ),
          ],
        ),
      ),
    );
  }

  // --- Google Workspace Dialog (Cho phép chọn/nhập địa chỉ Gmail) ---
  void _openGoogleWorkspaceDialog(BuildContext context) {
    final emailCtrl = TextEditingController(text: '');

    Get.dialog(
      AlertDialog(
        backgroundColor: const Color(0xFF0F172A),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: BorderSide(color: Colors.white.withValues(alpha: 0.1)),
        ),
        title: Row(
          children: const [
            Icon(Icons.mark_email_read_outlined, color: Colors.redAccent, size: 26),
            SizedBox(width: 10),
            Text(
              'Kết nối Gmail Google Workspace',
              style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
            ),
          ],
        ),
        content: SizedBox(
          width: 480,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Gợi ý sẵn địa chỉ Gmail (không bắt buộc) - bạn vẫn chọn lại được trong '
                'cửa sổ đăng nhập của Google:',
                style: TextStyle(color: AppTheme.textDark, fontSize: 14, fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 8),

              // Chỉ là login_hint cho Google. Tài khoản thật sự được kết nối là tài khoản
              // người dùng bấm đồng ý ở màn hình Google, và server đọc lại địa chỉ đó từ
              // token - không tin chuỗi gõ ở đây.
              TextField(
                controller: emailCtrl,
                style: const TextStyle(color: Colors.white, fontSize: 14),
                decoration: InputDecoration(
                  prefixIcon: const Icon(Icons.email_outlined, color: Colors.redAccent, size: 20),
                  hintText: 'Ví dụ: congviec@gmail.com',
                  hintStyle: const TextStyle(color: AppTheme.textMutedDark, fontSize: 13),
                  filled: true,
                  fillColor: AppTheme.surfaceDark,
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: BorderSide.none),
                ),
              ),
              const SizedBox(height: 16),

              const Text(
                'Quyền hạn AI sẽ thực hiện khi kết nối:',
                style: TextStyle(color: AppTheme.textMutedDark, fontSize: 13),
              ),
              const SizedBox(height: 12),

              _buildCapabilityItem(Icons.mark_email_unread_outlined, 'Đọc & Tìm kiếm Email', 'AI duyệt hòm thư đến, lọc thư theo người gửi, chủ đề hoặc từ khóa.'),
              const SizedBox(height: 10),
              _buildCapabilityItem(Icons.summarize_outlined, 'Tóm tắt hòm thư', 'Tóm tắt nhanh các email quan trọng, trích xuất việc cần làm trong ngày.'),
              const SizedBox(height: 10),
              _buildCapabilityItem(Icons.drafts_outlined, 'Soạn thư (chờ bạn duyệt)', 'AI chỉ lưu bản nháp; thư chỉ được gửi sau khi bạn tự bấm duyệt.'),
              const SizedBox(height: 18),

              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.blue.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: Colors.blue.withValues(alpha: 0.3)),
                ),
                child: Row(
                  children: const [
                    Icon(Icons.shield_outlined, color: Colors.blueAccent, size: 20),
                    SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        'Bạn đăng nhập trên trang accounts.google.com thật trong trình duyệt; '
                        'COSA OS không nhìn thấy mật khẩu của bạn và bạn thu hồi quyền bất cứ '
                        'lúc nào tại myaccount.google.com/permissions.',
                        style: TextStyle(color: Colors.blueAccent, fontSize: 12, height: 1.4),
                      ),
                    ),
                  ],
                ),
              ),

              Obx(() {
                if (controller.googleServerConfigured.value) {
                  return const SizedBox.shrink();
                }
                // Không có client id thì bấm nút chỉ nhận lỗi - nói trước cho đỡ mất công.
                return Container(
                  margin: const EdgeInsets.only(top: 12),
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.amber.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: Colors.amber.withValues(alpha: 0.35)),
                  ),
                  child: const Text(
                    'Máy chủ chưa cấu hình GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET nên chưa '
                    'mở được cửa sổ đăng nhập Google. Xem hướng dẫn trong DEPLOYMENT.md.',
                    style: TextStyle(color: Colors.amber, fontSize: 12, height: 1.4),
                  ),
                );
              }),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Get.back(),
            child: const Text('Hủy', style: TextStyle(color: AppTheme.textMutedDark)),
          ),
          Obx(
            () => ElevatedButton.icon(
              // Trước đây nút này chỉ lưu chuỗi email rồi tự nhận "đã kết nối" - không có
              // OAuth nào chạy, nên chat không bao giờ đọc được thư. Giờ nó mở đúng màn
              // hình đồng ý của Google và chờ callback mang refresh token về.
              onPressed: controller.isGoogleConnecting.value
                  ? null
                  : () async {
                      Get.back();
                      await controller.connectGoogle(
                        loginHint: emailCtrl.text.trim(),
                      );
                    },
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFFEA4335),
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
              ),
              icon: controller.isGoogleConnecting.value
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                    )
                  : const Icon(Icons.login_rounded, size: 18),
              label: Text(
                controller.isGoogleConnecting.value
                    ? 'Đang chờ bạn đồng ý...'
                    : 'Đăng nhập Google OAuth2',
                style: const TextStyle(fontWeight: FontWeight.bold),
              ),
            ),
          ),
        ],
      ),
    );
  }

  // --- Modal Quản Lý / Ngắt Kết Nối Tài Khoản ---
  void _openManageAccountsDialog(BuildContext context, Map<String, dynamic> item, List<Map<String, dynamic>> connectedList) {
    final itemId = item['id'] as String;
    final isGoogle = itemId == 'google_workspace';
    final isZalo = itemId == 'zalo_mcp';

    Get.dialog(
      AlertDialog(
        backgroundColor: const Color(0xFF0F172A),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: BorderSide(color: Colors.white.withValues(alpha: 0.1)),
        ),
        title: Row(
          children: [
            Icon(
              isGoogle ? Icons.mark_email_read_outlined : (isZalo ? Icons.chat_bubble_outline_rounded : Icons.hub_outlined),
              color: isGoogle ? Colors.redAccent : (isZalo ? Colors.blueAccent : AppTheme.primaryLight),
              size: 24,
            ),
            const SizedBox(width: 10),
            Text(
              'Quản lý kết nối ${item['name']}',
              style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
            ),
          ],
        ),
        content: SizedBox(
          width: 480,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Danh sách tài khoản đang kết nối:',
                style: TextStyle(color: AppTheme.textDark, fontSize: 14, fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 12),

              ListView.separated(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: connectedList.length,
                separatorBuilder: (context, index) => const SizedBox(height: 8),
                itemBuilder: (context, idx) {
                  final conn = connectedList[idx];
                  final connId = conn['id'];
                  final connName = conn['name'] ?? 'Tài khoản ${idx + 1}';

                  return Container(
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                    decoration: BoxDecoration(
                      color: AppTheme.surfaceDark,
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.check_circle_outline, color: AppTheme.success, size: 18),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            connName,
                            style: const TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.w500),
                          ),
                        ),
                        ElevatedButton.icon(
                          onPressed: () async {
                            Get.back();
                            await controller.deleteConnector(connId);
                          },
                          style: ElevatedButton.styleFrom(
                            backgroundColor: Colors.red.withValues(alpha: 0.2),
                            foregroundColor: Colors.redAccent,
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                            elevation: 0,
                          ),
                          icon: const Icon(Icons.link_off_rounded, size: 14),
                          label: const Text('Ngắt kết nối', style: TextStyle(fontSize: 12)),
                        ),
                      ],
                    ),
                  );
                },
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Get.back(),
            child: const Text('Đóng', style: TextStyle(color: AppTheme.textMutedDark)),
          ),
          ElevatedButton.icon(
            onPressed: () {
              Get.back();
              if (isGoogle) {
                _openGoogleWorkspaceDialog(context);
              } else if (isZalo) {
                _openZaloQrDialog(context);
              }
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: AppTheme.primary,
              foregroundColor: const Color(0xFF04070E),
            ),
            icon: const Icon(Icons.add_rounded, size: 16),
            label: const Text('+ Thêm tài khoản khác'),
          ),
        ],
      ),
    );
  }

  Widget _buildCapabilityItem(IconData icon, String title, String desc) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          padding: const EdgeInsets.all(6),
          decoration: BoxDecoration(
            color: AppTheme.primary.withValues(alpha: 0.15),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Icon(icon, color: AppTheme.primaryLight, size: 18),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: const TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.bold)),
              const SizedBox(height: 2),
              Text(desc, style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 12, height: 1.3)),
            ],
          ),
        ),
      ],
    );
  }

  void _confirmDelete(BuildContext context, String id) {
    Get.dialog(
      AlertDialog(
        backgroundColor: AppTheme.surfaceDark,
        title: const Text('Xác nhận ngắt kết nối'),
        content: const Text('Bạn có chắc chắn muốn ngắt kết nối tài khoản này không?'),
        actions: [
          TextButton(
            onPressed: () => Get.back(),
            child: const Text('Hủy', style: TextStyle(color: AppTheme.textMutedDark)),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: AppTheme.error),
            onPressed: () {
              controller.deleteConnector(id);
              Get.back();
            },
            child: const Text('Ngắt kết nối'),
          ),
        ],
      ),
    );
  }
}
