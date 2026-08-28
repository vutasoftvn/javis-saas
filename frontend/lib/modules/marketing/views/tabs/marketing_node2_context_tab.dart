import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../../core/theme/app_theme.dart';
import '../../controllers/marketing_controller.dart';
import '../widgets/canvas_status_banner.dart';
import '../widgets/marketing_common.dart';
import '../widgets/marketing_forms.dart';

/// Node 2: Bối cảnh & Canvas Dự án (Ground Truth Canvases)
class MarketingNode2ContextTab extends GetView<MarketingController> {
  const MarketingNode2ContextTab({super.key});

  @override
  Widget build(BuildContext context) {
    return Obx(() {
      final ctx = controller.marketingContext;
      final research = (ctx['customer_research'] as Map<String, dynamic>?) ?? const {};
      final pm = (ctx['product_marketing'] as Map<String, dynamic>?) ?? const {};
      final offer = (ctx['offer_architecture'] as Map<String, dynamic>?) ?? const {};

      String read(dynamic val) {
        if (val == null) return 'Chưa cấu hình';
        if (val is String && val.trim().isEmpty) return 'Chưa cấu hình';
        return val.toString();
      }

      bool hasConfig(dynamic val) {
        if (val == null) return false;
        if (val is String) return val.trim().isNotEmpty;
        if (val is Map) return val.values.any((v) => v != null && v.toString().trim().isNotEmpty);
        return true;
      }

      return SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Banner Tự động hóa Canvas với AI
            Container(
              margin: const EdgeInsets.only(bottom: 14),
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [
                    AppTheme.primary.withValues(alpha: 0.15),
                    Colors.purpleAccent.withValues(alpha: 0.1),
                  ],
                ),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppTheme.primary.withValues(alpha: 0.35)),
              ),
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: AppTheme.primary.withValues(alpha: 0.2),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: const Icon(Icons.auto_awesome_rounded, color: AppTheme.primaryLight, size: 20),
                  ),
                  const SizedBox(width: 12),
                  const Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Tài sản Bối cảnh Chiến lược (Ground Truth Canvas)',
                          style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13.5, color: Colors.white),
                        ),
                        SizedBox(height: 2),
                        Text(
                          'AI dùng dữ liệu này làm căn cứ gốc để sản xuất bài viết, kịch bản video và tối ưu quảng cáo.',
                          style: TextStyle(fontSize: 11.5, color: AppTheme.textMutedDark),
                        ),
                      ],
                    ),
                  ),
                  ElevatedButton.icon(
                    onPressed: () => controller.autoGenerateCanvas('all'),
                    icon: const Icon(Icons.auto_awesome_rounded, size: 15),
                    label: const Text('AI Tạo toàn bộ Canvas'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppTheme.primary,
                      foregroundColor: const Color(0xFF04070E),
                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
                      textStyle: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
                    ),
                  ),
                ],
              ),
            ),

            // Governance & Revision Status Bar
            Container(
              margin: const EdgeInsets.only(bottom: 16),
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              decoration: BoxDecoration(
                color: const Color(0xFF0E131F),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: Colors.white12),
              ),
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: AppTheme.primary.withValues(alpha: 0.2),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Text(
                      'Revision #${ctx['revision'] ?? 1}',
                      style: const TextStyle(color: AppTheme.primaryLight, fontSize: 12, fontWeight: FontWeight.bold),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: (ctx['status'] == 'approved')
                          ? Colors.green.withValues(alpha: 0.2)
                          : (ctx['status'] == 'review_required')
                              ? Colors.orange.withValues(alpha: 0.2)
                              : Colors.grey.withValues(alpha: 0.2),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Text(
                      (ctx['status'] == 'approved')
                          ? 'APPROVED'
                          : (ctx['status'] == 'review_required')
                              ? 'REVIEW REQUIRED'
                              : 'DRAFT',
                      style: TextStyle(
                        color: (ctx['status'] == 'approved')
                            ? Colors.greenAccent
                            : (ctx['status'] == 'review_required')
                                ? Colors.orangeAccent
                                : Colors.white70,
                        fontSize: 11,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  if (ctx['sourceSkillId'] != null)
                    Expanded(
                      child: Text(
                        'Nguồn: ${ctx['sourceSkillId']} (v${ctx['sourceSkillVersion'] ?? '1.0.0'})',
                        style: const TextStyle(fontSize: 11.5, color: AppTheme.textMutedDark),
                        overflow: TextOverflow.ellipsis,
                      ),
                    )
                  else
                    const Expanded(
                      child: Text(
                        'Cơ sở dữ liệu tiếp thị chính thức của doanh nghiệp',
                        style: TextStyle(fontSize: 11.5, color: AppTheme.textMutedDark),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  if (ctx['status'] == 'draft')
                    OutlinedButton.icon(
                      onPressed: controller.isSubmitting.value ? null : () => controller.submitContextForReview(),
                      icon: const Icon(Icons.send_rounded, size: 14),
                      label: const Text('Gửi duyệt'),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: Colors.orangeAccent,
                        side: const BorderSide(color: Colors.orangeAccent),
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                        textStyle: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold),
                      ),
                    )
                  else if (ctx['status'] == 'review_required')
                    ElevatedButton.icon(
                      onPressed: controller.isSubmitting.value ? null : () => controller.approveContext(),
                      icon: const Icon(Icons.check_circle_outline_rounded, size: 14),
                      label: const Text('Duyệt (Founder)'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.green,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                        textStyle: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold),
                      ),
                    ),
                ],
              ),
            ),

            // 1. Customer Research Canvas §10
            Column(
              children: [
                if ((controller.canvasesStatus['customer_research'] as Map<String, dynamic>?)?.isNotEmpty ?? false)
                  CanvasStatusBanner(
                    canvasKey: 'customer_research',
                    canvasTitle: 'Customer Research',
                    statusData: (controller.canvasesStatus['customer_research'] as Map<String, dynamic>),
                    onExtractAssumptions: () => controller.extractAssumptionsAI(
                      'Customer Research: ${research.toString()}',
                      canvasType: 'customer_research',
                      canvasContent: research,
                    ),
                  ),
                _buildCanvasAccordionCard(
                  index: 0,
                  title: '1. Nghiên cứu Khách hàng (Customer Research Canvas §10)',
                  description: 'Phân tích sâu ICP, Jobs-to-be-Done, rào cản và phân loại Sự thật vs Giả thuyết.',
                  icon: Icons.people_alt_rounded,
                  color: Colors.blueAccent,
                  isExpanded: controller.activeCanvasAccordionIndex.value == 0,
                  isConfigured: hasConfig(research['segments']) || hasConfig(research['jtbd']),
                  onToggle: () => controller.toggleCanvasAccordion(0),
                  onEdit: () => showCustomerResearchForm(context, controller),
                  onAiGenerate: () => controller.autoGenerateCanvas('customer_research'),
                  content: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      MarketingKeyValue(label: 'Phân khúc khách hàng mục tiêu', value: read(research['segments'])),
                      MarketingKeyValue(label: 'Việc cần làm (Jobs-to-be-Done)', value: read(research['jtbd'])),
                      MarketingKeyValue(label: 'Nỗi đau & Rào cản mua hàng', value: read(research['pains'])),
                      MarketingKeyValue(label: 'Sự thật đã kiểm chứng (FACTS)', value: read(research['facts'])),
                      MarketingKeyValue(
                          label: 'Giả thuyết cần kiểm định (HYPOTHESES)', value: read(research['hypotheses'])),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),

            // 2. Product Marketing & Positioning §11
            Column(
              children: [
                if ((controller.canvasesStatus['product_marketing'] as Map<String, dynamic>?)?.isNotEmpty ?? false)
                  CanvasStatusBanner(
                    canvasKey: 'product_marketing',
                    canvasTitle: 'Product Marketing',
                    statusData: (controller.canvasesStatus['product_marketing'] as Map<String, dynamic>),
                    onExtractAssumptions: () => controller.extractAssumptionsAI(
                      'Product Marketing: ${pm.toString()}',
                      canvasType: 'product_marketing',
                      canvasContent: pm,
                    ),
                  ),
                _buildCanvasAccordionCard(
                  index: 1,
                  title: '2. Định vị Sản phẩm (Product Marketing Canvas §11)',
                  description: 'Xác định Ngành hàng, giải pháp thay thế, điểm khác biệt độc bản và thông điệp.',
                  icon: Icons.verified_rounded,
                  color: Colors.purpleAccent,
                  isExpanded: controller.activeCanvasAccordionIndex.value == 1,
                  isConfigured: hasConfig(pm['category']) || hasConfig(pm['differentiators']),
                  onToggle: () => controller.toggleCanvasAccordion(1),
                  onEdit: () => showProductMarketingForm(context, controller),
                  onAiGenerate: () => controller.autoGenerateCanvas('product_marketing'),
                  content: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      MarketingKeyValue(
                          label: 'Ngành hàng (Category)', value: read(pm['category'] ?? ctx['category'])),
                      MarketingKeyValue(label: 'Giải pháp thay thế hiện có', value: read(pm['alternatives'])),
                      MarketingKeyValue(
                          label: 'Điểm khác biệt độc bản (Differentiators)', value: read(pm['differentiators'])),
                      MarketingKeyValue(
                          label: 'Tuyên bố định vị (Positioning Statement)',
                          value: read(pm['positioning_statement'] ?? ctx['positioning'])),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),

            // 3. Offer Architecture Canvas §12
            Column(
              children: [
                if ((controller.canvasesStatus['offer_architecture'] as Map<String, dynamic>?)?.isNotEmpty ?? false)
                  CanvasStatusBanner(
                    canvasKey: 'offer_architecture',
                    canvasTitle: 'Offer Architecture',
                    statusData: (controller.canvasesStatus['offer_architecture'] as Map<String, dynamic>),
                    onExtractAssumptions: () => controller.extractAssumptionsAI(
                      'Offer: ${offer.toString()}',
                      canvasType: 'offer_architecture',
                      canvasContent: offer,
                    ),
                  ),
                _buildCanvasAccordionCard(
                  index: 2,
                  title: '3. Kiến trúc Ưu đãi (Offer Architecture Canvas §12)',
                  description:
                      'Thiết kế gói giá trị không thể chối từ: Core Offer + Value + Proof + Bonus + Guarantee + CTA.',
                  icon: Icons.local_offer_rounded,
                  color: Colors.amberAccent,
                  isExpanded: controller.activeCanvasAccordionIndex.value == 2,
                  isConfigured: hasConfig(offer['core_offer']) || hasConfig(offer['value']),
                  onToggle: () => controller.toggleCanvasAccordion(2),
                  onEdit: () => showOfferArchitectureForm(context, controller),
                  onAiGenerate: () => controller.autoGenerateCanvas('offer_architecture'),
                  content: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      MarketingKeyValue(label: 'Ưu đãi cốt lõi (Core Offer)', value: read(offer['core_offer'])),
                      MarketingKeyValue(label: 'Giá trị mang lại (Value)', value: read(offer['value'])),
                      MarketingKeyValue(label: 'Bảo chứng & Bằng chứng (Proof)', value: read(offer['proof'])),
                      MarketingKeyValue(label: 'Quà tặng kèm (Bonus / Add-ons)', value: read(offer['bonus'])),
                      MarketingKeyValue(
                          label: 'Cam kết đảo ngược rủi ro (Risk Reversal / Guarantee)',
                          value: read(offer['guarantee'])),
                      MarketingKeyValue(
                          label: 'Yếu tố thúc đẩy (Urgency / Scarcity)', value: read(offer['urgency'])),
                      MarketingKeyValue(label: 'Lời kêu gọi hành động (Call to Action)', value: read(offer['cta'])),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),

            // 4. Bối cảnh Thương hiệu & Ràng buộc
            Column(
              children: [
                if ((controller.canvasesStatus['brand_context'] as Map<String, dynamic>?)?.isNotEmpty ?? false)
                  CanvasStatusBanner(
                    canvasKey: 'brand_context',
                    canvasTitle: 'Brand Context',
                    statusData: (controller.canvasesStatus['brand_context'] as Map<String, dynamic>),
                  ),
                _buildCanvasAccordionCard(
                  index: 3,
                  title: '4. Bối cảnh Thương hiệu & Ràng buộc',
                  description: 'Giọng điệu thương hiệu, chính sách giá, danh sách đối thủ và các quy định ràng buộc.',
                  icon: Icons.shield_rounded,
                  color: Colors.tealAccent,
                  isExpanded: controller.activeCanvasAccordionIndex.value == 3,
                  isConfigured: hasConfig(ctx['icp']) || hasConfig(ctx['value_proposition']),
                  onToggle: () => controller.toggleCanvasAccordion(3),
                  onEdit: () => showContextForm(context, controller),
                  onAiGenerate: () => controller.autoGenerateCanvas('brand_context'),
                  content: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      MarketingKeyValue(
                          label: 'Chân dung khách hàng lý tưởng (ICP tóm tắt)', value: read(ctx['icp'])),
                      MarketingKeyValue(label: 'Tuyên ngôn giá trị', value: read(ctx['value_proposition'])),
                      MarketingKeyValue(label: 'Giọng điệu thương hiệu', value: read(ctx['brand_voice'])),
                      MarketingKeyValue(label: 'Chính sách giá', value: read(ctx['pricing'])),
                      MarketingKeyValue(label: 'Đối thủ cạnh tranh', value: read(ctx['competitors'])),
                      MarketingKeyValue(label: 'Ràng buộc vận hành', value: read(ctx['constraints'])),
                      const SizedBox(height: 6),
                      Text(
                        'Cập nhật lần cuối: ${formatDate(ctx['updated_at']?.toString())}',
                        style: const TextStyle(fontSize: 11.5, color: AppTheme.textMutedDark),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),

            // 5. Đề xuất Cập nhật Canvas từ Evidence (§41, §43)
            if (controller.canvasRevisions.isNotEmpty)
              MarketingCard(
                borderColor: Colors.deepPurpleAccent.withValues(alpha: 0.4),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.all(6),
                          decoration: BoxDecoration(
                            color: Colors.deepPurpleAccent.withValues(alpha: 0.15),
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: const Icon(Icons.history_edu_rounded, size: 16, color: Colors.deepPurpleAccent),
                        ),
                        const SizedBox(width: 10),
                        Text(
                          'Đề xuất Cập nhật Canvas từ Bằng chứng Thực tế (${controller.canvasRevisions.length})',
                          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13.5, color: Colors.white),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    ...controller.canvasRevisions.map((r) {
                      final status = r['status'] ?? 'pending_review';
                      final canvasType = r['canvas_type'] ?? '';
                      final reason = r['reason'] ?? '';
                      final isPending = status == 'pending_review';

                      return Container(
                        margin: const EdgeInsets.only(bottom: 8),
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.white.withValues(alpha: 0.03),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
                        ),
                        child: Row(
                          children: [
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(
                                    children: [
                                      MarketingChip(
                                          label: canvasType.toString().toUpperCase(), color: Colors.purpleAccent),
                                      const SizedBox(width: 8),
                                      MarketingChip(
                                        label: isPending
                                            ? 'Chờ duyệt'
                                            : (status == 'approved' ? 'Đã duyệt' : 'Từ chối'),
                                        color: isPending
                                            ? Colors.amberAccent
                                            : (status == 'approved' ? AppTheme.success : AppTheme.error),
                                      ),
                                    ],
                                  ),
                                  const SizedBox(height: 6),
                                  Text(
                                    reason,
                                    style: const TextStyle(fontSize: 12.5, color: Colors.white),
                                  ),
                                ],
                              ),
                            ),
                            if (isPending) ...[
                              const SizedBox(width: 10),
                              OutlinedButton(
                                onPressed: () => controller.rejectCanvasRevision(r['id'].toString()),
                                style: OutlinedButton.styleFrom(
                                  foregroundColor: AppTheme.error,
                                  side: BorderSide(color: AppTheme.error.withValues(alpha: 0.5)),
                                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                                ),
                                child: const Text('Từ chối', style: TextStyle(fontSize: 11.5)),
                              ),
                              const SizedBox(width: 6),
                              ElevatedButton(
                                onPressed: () => controller.approveCanvasRevision(r['id'].toString()),
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: AppTheme.success,
                                  foregroundColor: Colors.white,
                                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                                ),
                                child: const Text('Phê duyệt', style: TextStyle(fontSize: 11.5)),
                              ),
                            ],
                          ],
                        ),
                      );
                    }),
                  ],
                ),
              ),
            const SizedBox(height: 16),
          ],
        ),
      );
    });
  }

  Widget _buildCanvasAccordionCard({
    required int index,
    required String title,
    required String description,
    required IconData icon,
    required Color color,
    required bool isExpanded,
    required bool isConfigured,
    required VoidCallback onToggle,
    required VoidCallback onEdit,
    required VoidCallback onAiGenerate,
    required Widget content,
  }) {
    return MarketingCard(
      padding: EdgeInsets.zero,
      borderColor: isExpanded ? color.withValues(alpha: 0.6) : Colors.white.withValues(alpha: 0.08),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Header Bar (Clickable)
          InkWell(
            onTap: onToggle,
            borderRadius: BorderRadius.circular(14),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: color.withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: color.withValues(alpha: 0.4)),
                    ),
                    child: Icon(icon, color: color, size: 18),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Expanded(
                              child: Text(
                                title,
                                style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: Colors.white),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                            const SizedBox(width: 8),
                            MarketingChip(
                              label: isConfigured ? 'Đã cấu hình' : 'Chưa cấu hình',
                              color: isConfigured ? AppTheme.success : AppTheme.textMutedDark,
                            ),
                          ],
                        ),
                        const SizedBox(height: 3),
                        Text(
                          description,
                          style: const TextStyle(fontSize: 11.5, color: AppTheme.textMutedDark),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 12),
                  // Action buttons
                  ElevatedButton.icon(
                    onPressed: onAiGenerate,
                    icon: const Icon(Icons.auto_awesome_rounded, size: 13),
                    label: const Text('AI Tự tạo'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: color.withValues(alpha: 0.18),
                      foregroundColor: color,
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                      elevation: 0,
                      side: BorderSide(color: color.withValues(alpha: 0.4)),
                      textStyle: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.bold),
                    ),
                  ),
                  const SizedBox(width: 8),
                  ElevatedButton.icon(
                    onPressed: onEdit,
                    icon: const Icon(Icons.edit_outlined, size: 13),
                    label: const Text('Cập nhật'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppTheme.primary,
                      foregroundColor: const Color(0xFF04070E),
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                      elevation: 0,
                      textStyle: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.bold),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Icon(
                    isExpanded ? Icons.keyboard_arrow_up_rounded : Icons.keyboard_arrow_down_rounded,
                    color: Colors.white70,
                    size: 20,
                  ),
                ],
              ),
            ),
          ),
          if (isExpanded) ...[
            const Divider(color: Colors.white12, height: 1),
            Padding(
              padding: const EdgeInsets.all(16),
              child: content,
            ),
          ],
        ],
      ),
    );
  }
}
