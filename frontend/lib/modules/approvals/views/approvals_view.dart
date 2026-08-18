import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/approvals_controller.dart';

class ApprovalsView extends GetView<ApprovalsController> {
  const ApprovalsView({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0B0F19),
      body: Column(
        children: [
          // Header Bar
          _buildHeaderBar(context),

          // Main Tabs & List
          Expanded(
            child: TabBarView(
              controller: controller.tabController,
              children: [
                _buildPendingTab(context),
                _buildHistoryTab(context),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildHeaderBar(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 18),
      decoration: const BoxDecoration(
        color: Color(0xFF0F172A),
        border: Border(bottom: BorderSide(color: Color(0xFF1E293B))),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: Colors.amber.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(12),
            ),
            child: const Icon(Icons.verified_user_outlined, color: Colors.amber, size: 24),
          ),
          const SizedBox(width: 14),
          const Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Human Approval Inbox',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 20,
                  fontWeight: FontWeight.w800,
                  letterSpacing: -0.5,
                ),
              ),
              Text(
                'Cổng phê duyệt quyết định & kiểm soát rủi ro cho Founder / Human Leads',
                style: TextStyle(color: Color(0xFF94A3B8), fontSize: 12.5),
              ),
            ],
          ),
          const Spacer(),

          // Tab Bar Switcher
          Container(
            width: 320,
            decoration: BoxDecoration(
              color: const Color(0xFF1E293B),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: const Color(0xFF334155)),
            ),
            child: TabBar(
              controller: controller.tabController,
              indicatorSize: TabBarIndicatorSize.tab,
              indicator: BoxDecoration(
                color: Colors.blueAccent,
                borderRadius: BorderRadius.circular(8),
              ),
              labelColor: Colors.white,
              unselectedLabelColor: Colors.grey,
              labelStyle: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13),
              tabs: [
                Obx(() => Tab(
                      text: 'Chờ duyệt (${controller.pendingApprovals.length})',
                    )),
                const Tab(text: 'Lịch sử đã duyệt'),
              ],
            ),
          ),

          const SizedBox(width: 14),

          // Refresh Button
          IconButton(
            tooltip: 'Làm mới',
            onPressed: () => controller.loadApprovals(),
            icon: const Icon(Icons.refresh_rounded, color: Colors.white70),
            style: IconButton.styleFrom(
              backgroundColor: const Color(0xFF1E293B),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(8),
                side: const BorderSide(color: Color(0xFF334155)),
              ),
            ),
          ),
        ],
      ),
    );
  }

  // --- TAB 1: PENDING TICKETS ---
  Widget _buildPendingTab(BuildContext context) {
    return Column(
      children: [
        // Risk Filter Chips
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 10),
          decoration: const BoxDecoration(
            color: Color(0xFF0F172A),
            border: Border(bottom: BorderSide(color: Color(0xFF1E293B))),
          ),
          child: Row(
            children: [
              const Text('Mức rủi ro:', style: TextStyle(color: Colors.grey, fontSize: 12.5, fontWeight: FontWeight.w600)),
              const SizedBox(width: 12),
              _buildRiskFilterChip('Tất cả', 'ALL'),
              const SizedBox(width: 8),
              _buildRiskFilterChip('🔴 CRITICAL (Founder Only)', 'CRITICAL', color: const Color(0xFFEF4444)),
              const SizedBox(width: 8),
              _buildRiskFilterChip('🟠 HIGH RISK (Lead Review)', 'HIGH', color: const Color(0xFFF59E0B)),
            ],
          ),
        ),

        // List Content
        Expanded(
          child: Obx(() {
            if (controller.isLoading.value) {
              return const Center(child: CircularProgressIndicator(color: Colors.blueAccent));
            }
            if (controller.filteredApprovals.isEmpty) {
              return Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.task_alt_rounded, size: 56, color: Colors.green.shade400),
                    const SizedBox(height: 14),
                    const Text(
                      'Tuyệt vời! Không có yêu cầu nào đang chờ phê duyệt.',
                      style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w600),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Mọi hoạt động của AI Workforce đang vận hành an toàn trong hạn mức.',
                      style: TextStyle(color: Colors.grey.shade400, fontSize: 13),
                    ),
                  ],
                ),
              );
            }

            return ListView.separated(
              padding: const EdgeInsets.all(24),
              itemCount: controller.filteredApprovals.length,
              separatorBuilder: (context, index) => const SizedBox(height: 14),
              itemBuilder: (ctx, i) {
                final item = controller.filteredApprovals[i];
                return _buildApprovalCard(context, item);
              },
            );
          }),
        ),
      ],
    );
  }

  Widget _buildRiskFilterChip(String label, String value, {Color? color}) {
    return Obx(() {
      final isSelected = controller.selectedRiskFilter.value == value;
      return FilterChip(
        label: Text(label),
        selected: isSelected,
        onSelected: (_) => controller.setRiskFilter(value),
        selectedColor: color ?? Colors.blueAccent,
        backgroundColor: const Color(0xFF1E293B),
        labelStyle: TextStyle(
          fontSize: 12,
          fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
          color: isSelected ? Colors.white : Colors.grey.shade400,
        ),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: BorderSide(
            color: isSelected ? (color ?? Colors.blueAccent) : const Color(0xFF334155),
          ),
        ),
      );
    });
  }

  Widget _buildApprovalCard(BuildContext context, Map<String, dynamic> item) {
    final id = item['id'];
    final requester = item['requester_agent_key'] ?? item['agent_name'] ?? 'Agent';
    final actionType = item['action_type'] ?? 'TOOL_EXEC';
    final riskLevel = (item['risk_level'] ?? 'HIGH').toString().toUpperCase();
    final role = item['required_role'] ?? 'FOUNDER';
    final reason = item['reason'] ?? 'Hành động rủi ro cần Founder phê duyệt';
    final toolKey = item['tool_key'] ?? actionType;
    final payload = item['payload_jsonb'] ?? item['payload'] ?? {};

    final isCritical = riskLevel == 'CRITICAL';
    final riskColor = isCritical ? const Color(0xFFEF4444) : const Color(0xFFF59E0B);

    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: riskColor.withValues(alpha: 0.5), width: 1.2),
        boxShadow: [
          BoxShadow(color: riskColor.withValues(alpha: 0.1), blurRadius: 12, offset: const Offset(0, 4)),
        ],
      ),
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Card Header
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
                decoration: BoxDecoration(
                  color: riskColor.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: riskColor.withValues(alpha: 0.3)),
                ),
                child: Row(
                  children: [
                    Icon(isCritical ? Icons.gavel_rounded : Icons.warning_amber_rounded, size: 14, color: riskColor),
                    const SizedBox(width: 5),
                    Text(
                      '$riskLevel RISK ($role)',
                      style: TextStyle(color: riskColor, fontSize: 11, fontWeight: FontWeight.w800),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 10),
              Text(
                'Lệnh gọi: $toolKey',
                style: const TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.w700),
              ),
              const Spacer(),
              Text(
                'Người yêu cầu: $requester',
                style: TextStyle(color: Colors.blueAccent.shade100, fontSize: 12.5, fontWeight: FontWeight.w600),
              ),
            ],
          ),

          const SizedBox(height: 12),

          // Reason Context
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: const Color(0xFF0F172A),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: const Color(0xFF334155)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Lý do phê duyệt:', style: TextStyle(color: Colors.grey, fontSize: 11.5, fontWeight: FontWeight.w600)),
                const SizedBox(height: 4),
                Text(
                  reason,
                  style: const TextStyle(color: Color(0xFFE2E8F0), fontSize: 13, height: 1.4),
                ),
              ],
            ),
          ),

          const SizedBox(height: 12),

          // Payload Preview Accordion
          ExpansionTile(
            tilePadding: EdgeInsets.zero,
            title: const Text('Xem chi tiết Payload dữ liệu', style: TextStyle(color: Colors.blueAccent, fontSize: 12.5, fontWeight: FontWeight.w600)),
            children: [
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFF020617),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: SelectableText(
                  const JsonEncoder.withIndent('  ').convert(payload),
                  style: const TextStyle(color: Color(0xFF94A3B8), fontFamily: 'monospace', fontSize: 12),
                ),
              ),
            ],
          ),

          const Divider(color: Color(0xFF334155), height: 20),

          // 3-Action Buttons (Approve, Reject, Request Revision)
          Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              // Request Revision Button
              OutlinedButton.icon(
                onPressed: () => _showRevisionDialog(context, id),
                icon: const Icon(Icons.edit_note_rounded, size: 16, color: Color(0xFF818CF8)),
                label: const Text('Yêu cầu sửa lại', style: TextStyle(color: Color(0xFF818CF8), fontSize: 12.5)),
                style: OutlinedButton.styleFrom(
                  side: const BorderSide(color: Color(0xFF4F46E5)),
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
              ),
              const SizedBox(width: 10),

              // Reject Button
              OutlinedButton.icon(
                onPressed: () => _showRejectDialog(context, id),
                icon: const Icon(Icons.close_rounded, size: 16, color: Color(0xFFF87171)),
                label: const Text('Từ chối', style: TextStyle(color: Color(0xFFF87171), fontSize: 12.5)),
                style: OutlinedButton.styleFrom(
                  side: const BorderSide(color: Color(0xFFDC2626)),
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
              ),
              const SizedBox(width: 10),

              // Approve Button
              ElevatedButton.icon(
                onPressed: () => _showApproveDialog(context, id),
                icon: const Icon(Icons.check_rounded, size: 16, color: Colors.white),
                label: const Text('Chấp thuận (Approve)', style: TextStyle(color: Colors.white, fontSize: 12.5, fontWeight: FontWeight.w700)),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF10B981),
                  padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 10),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  // --- TAB 2: HISTORY ---
  Widget _buildHistoryTab(BuildContext context) {
    return Obx(() {
      if (controller.historyApprovals.isEmpty) {
        return Center(
          child: Text('Chưa có lịch sử phê duyệt.', style: TextStyle(color: Colors.grey.shade500)),
        );
      }
      return ListView.separated(
        padding: const EdgeInsets.all(24),
        itemCount: controller.historyApprovals.length,
        separatorBuilder: (context, index) => const SizedBox(height: 10),
        itemBuilder: (ctx, i) {
          final item = controller.historyApprovals[i];
          final status = (item['status'] ?? 'APPROVED').toString().toUpperCase();
          final isApproved = status == 'APPROVED';
          final statusColor = isApproved ? const Color(0xFF10B981) : const Color(0xFFEF4444);

          return Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: const Color(0xFF1E293B),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: const Color(0xFF334155)),
            ),
            child: Row(
              children: [
                Icon(isApproved ? Icons.check_circle_outline : Icons.cancel_outlined, color: statusColor, size: 22),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Lệnh: ${item['tool_key'] ?? item['action_type'] ?? 'Action'}',
                        style: const TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.w700),
                      ),
                      Text(
                        'Người duyệt / Lý do: ${item['approver_comment'] ?? 'N/A'}',
                        style: TextStyle(color: Colors.grey.shade400, fontSize: 12),
                      ),
                    ],
                  ),
                ),
                Text(
                  status,
                  style: TextStyle(color: statusColor, fontSize: 12, fontWeight: FontWeight.w800),
                ),
              ],
            ),
          );
        },
      );
    });
  }

  // --- DIALOGS ---
  void _showApproveDialog(BuildContext context, dynamic id) {
    final commentCtrl = TextEditingController();
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF1E293B),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        title: const Text('Xác nhận Phê duyệt', style: TextStyle(color: Colors.white)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Lệnh sẽ được gửi ngay cho Agent tiếp tục xử lý.', style: TextStyle(color: Colors.grey, fontSize: 13)),
            const SizedBox(height: 12),
            TextField(
              controller: commentCtrl,
              style: const TextStyle(color: Colors.white, fontSize: 13),
              decoration: InputDecoration(
                hintText: 'Ghi chú phê duyệt (tùy chọn)...',
                hintStyle: TextStyle(color: Colors.grey.shade600),
                filled: true,
                fillColor: const Color(0xFF0F172A),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Hủy', style: TextStyle(color: Colors.grey))),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(ctx);
              controller.approveTicket(id, comment: commentCtrl.text.trim());
            },
            style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF10B981)),
            child: const Text('Xác nhận Duyệt', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );
  }

  void _showRejectDialog(BuildContext context, dynamic id) {
    final reasonCtrl = TextEditingController();
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF1E293B),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        title: const Text('Từ chối thực thi', style: TextStyle(color: Color(0xFFEF4444))),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Nhập lý do từ chối để thông báo cho Agent:', style: TextStyle(color: Colors.grey, fontSize: 13)),
            const SizedBox(height: 12),
            TextField(
              controller: reasonCtrl,
              style: const TextStyle(color: Colors.white, fontSize: 13),
              decoration: InputDecoration(
                hintText: 'Lý do từ chối (bắt buộc)...',
                hintStyle: TextStyle(color: Colors.grey.shade600),
                filled: true,
                fillColor: const Color(0xFF0F172A),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Hủy', style: TextStyle(color: Colors.grey))),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(ctx);
              controller.rejectTicket(id, reason: reasonCtrl.text.trim());
            },
            style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFFEF4444)),
            child: const Text('Từ chối lệnh', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );
  }

  void _showRevisionDialog(BuildContext context, dynamic id) {
    final feedbackCtrl = TextEditingController();
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF1E293B),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        title: const Text('Yêu cầu Agent sửa lại', style: TextStyle(color: Color(0xFF818CF8))),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Nhập hướng dẫn cụ thể để Agent viết lại nội dung:', style: TextStyle(color: Colors.grey, fontSize: 13)),
            const SizedBox(height: 12),
            TextField(
              controller: feedbackCtrl,
              maxLines: 3,
              style: const TextStyle(color: Colors.white, fontSize: 13),
              decoration: InputDecoration(
                hintText: 'Ví dụ: Sửa lại văn phong trang trọng hơn và giảm chiết khấu xuống 10%...',
                hintStyle: TextStyle(color: Colors.grey.shade600),
                filled: true,
                fillColor: const Color(0xFF0F172A),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Hủy', style: TextStyle(color: Colors.grey))),
          ElevatedButton(
            onPressed: () {
              if (feedbackCtrl.text.trim().isNotEmpty) {
                Navigator.pop(ctx);
                controller.requestRevisionTicket(id, feedback: feedbackCtrl.text.trim());
              }
            },
            style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF4F46E5)),
            child: const Text('Gửi yêu cầu sửa', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );
  }
}
