import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../controllers/strategy_controller.dart';
import '../../../../core/theme/app_theme.dart';
import '../widgets/analysis/pestel_grid_widget.dart';
import '../widgets/analysis/swot_grid_widget.dart';
import '../widgets/analysis/tows_grid_widget.dart';
import '../dialogs/pestel_form_dialog.dart';
import '../dialogs/swot_form_dialog.dart';
import '../dialogs/tows_form_dialog.dart';
import '../dialogs/ai_analysis_modal.dart';

class AnalysisTab extends StatefulWidget {
  const AnalysisTab({super.key});

  @override
  State<AnalysisTab> createState() => _AnalysisTabState();
}

class _AnalysisTabState extends State<AnalysisTab> {
  String _activeSubTab = 'PESTEL';
  String? _selectedProjectId;

  StrategyController get controller => Get.find<StrategyController>();

  @override
  Widget build(BuildContext context) {
    return Obx(() {
      if (controller.isLoading.value) {
        return const Center(
          child: CircularProgressIndicator(color: AppTheme.primaryLight),
        );
      }

      final isDesktop = MediaQuery.of(context).size.width >= 900;

      if (!isDesktop) {
        return SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildSubBar(context),
              const SizedBox(height: 20),
              _buildMainContent(context, false),
            ],
          ),
        );
      }

