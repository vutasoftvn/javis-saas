import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/sales_controller.dart';
import 'widgets/crm_account_entry_dialog.dart';

class CustomerView extends StatelessWidget {
  const CustomerView({super.key});

  String _formatVND(num amount) {
    if (amount >= 1000000000) return '${(amount / 1000000000).toStringAsFixed(1)} tỷ đồng';
    if (amount >= 1000000) return '${(amount / 1000000).toStringAsFixed(1)} triệu đồng';
    if (amount >= 1000) return '${(amount / 1000).toStringAsFixed(0)} nghìn đồng';
    return '${amount.toInt()} đồng';
  }

  void _openAddAccountDialog(BuildContext context, SalesController controller) {
    showDialog(
      context: context,
      builder: (_) => CrmAccountEntryDialog(
        onSubmit: ({
          required name,
          required category,
          domain,
          industry,
          sizeSegment,
          source,
          lifecycleStatus,
          tags,
          contactName,
          contactPhone,
          contactEmail,
        }) =>
            controller.createAccount(
          name: name,
          category: category,
          domain: domain,
          industry: industry,
          sizeSegment: sizeSegment,
          source: source,
          lifecycleStatus: lifecycleStatus,
          tags: tags,
          contactName: contactName,
          contactPhone: contactPhone,
          contactEmail: contactEmail,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final c = Get.find<SalesController>();

    return Obx(() {
      final accounts = c.crmAccounts;
      final selectedType = c.selectedAccountType.value;

      return ListView(
        padding: const EdgeInsets.all(20),
        children: [
          // 1. Header Toolbar
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: const Color(0xFF0F172A),
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: const Color(0xFF1E293B)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: const [
                          Text(
                            'DANH BẠ 360°: KHÁCH HÀNG & ĐỐI TÁC',
                            style: TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.bold, letterSpacing: 0.5),
                          ),
                          SizedBox(height: 4),
                          Text(
                            'Phân loại chi tiết khách hàng, đối tác chiến lược, đại lý và nhà cung cấp',
                            style: TextStyle(color: Color(0xFF94A3B8), fontSize: 11),
                          ),
                        ],
                      ),
                    ),
                    Row(
                      children: [
                        ElevatedButton.icon(
                          onPressed: () => _openAddAccountDialog(context, c),
                          icon: const Icon(Icons.add_rounded, size: 14, color: Colors.black),
                          label: const Text('Thêm Đối tác / Khách', style: TextStyle(color: Colors.black, fontSize: 12, fontWeight: FontWeight.bold)),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: const Color(0xFF00E5FF),
                            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                          ),
                        ),
                        const SizedBox(width: 8),
                        IconButton(
                          onPressed: c.loadAll,
                          icon: const Icon(Icons.refresh_rounded, size: 18, color: Color(0xFF94A3B8)),
                          tooltip: 'Làm mới danh bạ',
                        ),
                      ],
                    ),
                  ],
                ),
                const SizedBox(height: 14),

                // Search & Filter Row
                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        style: const TextStyle(color: Colors.white, fontSize: 12),
                        decoration: InputDecoration(
                          hintText: 'Tìm kiếm theo tên công ty, domain, ngành nghề...',
                          hintStyle: const TextStyle(color: Color(0xFF475569), fontSize: 12),
                          prefixIcon: const Icon(Icons.search_rounded, size: 16, color: Color(0xFF64748B)),
                          filled: true,
                          fillColor: const Color(0xFF131D35),
                          isDense: true,
                          contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                          border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: const BorderSide(color: Color(0xFF1E293B))),
                        ),
                        onChanged: (val) => c.filterAccounts(search: val),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),

                // Type Filter Chips
                SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    children: [
                      _buildFilterChip('Tất cả (${accounts.length})', 'ALL', selectedType, (v) => c.filterAccounts(type: v)),
                      const SizedBox(width: 8),
                      _buildFilterChip('🏢 Khách hàng', 'CUSTOMER', selectedType, (v) => c.filterAccounts(type: v)),
                      const SizedBox(width: 8),
                      _buildFilterChip('🤝 Đối tác / Đại lý', 'PARTNER', selectedType, (v) => c.filterAccounts(type: v)),
                      const SizedBox(width: 8),
                      _buildFilterChip('🚚 Nhà cung cấp', 'VENDOR', selectedType, (v) => c.filterAccounts(type: v)),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),

