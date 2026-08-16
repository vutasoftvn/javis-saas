import 'package:flutter/material.dart';

class DealKanbanBoard extends StatelessWidget {
  final List<dynamic> stages;
  final Function(String dealId, String newStage)? onMoveStage;
  final Function(String dealId)? onTapDeal;

  const DealKanbanBoard({
    super.key,
    required this.stages,
    this.onMoveStage,
    this.onTapDeal,
  });

  static String formatCurrency(num amount) {
    if (amount >= 1000000000) {
      return '${(amount / 1000000000).toStringAsFixed(1)} tỷ đ';
    } else if (amount >= 1000000) {
      return '${(amount / 1000000).toStringAsFixed(1)} tr đ';
    } else if (amount >= 1000) {
      return '${(amount / 1000).toStringAsFixed(0)}k đ';
    }
    return '${amount.toInt()} đ';
  }

  @override
  Widget build(BuildContext context) {
    if (stages.isEmpty) {
      return Container(
        height: 300,
        alignment: Alignment.center,
        child: const Text(
          'Chưa có cơ hội bán hàng nào trong Pipeline.',
          style: TextStyle(color: Color(0xFF64748B), fontSize: 14),
        ),
      );
    }

    return LayoutBuilder(
      builder: (context, constraints) {
        final columnCount = stages.length;
        const spacing = 12.0;
        final totalSpacing = (columnCount - 1) * spacing;
        final calculatedWidth = (constraints.maxWidth - totalSpacing) / columnCount;
        const minColWidth = 220.0;
        final isScrollable = calculatedWidth < minColWidth;
        final columnWidth = isScrollable ? 260.0 : calculatedWidth;

        final content = Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: stages.asMap().entries.map((entry) {
            final idx = entry.key;
            final stageMap = entry.value as Map<String, dynamic>;
            final isLast = idx == stages.length - 1;
            return Container(
              width: columnWidth,
              margin: EdgeInsets.only(right: isLast ? 0 : spacing),
              child: _buildKanbanColumn(context, stageMap),
            );
          }).toList(),
        );

        if (isScrollable) {
          return SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: content,
          );
        }

        return content;
      },
    );
  }

  Widget _buildKanbanColumn(BuildContext context, Map<String, dynamic> stage) {
    final stageId = stage['id']?.toString() ?? 'DISCOVERY';
    final stageName = stage['name']?.toString() ?? stageId;
    final deals = stage['deals'] as List<dynamic>? ?? [];
    final stageValue = (stage['stage_value'] as num?)?.toDouble() ?? 0.0;

    Color headerColor;
    switch (stageId) {
      case 'DISCOVERY':
        headerColor = const Color(0xFF38BDF8);
        break;
      case 'PROPOSAL':
        headerColor = const Color(0xFFF59E0B);
        break;
      case 'NEGOTIATION':
        headerColor = const Color(0xFFA855F7);
        break;
      case 'WON':
        headerColor = const Color(0xFF10B981);
        break;
      case 'LOST':
        headerColor = const Color(0xFFEF4444);
        break;
      default:
        headerColor = const Color(0xFF64748B);
    }

    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF0D1527).withValues(alpha: 0.9),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: headerColor.withValues(alpha: 0.25),
          width: 1.2,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          // Column Header
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            decoration: BoxDecoration(
              color: const Color(0xFF131D35),
              borderRadius: const BorderRadius.vertical(top: Radius.circular(15)),
              border: const Border(bottom: BorderSide(color: Color(0xFF1E293B))),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      width: 8,
                      height: 8,
                      decoration: BoxDecoration(
                        color: headerColor,
                        shape: BoxShape.circle,
                        boxShadow: [
                          BoxShadow(
                            color: headerColor.withValues(alpha: 0.8),
                            blurRadius: 6,
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        stageName,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 12,
                          fontWeight: FontWeight.w700,
                          letterSpacing: 0.5,
                        ),
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: const Color(0xFF1E293B),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        '${deals.length}',
                        style: TextStyle(
                          color: headerColor,
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 6),
                Text(
                  formatCurrency(stageValue),
                  style: const TextStyle(
                    color: Color(0xFF94A3B8),
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
          // Deals List
          Padding(
            padding: const EdgeInsets.all(10),
            child: deals.isEmpty
                ? Container(
                    height: 90,
                    alignment: Alignment.center,
                    child: const Text(
                      'Kéo thẻ vào đây',
                      style: TextStyle(
                        color: Color(0xFF475569),
                        fontSize: 12,
                        fontStyle: FontStyle.italic,
                      ),
                    ),
                  )
                : Column(
                    children: deals.map((d) {
                      final dealMap = d as Map<String, dynamic>;
                      return _buildDealCard(context, dealMap, stageId);
                    }).toList(),
                  ),
          ),
        ],
      ),
    );
  }

  Widget _buildDealCard(BuildContext context, Map<String, dynamic> deal, String currentStage) {
    final dealId = deal['id']?.toString() ?? '';
    final title = deal['title']?.toString() ?? 'Cơ hội';
    final companyName = deal['company_name']?.toString() ?? 'Doanh nghiệp';
    final value = (deal['value'] as num?)?.toDouble() ?? 0.0;
    final probability = (deal['probability'] as num?)?.toDouble() ?? 0.3;
    final nextAction = deal['next_action']?.toString() ?? '';

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF131D35),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFF1E293B)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.2),
            blurRadius: 6,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  companyName,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              PopupMenuButton<String>(
                color: const Color(0xFF0F172A),
                icon: const Icon(Icons.more_vert_rounded, size: 16, color: Color(0xFF64748B)),
                onSelected: (targetStage) {
                  onMoveStage?.call(dealId, targetStage);
                },
                itemBuilder: (context) => [
                  const PopupMenuItem(value: 'DISCOVERY', child: Text('Chuyển: Khám phá', style: TextStyle(color: Colors.white, fontSize: 12))),
                  const PopupMenuItem(value: 'PROPOSAL', child: Text('Chuyển: Đề xuất', style: TextStyle(color: Colors.white, fontSize: 12))),
                  const PopupMenuItem(value: 'NEGOTIATION', child: Text('Chuyển: Đàm phán', style: TextStyle(color: Colors.white, fontSize: 12))),
                  const PopupMenuItem(value: 'WON', child: Text('Chuyển: Thành công (Won)', style: TextStyle(color: Color(0xFF10B981), fontSize: 12, fontWeight: FontWeight.w700))),
                  const PopupMenuItem(value: 'LOST', child: Text('Chuyển: Thất bại (Lost)', style: TextStyle(color: Color(0xFFEF4444), fontSize: 12))),
                ],
              ),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            title,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              color: Color(0xFF94A3B8),
              fontSize: 11,
            ),
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: const Color(0xFF00E5FF).withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  formatCurrency(value),
                  style: const TextStyle(
                    color: Color(0xFF00E5FF),
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              const Spacer(),
              Text(
                '${(probability * 100).toInt()}% win',
                style: const TextStyle(
                  color: Color(0xFF64748B),
                  fontSize: 10,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
          if (nextAction.isNotEmpty) ...[
            const SizedBox(height: 8),
            Row(
              children: [
                const Icon(Icons.arrow_forward_rounded, size: 11, color: Color(0xFF38BDF8)),
                const SizedBox(width: 4),
                Expanded(
                  child: Text(
                    nextAction,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: Color(0xFF38BDF8),
                      fontSize: 10,
                    ),
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}