      return SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 28),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(
              width: 260,
              child: _buildSubBar(context),
            ),
            const SizedBox(width: 28),
            Expanded(
              child: _buildMainContent(context, true),
            ),
          ],
        ),
      );
    });
  }

  Widget _buildSubBar(BuildContext context) {
    final subTabs = [
      {'key': 'PESTEL', 'label': 'PESTEL', 'icon': Icons.public_rounded},
      {'key': 'SWOT', 'label': 'SWOT', 'icon': Icons.grid_view_rounded},
      {'key': 'TOWS', 'label': 'TOWS', 'icon': Icons.alt_route_rounded},
      {'key': 'ALL', 'label': 'Tất cả', 'icon': Icons.view_quilt_rounded},
    ];

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDark,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              const Icon(Icons.analytics_outlined, size: 18, color: AppTheme.primaryLight),
              const SizedBox(width: 8),
              const Text('Khung Phân tích', style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: Colors.white)),
              const Spacer(),
              IconButton(
                tooltip: 'Sinh AI',
                icon: const Icon(Icons.auto_awesome_rounded, size: 18, color: AppTheme.primary),
                onPressed: () => AiAnalysisModal.show(context, controller, initialProjectId: _selectedProjectId),
              ),
            ],
          ),
          const SizedBox(height: 12),
          ...subTabs.map((tab) {
            final active = _activeSubTab == tab['key'];
            return Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: InkWell(
                onTap: () => setState(() => _activeSubTab = tab['key'] as String),
                borderRadius: BorderRadius.circular(10),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                  decoration: BoxDecoration(
                    color: active ? AppTheme.primary.withValues(alpha: 0.15) : Colors.transparent,
                    borderRadius: BorderRadius.circular(10),
                    border: active ? Border.all(color: AppTheme.primary.withValues(alpha: 0.4)) : null,
                  ),
                  child: Row(
                    children: [
                      Icon(tab['icon'] as IconData, size: 16, color: active ? AppTheme.primary : Colors.white60),
                      const SizedBox(width: 10),
                      Text(
                        tab['label'] as String,
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: active ? FontWeight.bold : FontWeight.normal,
                          color: active ? Colors.white : Colors.white70,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            );
          }),
        ],
      ),
    );
  }

  Widget _buildMainContent(BuildContext context, bool isDesktop) {
    switch (_activeSubTab) {
      case 'PESTEL':
        return PestelGridWidget(
          items: controller.pestelItems,
          isDesktop: isDesktop,
          onAddFactor: (factor) => PestelFormDialog.show(
            context,
            initialFactor: factor,
            onSubmit: (data) => controller.createPestelItem(
              factor: data['factor'] ?? 'Political',
              statement: data['statement'] ?? '',
              impact: data['impact'],
            ),
          ),
          onEditItem: (item) => PestelFormDialog.show(
            context,
            item: item,
            onSubmit: (data) => controller.updatePestelItem(
              item['id'].toString(),
              factor: data['factor'],
              statement: data['statement'],
              impact: data['impact'],
            ),
          ),
          onDeleteItem: (id) => controller.deletePestelItem(id),
        );
      case 'SWOT':
        return SwotGridWidget(
          items: controller.swotItems,
          isDesktop: isDesktop,
          onAddCategory: (category) => SwotFormDialog.show(
            context,
            initialCategory: category,
            onSubmit: (data) => controller.createSwotItem(
              category: data['category'] ?? 'Strength',
              statement: data['statement'] ?? '',
              impact: data['impact'],
            ),
          ),
          onEditItem: (item) => SwotFormDialog.show(
            context,
            item: item,
            onSubmit: (data) => controller.updateSwotItem(
              item['id'].toString(),
              category: data['category'],
              statement: data['statement'],
              impact: data['impact'],
            ),
          ),
          onDeleteItem: (id) => controller.deleteSwotItem(id),
        );
      case 'TOWS':
        return TowsGridWidget(
          options: controller.towsOptions,
          isDesktop: isDesktop,
          onAddQuadrant: (quadrant) => TowsFormDialog.show(
            context,
            initialQuadrant: quadrant,
            onSubmit: (data) => controller.createTowsOption(
              quadrant: data['quadrant'] ?? 'SO',
              title: data['title'] ?? '',
              tradeoffs: data['tradeoffs'],
            ),
          ),
          onEditOption: (option) => TowsFormDialog.show(
            context,
            option: option,
            onSubmit: (data) => controller.updateTowsOption(
              option['id'].toString(),
              quadrant: data['quadrant'],
              title: data['title'],
              tradeoffs: data['tradeoffs'],
            ),
          ),
          onDeleteOption: (id) => controller.deleteTowsOption(id),
        );
      default:
        return Column(
          children: [
            PestelGridWidget(
              items: controller.pestelItems,
              isDesktop: isDesktop,
              onAddFactor: (factor) => PestelFormDialog.show(
                context,
                initialFactor: factor,
                onSubmit: (data) => controller.createPestelItem(
                  factor: data['factor'] ?? 'Political',
                  statement: data['statement'] ?? '',
                  impact: data['impact'],
                ),
              ),
              onEditItem: (item) => PestelFormDialog.show(
                context,
                item: item,
                onSubmit: (data) => controller.updatePestelItem(
                  item['id'].toString(),
                  factor: data['factor'],
                  statement: data['statement'],
                  impact: data['impact'],
                ),
              ),
              onDeleteItem: (id) => controller.deletePestelItem(id),
            ),
            const SizedBox(height: 24),
            SwotGridWidget(
              items: controller.swotItems,
              isDesktop: isDesktop,
              onAddCategory: (category) => SwotFormDialog.show(
                context,
                initialCategory: category,
                onSubmit: (data) => controller.createSwotItem(
                  category: data['category'] ?? 'Strength',
                  statement: data['statement'] ?? '',
                  impact: data['impact'],
                ),
              ),
              onEditItem: (item) => SwotFormDialog.show(
                context,
                item: item,
                onSubmit: (data) => controller.updateSwotItem(
                  item['id'].toString(),
                  category: data['category'],
                  statement: data['statement'],
                  impact: data['impact'],
                ),
              ),
              onDeleteItem: (id) => controller.deleteSwotItem(id),
            ),
            const SizedBox(height: 24),
            TowsGridWidget(
              options: controller.towsOptions,
              isDesktop: isDesktop,
              onAddQuadrant: (quadrant) => TowsFormDialog.show(
                context,
                initialQuadrant: quadrant,
                onSubmit: (data) => controller.createTowsOption(
                  quadrant: data['quadrant'] ?? 'SO',
                  title: data['title'] ?? '',
                  tradeoffs: data['tradeoffs'],
                ),
              ),
              onEditOption: (option) => TowsFormDialog.show(
                context,
                option: option,
                onSubmit: (data) => controller.updateTowsOption(
                  option['id'].toString(),
                  quadrant: data['quadrant'],
                  title: data['title'],
                  tradeoffs: data['tradeoffs'],
                ),
              ),
              onDeleteOption: (id) => controller.deleteTowsOption(id),
            ),
          ],
        );
    }
  }
}