          // 2. Account List
          if (c.isLoading.value)
            const Center(
              child: Padding(
                padding: EdgeInsets.all(40),
                child: CircularProgressIndicator(),
              ),
            )
          else if (accounts.isEmpty)
            Container(
              padding: const EdgeInsets.symmetric(vertical: 48, horizontal: 24),
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: const Color(0xFF0F172A),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: const Color(0xFF1E293B)),
              ),
              child: Column(
                children: [
                  const Icon(Icons.business_outlined, size: 48, color: Color(0xFF475569)),
                  const SizedBox(height: 14),
                  const Text(
                    'Chưa có dữ liệu danh bạ phù hợp',
                    style: TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.w600),
                  ),
                  const SizedBox(height: 6),
                  const Text(
                    'Bấm "+ Thêm Đối tác / Khách" để tạo hồ sơ khách hàng hoặc đối tác phân phối đầu tiên.',
                    textAlign: TextAlign.center,
                    style: TextStyle(color: Color(0xFF64748B), fontSize: 12),
                  ),
                ],
              ),
            )
          else
            ...accounts.map((acc) {
              final accMap = acc is Map<String, dynamic> ? acc : <String, dynamic>{};
              return _buildAccountCard(accMap);
            }),
        ],
      );
    });
  }

  Widget _buildFilterChip(String label, String value, String currentSelected, Function(String) onSelect) {
    final isSel = currentSelected == value;
    return InkWell(
      onTap: () => onSelect(value),
      borderRadius: BorderRadius.circular(6),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: isSel ? const Color(0xFF00E5FF).withValues(alpha: 0.15) : const Color(0xFF131D35),
          borderRadius: BorderRadius.circular(6),
          border: Border.all(
            color: isSel ? const Color(0xFF00E5FF) : const Color(0xFF1E293B),
            width: isSel ? 1.5 : 1,
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: isSel ? const Color(0xFF00E5FF) : const Color(0xFF94A3B8),
            fontSize: 11,
            fontWeight: isSel ? FontWeight.bold : FontWeight.normal,
          ),
        ),
      ),
    );
  }

  Widget _buildAccountCard(Map<String, dynamic> acc) {
    final name = acc['name']?.toString() ?? 'Doanh nghiệp';
    final domain = acc['domain']?.toString();
    final industry = acc['industry']?.toString() ?? 'Chưa cập nhật';
    final size = acc['size_segment']?.toString() ?? 'Tiêu chuẩn';
    final category = acc['category']?.toString() ?? 'CUSTOMER';
    final status = acc['lifecycle_status']?.toString() ?? 'ACTIVE';
    final tags = (acc['tags'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [];
    final contactName = acc['contact_name']?.toString();
    final contactPhone = acc['contact_phone']?.toString();
    final contactEmail = acc['contact_email']?.toString();
    final dealsCount = (acc['deals_count'] as num?)?.toInt() ?? 0;
    final wonRevenue = (acc['won_revenue'] as num?) ?? 0;

    // Category styling
    Color catColor = const Color(0xFF00E5FF);
    String catLabel = 'KHÁCH HÀNG';
    IconData catIcon = Icons.business_center_rounded;
    if (category == 'PARTNER') {
      catColor = const Color(0xFFA855F7);
      catLabel = 'ĐỐI TÁC / ĐẠI LÝ';
      catIcon = Icons.handshake_rounded;
    } else if (category == 'VENDOR') {
      catColor = const Color(0xFFF59E0B);
      catLabel = 'NHÀ CUNG CẤP';
      catIcon = Icons.local_shipping_rounded;
    }

    // Status styling
    Color statusColor = const Color(0xFF10B981);
    String statusLabel = 'Đang hoạt động';
    if (status == 'PROSPECT') {
      statusColor = const Color(0xFF38BDF8);
      statusLabel = 'Tiềm năng mới';
    } else if (status == 'ONBOARDING') {
      statusColor = const Color(0xFFF59E0B);
      statusLabel = 'Đang bàn giao';
    } else if (status == 'WATCH') {
      statusColor = const Color(0xFFF97316);
      statusLabel = 'Cần theo dõi';
    } else if (status == 'AT_RISK') {
      statusColor = const Color(0xFFEF4444);
      statusLabel = 'Nguy cơ rời bỏ';
    }

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFF1E293B)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Avatar
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: catColor.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: catColor.withValues(alpha: 0.3)),
                ),
                alignment: Alignment.center,
                child: Text(
                  name.isNotEmpty ? name.substring(0, 1).toUpperCase() : 'C',
                  style: TextStyle(color: catColor, fontSize: 18, fontWeight: FontWeight.bold),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Flexible(
                          child: Text(
                            name,
                            style: const TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.bold),
                          ),
                        ),
                        if (domain != null && domain.isNotEmpty) ...[
                          const SizedBox(width: 8),
                          Text('• $domain', style: const TextStyle(color: Color(0xFF64748B), fontSize: 11)),
                        ],
                      ],
                    ),
                    const SizedBox(height: 4),
                    Row(
                      children: [
                        Text('$industry • $size', style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 11)),
                      ],
                    ),
                  ],
                ),
              ),
              // Category Badge & Status
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: catColor.withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: catColor.withValues(alpha: 0.3)),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(catIcon, size: 11, color: catColor),
                        const SizedBox(width: 4),
                        Text(catLabel, style: TextStyle(color: catColor, fontSize: 9, fontWeight: FontWeight.bold)),
                      ],
                    ),
                  ),
                  const SizedBox(height: 4),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                    decoration: BoxDecoration(
                      color: statusColor.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(statusLabel, style: TextStyle(color: statusColor, fontSize: 9, fontWeight: FontWeight.w600)),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 12),

          // Contact details & Metrics Row
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: const Color(0xFF131D35),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Row(
                    children: [
                      const Icon(Icons.person_outline_rounded, size: 14, color: Color(0xFF64748B)),
                      const SizedBox(width: 6),
                      Text(
                        contactName ?? 'Chưa gán người đại diện',
                        style: TextStyle(
                          color: contactName != null ? Colors.white : const Color(0xFF64748B),
                          fontSize: 11,
                          fontWeight: contactName != null ? FontWeight.w500 : FontWeight.normal,
                        ),
                      ),
                      if (contactPhone != null) ...[
                        const SizedBox(width: 12),
                        const Icon(Icons.phone_outlined, size: 13, color: Color(0xFF64748B)),
                        const SizedBox(width: 4),
                        Text(contactPhone, style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 11)),
                      ],
                      if (contactEmail != null) ...[
                        const SizedBox(width: 12),
                        const Icon(Icons.email_outlined, size: 13, color: Color(0xFF64748B)),
                        const SizedBox(width: 4),
                        Text(contactEmail, style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 11)),
                      ],
                    ],
                  ),
                ),
                Row(
                  children: [
                    const Icon(Icons.monetization_on_outlined, size: 14, color: Color(0xFF10B981)),
                    const SizedBox(width: 4),
                    Text(
                      dealsCount > 0 ? '$dealsCount Deal • ${_formatVND(wonRevenue)}' : 'Chưa có deal',
                      style: const TextStyle(color: Color(0xFF10B981), fontSize: 11, fontWeight: FontWeight.bold),
                    ),
                  ],
                ),
              ],
            ),
          ),

          // Tags Row
          if (tags.isNotEmpty) ...[
            const SizedBox(height: 10),
            Wrap(
              spacing: 6,
              runSpacing: 4,
              children: tags.map((t) {
                Color tagColor = const Color(0xFF38BDF8);
                if (t.contains('VIP') || t.contains('Key')) tagColor = const Color(0xFFF59E0B);
                if (t.contains('ĐạiLý') || t.contains('Đối tác')) tagColor = const Color(0xFFA855F7);
                if (t.contains('Hot')) tagColor = const Color(0xFFEF4444);

                return Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: tagColor.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(4),
                    border: Border.all(color: tagColor.withValues(alpha: 0.3)),
                  ),
                  child: Text(
                    t,
                    style: TextStyle(color: tagColor, fontSize: 9, fontWeight: FontWeight.w600),
                  ),
                );
              }).toList(),
            ),
          ],
        ],
      ),
    );
  }
}
