import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/tech_radar_controller.dart';
import 'widgets/radar_canvas.dart';
import 'widgets/add_radar_item_dialog.dart';
import 'widgets/radar_item_detail_dialog.dart';

class TechRadarView extends StatelessWidget {
  const TechRadarView({super.key});

  @override
  Widget build(BuildContext context) {
    final controller = Get.put(TechRadarController());

    return Scaffold(
      backgroundColor: const Color(0xFF060A14),
      body: Column(
        children: [
          // ── Header Bar ──────────────────────────────────────────
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 18),
            decoration: BoxDecoration(
              color: const Color(0xFF090E1B),
              border: Border(
                bottom: BorderSide(
                  color: const Color(0xFF00E5FF).withValues(alpha: 0.15),
                ),
              ),
            ),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: const Color(0xFF00E5FF).withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(
                      color: const Color(0xFF00E5FF).withValues(alpha: 0.3),
                    ),
                  ),
                  child: const Icon(
                    Icons.radar_rounded,
                    color: Color(0xFF00E5FF),
                    size: 22,
                  ),
                ),
                const SizedBox(width: 14),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Radar Công nghệ & Kiến trúc AI (P5)',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 18,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      'Định vị công nghệ COSA OS: ADOPT • TRIAL • ASSESS • WATCH (§104)',
                      style: TextStyle(
                        color: Colors.white.withValues(alpha: 0.6),
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
                const Spacer(),
                // Seed button
                OutlinedButton.icon(
                  style: OutlinedButton.styleFrom(
                    foregroundColor: const Color(0xFF38BDF8),
                    side: BorderSide(color: const Color(0xFF38BDF8).withValues(alpha: 0.4)),
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  ),
                  icon: const Icon(Icons.bolt, size: 16),
                  label: const Text('Nạp mẫu COSA §104', style: TextStyle(fontSize: 12)),
                  onPressed: () => controller.seedDefaults(),
                ),
                const SizedBox(width: 10),
                // Add item button
                ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF00E5FF),
                    foregroundColor: Colors.black,
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  ),
                  icon: const Icon(Icons.add, size: 16),
                  label: const Text(
                    'Thêm công nghệ',
                    style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700),
                  ),
                  onPressed: () => AddRadarItemDialog.show(context),
                ),
              ],
            ),
          ),

          // ── Stats Summary Bar ────────────────────────────────────
          Obx(() {
            final adoptCount = controller.countByStatus('ADOPT');
            final trialCount = controller.countByStatus('TRIAL');
            final assessCount = controller.countByStatus('ASSESS');
            final watchCount = controller.countByStatus('WATCH');

            return Container(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
              color: const Color(0xFF0B1222),
              child: Row(
                children: [
                  _buildStatPill('Tất cả', '${controller.items.length}', Colors.white, 'ALL', controller),
                  const SizedBox(width: 12),
                  _buildStatPill('ADOPT (Chính thức)', '$adoptCount', const Color(0xFF10B981), 'ADOPT', controller),
                  const SizedBox(width: 12),
                  _buildStatPill('TRIAL (Thử nghiệm)', '$trialCount', const Color(0xFF00E5FF), 'TRIAL', controller),
                  const SizedBox(width: 12),
                  _buildStatPill('ASSESS (Đánh giá)', '$assessCount', const Color(0xFFF59E0B), 'ASSESS', controller),
                  const SizedBox(width: 12),
                  _buildStatPill('WATCH (Theo dõi)', '$watchCount', const Color(0xFFA855F7), 'WATCH', controller),
                  const Spacer(),
                  // Search input
                  SizedBox(
                    width: 220,
                    height: 36,
                    child: TextField(
                      style: const TextStyle(color: Colors.white, fontSize: 12),
                      decoration: InputDecoration(
                        hintText: 'Tìm kiếm công nghệ...',
                        hintStyle: const TextStyle(color: Color(0xFF64748B), fontSize: 12),
                        prefixIcon: const Icon(Icons.search, size: 16, color: Color(0xFF64748B)),
                        filled: true,
                        fillColor: const Color(0xFF131B2E),
                        contentPadding: EdgeInsets.zero,
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(8),
                          borderSide: BorderSide(color: Colors.white.withValues(alpha: 0.1)),
                        ),
                      ),
                      onChanged: (val) => controller.searchQuery.value = val,
                    ),
                  ),
                ],
              ),
            );
          }),

          // ── Main Content Area (Split: Left Visual Radar, Right Item Cards) ──
          Expanded(
            child: Obx(() {
              if (controller.isLoading.value && controller.items.isEmpty) {
                return const Center(
                  child: CircularProgressIndicator(color: Color(0xFF00E5FF)),
                );
              }

              final filtered = controller.filteredItems;

              return Row(
                children: [
                  // Left Side: Interactive Radar Canvas (45% width)
                  Expanded(
                    flex: 5,
                    child: Container(
                      padding: const EdgeInsets.all(24),
                      decoration: BoxDecoration(
                        border: Border(
                          right: BorderSide(
                            color: const Color(0xFF1E293B).withValues(alpha: 0.8),
                          ),
                        ),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              const Icon(Icons.hub_outlined, color: Color(0xFF00E5FF), size: 18),
                              const SizedBox(width: 8),
                              const Text(
                                'Bản đồ Radar Trực quan',
                                style: TextStyle(
                                  color: Colors.white,
                                  fontSize: 14,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                              const Spacer(),
                              Text(
                                '${filtered.length} mục',
                                style: const TextStyle(
                                  color: Color(0xFF64748B),
                                  fontSize: 12,
                                  fontFamily: 'monospace',
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 16),
                          Expanded(
                            child: RadarCanvas(
                              items: filtered,
                              onItemTap: (item) => RadarItemDetailDialog.show(context, item),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),

                  // Right Side: Technology Cards List (55% width)
                  Expanded(
                    flex: 6,
                    child: Container(
                      padding: const EdgeInsets.all(24),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          // Category selector tabs
                          SingleChildScrollView(
                            scrollDirection: Axis.horizontal,
                            child: Row(
                              children: controller.categories.map((cat) {
                                final isSelected = controller.selectedCategory.value == cat;
                                return Padding(
                                  padding: const EdgeInsets.only(right: 8),
                                  child: FilterChip(
                                    label: Text(cat),
                                    labelStyle: TextStyle(
                                      color: isSelected ? Colors.black : const Color(0xFF94A3B8),
                                      fontSize: 11,
                                      fontWeight: isSelected ? FontWeight.w700 : FontWeight.normal,
                                    ),
                                    selected: isSelected,
                                    selectedColor: const Color(0xFF00E5FF),
                                    backgroundColor: const Color(0xFF131B2E),
                                    onSelected: (selected) {
                                      controller.selectedCategory.value = cat;
                                    },
                                  ),
                                );
                              }).toList(),
                            ),
                          ),
                          const SizedBox(height: 16),

                          // Cards Grid / List
                          Expanded(
                            child: filtered.isEmpty
                                ? Center(
                                    child: Column(
                                      mainAxisAlignment: MainAxisAlignment.center,
                                      children: [
                                        Icon(Icons.radar, size: 48, color: Colors.white.withValues(alpha: 0.15)),
                                        const SizedBox(height: 12),
                                        const Text(
                                          'Không tìm thấy công nghệ phù hợp',
                                          style: TextStyle(color: Color(0xFF64748B), fontSize: 13),
                                        ),
                                      ],
                                    ),
                                  )
                                : ListView.builder(
                                    itemCount: filtered.length,
                                    itemBuilder: (context, index) {
                                      final item = filtered[index];
                                      return _buildTechCard(context, item, controller);
                                    },
                                  ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              );
            }),
          ),
        ],
      ),
    );
  }

  Widget _buildStatPill(
    String label,
    String count,
    Color color,
    String statusKey,
    TechRadarController controller,
  ) {
    final isSelected = controller.selectedStatus.value == statusKey;
    return InkWell(
      onTap: () => controller.selectedStatus.value = statusKey,
      borderRadius: BorderRadius.circular(20),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: isSelected ? color.withValues(alpha: 0.18) : const Color(0xFF131B2E),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: isSelected ? color : const Color(0xFF1E293B),
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 8,
              height: 8,
              decoration: BoxDecoration(color: color, shape: BoxShape.circle),
            ),
            const SizedBox(width: 8),
            Text(
              label,
              style: TextStyle(
                color: isSelected ? Colors.white : const Color(0xFF94A3B8),
                fontSize: 11,
                fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
              ),
            ),
            const SizedBox(width: 6),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
              decoration: BoxDecoration(
                color: color.withValues(alpha: 0.2),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Text(
                count,
                style: TextStyle(
                  color: color,
                  fontSize: 10,
                  fontWeight: FontWeight.w800,
                  fontFamily: 'monospace',
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTechCard(
    BuildContext context,
    Map<String, dynamic> item,
    TechRadarController controller,
  ) {
    final name = item['name']?.toString() ?? 'Technology';
    final category = item['category']?.toString() ?? 'General';
    final status = (item['status']?.toString() ?? 'WATCH').toUpperCase();
    final maturity = item['maturity']?.toString() ?? 'beta';
    final potential = item['potential']?.toString() ?? 'high';
    final description = item['description']?.toString() ?? '';
    final cosaUse = item['cosa_use']?.toString() ?? 'pattern';

    Color ringColor = const Color(0xFFA855F7);
    if (status == 'ADOPT') ringColor = const Color(0xFF10B981);
    if (status == 'TRIAL') ringColor = const Color(0xFF00E5FF);
    if (status == 'ASSESS') ringColor = const Color(0xFFF59E0B);

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFF1E293B)),
      ),
      child: InkWell(
        onTap: () => RadarItemDetailDialog.show(context, item),
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    width: 10,
                    height: 10,
                    decoration: BoxDecoration(color: ringColor, shape: BoxShape.circle),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      name,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 14,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: ringColor.withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: ringColor.withValues(alpha: 0.3)),
                    ),
                    child: Text(
                      status,
                      style: TextStyle(
                        color: ringColor,
                        fontSize: 10,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  _buildTag(category, const Color(0xFF38BDF8)),
                  const SizedBox(width: 6),
                  _buildTag('Maturity: $maturity', const Color(0xFF94A3B8)),
                  const SizedBox(width: 6),
                  _buildTag('COSA: $cosaUse', const Color(0xFFA78BFA)),
                  const SizedBox(width: 6),
                  _buildTag('Potential: $potential', const Color(0xFFFBBF24)),
                ],
              ),
              if (description.isNotEmpty) ...[
                const SizedBox(height: 8),
                Text(
                  description,
                  style: TextStyle(
                    color: Colors.white.withValues(alpha: 0.7),
                    fontSize: 12,
                    height: 1.4,
                  ),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildTag(String text, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        text,
        style: TextStyle(
          color: color,
          fontSize: 10,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}
