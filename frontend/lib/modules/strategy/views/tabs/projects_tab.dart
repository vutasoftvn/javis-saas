import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:get/get.dart';
import '../../controllers/strategy_controller.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/theme/glassmorphism.dart';
import '../../../../core/widgets/app_modal_dialog.dart';

class ProjectsTab extends GetView<StrategyController> {
  const ProjectsTab({super.key});

  @override
  Widget build(BuildContext context) {
    return Obx(() {
      if (controller.isLoading.value) {
        return const Center(
          child: CircularProgressIndicator(color: AppTheme.primaryLight),
        );
      }

      return SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 28),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Hành trình Dự án Chiến lược (mCOSA V12)',
                      style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: Colors.white),
                    ),
                    SizedBox(height: 4),
                    Text(
                      'Phân loại AI, Lộ trình Phương pháp, Phân tích ChatGPT Terra và Cổng kiểm soát (Stage-Gate)',
                      style: TextStyle(color: AppTheme.textMutedDark, fontSize: 14),
                    ),
                  ],
                ),
                Row(
                  children: [
                    OutlinedButton.icon(
                      onPressed: () => _showPortfoliosDialog(context),
                      icon: const Icon(Icons.dashboard_customize_rounded, size: 18, color: Colors.purpleAccent),
                      label: const Text('Quản Trị Portfolio', style: TextStyle(color: Colors.purpleAccent)),
                      style: OutlinedButton.styleFrom(
                        side: BorderSide(color: Colors.purpleAccent.withValues(alpha: 0.5)),
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                      ),
                    ),
                    const SizedBox(width: 12),
                    OutlinedButton.icon(
                      onPressed: () => _showTerraDialog(context, null),
                      icon: const Icon(Icons.psychology_alt_rounded, size: 18, color: AppTheme.secondaryLight),
                      label: const Text('Terra Export/Import', style: TextStyle(color: AppTheme.secondaryLight)),
                      style: OutlinedButton.styleFrom(
                        side: BorderSide(color: AppTheme.secondaryLight.withValues(alpha: 0.5)),
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                      ),
                    ),
                    const SizedBox(width: 12),
                    OutlinedButton.icon(
                      onPressed: () => _showLivingPestelDialog(context),
                      icon: const Icon(Icons.travel_explore_rounded, size: 18, color: Colors.tealAccent),
                      label: const Text('Living PESTEL & AI', style: TextStyle(color: Colors.tealAccent)),
                      style: OutlinedButton.styleFrom(
                        side: BorderSide(color: Colors.tealAccent.withValues(alpha: 0.5)),
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                      ),
                    ),
                    const SizedBox(width: 12),
                    ElevatedButton.icon(
                      onPressed: () => _showCreateProjectDialog(context),
                      icon: const Icon(Icons.add_rounded, size: 18),
                      label: const Text('Tạo Dự án mới'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppTheme.primary,
                        foregroundColor: const Color(0xFF04070E),
                        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
                      ),
                    ),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 20),

            // CEO Next Best Actions Brief Banner (Sprint 9 Spec §37 & V12.6)
            Obx(() {
              final actions = controller.ceoNextActions;
              if (actions.isEmpty) return const SizedBox.shrink();

              return Container(
                margin: const EdgeInsets.only(bottom: 20),
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.amber.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Colors.amberAccent.withValues(alpha: 0.4)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Row(
                          children: [
                            const Icon(Icons.bolt_rounded, color: Colors.amberAccent, size: 22),
                            const SizedBox(width: 10),
                            const Text(
                              'CEO Brief — Next Best Actions (Thứ Tự Ưu Tiên Hành Động — Spec §37)',
                              style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: Colors.amberAccent),
                            ),
                          ],
                        ),
                        OutlinedButton.icon(
                          onPressed: () => controller.evaluateCeoNextActions(),
                          icon: const Icon(Icons.refresh_rounded, size: 14, color: Colors.amberAccent),
                          label: const Text('Rerank (R0/R2)', style: TextStyle(color: Colors.amberAccent, fontSize: 11)),
                          style: OutlinedButton.styleFrom(
                            side: BorderSide(color: Colors.amberAccent.withValues(alpha: 0.4)),
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    ...actions.take(3).map((act) {
                      final title = act['title'] ?? 'Hành động đề xuất';
                      final category = act['category'] ?? 'DECISION';
                      final r0Score = (act['r0_score'] as num?)?.toDouble() ?? 0.5;

                      return Container(
                        margin: const EdgeInsets.only(bottom: 8),
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                        decoration: BoxDecoration(
                          color: AppTheme.surfaceDark,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: Colors.amberAccent.withValues(alpha: 0.2)),
                        ),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Expanded(
                              child: Row(
                                children: [
                                  Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                    decoration: BoxDecoration(
                                      color: Colors.amber.withValues(alpha: 0.2),
                                      borderRadius: BorderRadius.circular(4),
                                    ),
                                    child: Text(category, style: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: Colors.amberAccent)),
                                  ),
                                  const SizedBox(width: 10),
                                  Expanded(
                                    child: Text(title, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.white), overflow: TextOverflow.ellipsis),
                                  ),
                                ],
                              ),
                            ),
                            Row(
                              children: [
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                                  decoration: BoxDecoration(
                                    color: Colors.cyanAccent.withValues(alpha: 0.15),
                                    borderRadius: BorderRadius.circular(4),
                                  ),
                                  child: Text('R0 Score: ${r0Score.toStringAsFixed(2)}', style: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: Colors.cyanAccent)),
                                ),
                                const SizedBox(width: 8),
                                ElevatedButton(
                                  onPressed: () => controller.updateNextActionStatus(act['id'], 'accepted'),
                                  style: ElevatedButton.styleFrom(
                                    backgroundColor: AppTheme.secondary,
                                    foregroundColor: const Color(0xFF04070E),
                                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                                  ),
                                  child: const Text('Chấp nhận', style: TextStyle(fontSize: 10)),
                                ),
                              ],
                            ),
                          ],
                        ),
                      );
                    }),
                  ],
                ),
              );
            }),

            // Portfolio Intelligence Detector Banner

            Obx(() {
              final detect = controller.portfolioDetection.value;
              if (detect == null) return const SizedBox.shrink();
              final needsPortfolio = detect['needs_portfolio'] == true;
              final reason = detect['reason'] ?? '';
              final portfoliosCount = controller.portfolios.length;

              return Container(
                margin: const EdgeInsets.only(bottom: 20),
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: (needsPortfolio ? Colors.purple : Colors.blue).withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: (needsPortfolio ? Colors.purpleAccent : Colors.blueAccent).withValues(alpha: 0.3),
                  ),
                ),
                child: Row(
                  children: [
                    Icon(
                      needsPortfolio ? Icons.hub_rounded : Icons.info_outline_rounded,
                      color: needsPortfolio ? Colors.purpleAccent : Colors.blueAccent,
                      size: 24,
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Text(
                                needsPortfolio
                                    ? 'Khuyến nghị Quản trị Danh mục (Portfolio Intelligence — Spec §22)'
                                    : 'Mô hình Dự án Đơn lẻ (Single Project Mode)',
                                style: TextStyle(
                                  fontWeight: FontWeight.bold,
                                  fontSize: 13,
                                  color: needsPortfolio ? Colors.purpleAccent : Colors.blueAccent,
                                ),
                              ),
                              const SizedBox(width: 8),
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                                decoration: BoxDecoration(
                                  color: (needsPortfolio ? Colors.purple : Colors.blue).withValues(alpha: 0.2),
                                  borderRadius: BorderRadius.circular(6),
                                ),
                                child: Text(
                                  'Đang có $portfoliosCount Portfolio',
                                  style: const TextStyle(fontSize: 10, color: Colors.white70),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 4),
                          Text(reason, style: const TextStyle(fontSize: 12, color: Colors.white70)),
                        ],
                      ),
                    ),
                    const SizedBox(width: 12),
                    TextButton.icon(
                      onPressed: () => _showPortfoliosDialog(context),
                      icon: const Icon(Icons.arrow_forward_rounded, size: 16, color: Colors.purpleAccent),
                      label: const Text('Xem Danh Mục & PESTEL', style: TextStyle(color: Colors.purpleAccent, fontSize: 12)),
                    ),
                  ],
                ),
              );
            }),

            // Projects List

            if (controller.projects.isEmpty)
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(36),
                decoration: BoxDecoration(
                  color: AppTheme.surfaceDark.withValues(alpha: 0.3),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: Colors.white.withValues(alpha: 0.06)),
                ),
                child: Column(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: AppTheme.primary.withValues(alpha: 0.1),
                        shape: BoxShape.circle,
                      ),
                      child: const Icon(Icons.folder_special_rounded, color: AppTheme.primaryLight, size: 36),
                    ),
                    const SizedBox(height: 16),
                    const Text('Chưa có Dự án chiến lược nào', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white)),
                    const SizedBox(height: 6),
                    const Text('Tạo dự án để bắt đầu quy trình phân loại AI và lập lộ trình phương pháp thực thi.', textAlign: TextAlign.center, style: TextStyle(color: AppTheme.textMutedDark, fontSize: 14)),
                    const SizedBox(height: 20),
                    ElevatedButton.icon(
                      onPressed: () => _showCreateProjectDialog(context),
                      icon: const Icon(Icons.add_rounded, size: 18),
                      label: const Text('Tạo Dự án Đầu Tiên'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppTheme.primary,
                        foregroundColor: const Color(0xFF04070E),
                      ),
                    ),
                  ],
                ),
              )
            else
              Column(
                children: controller.projects
                    .map((proj) => _buildProjectCard(context, proj))
                    .toList(),
              ),
          ],
        ),
      );
    });
  }

  Widget _buildProjectCard(BuildContext context, dynamic proj) {
    final projectId = proj['id']?.toString() ?? '';
    final title = proj['title'] ?? proj['name'] ?? 'Dự án không tên';
    final phase = proj['phase'] ?? 'Phase 1 - Khởi động';
    final currentGate = proj['current_gate'] ?? 'Gate 1';
    final status = proj['status'] ?? 'On Track';
    final projectType = proj['project_type'] ?? 'STRATEGIC';
    final priority = proj['strategic_priority'] ?? 'P1';
    final progress = (proj['progress'] as num?)?.toDouble() ?? 0.0;
    final initiatives = (proj['initiatives'] as List<dynamic>?) ?? [];
    final classification = proj['classification'] as Map<String, dynamic>?;
    final methodologyPlan = proj['methodology_plan'] as Map<String, dynamic>?;
    final methodologies = (methodologyPlan?['selected_methodologies'] as List<dynamic>?) ?? [];

    return Glassmorphism(
      blur: 16,
      opacity: 0.12,
      color: AppTheme.surfaceDark,
      borderRadius: BorderRadius.circular(16),
      child: Container(
        margin: const EdgeInsets.only(bottom: 20),
        padding: const EdgeInsets.all(24),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppTheme.primary.withValues(alpha: 0.25)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Top Row: Title, Project Type Badge, Phase/Gate badges, Menu
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                            decoration: BoxDecoration(
                              color: _getProjectTypeColor(projectType).withValues(alpha: 0.2),
                              borderRadius: BorderRadius.circular(6),
                              border: Border.all(color: _getProjectTypeColor(projectType).withValues(alpha: 0.6)),
                            ),
                            child: Text(
                              projectType,
                              style: TextStyle(color: _getProjectTypeColor(projectType), fontSize: 11, fontWeight: FontWeight.bold),
                            ),
                          ),
                          const SizedBox(width: 8),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                            decoration: BoxDecoration(
                              color: Colors.white12,
                              borderRadius: BorderRadius.circular(4),
                            ),
                            child: Text(priority, style: const TextStyle(color: Colors.white70, fontSize: 11, fontWeight: FontWeight.bold)),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Text(
                              title,
                              style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
                            decoration: BoxDecoration(
                              color: AppTheme.primary.withValues(alpha: 0.15),
                              borderRadius: BorderRadius.circular(6),
                            ),
                            child: Text(phase, style: const TextStyle(color: AppTheme.primaryLight, fontSize: 12, fontWeight: FontWeight.w600)),
                          ),
                          const SizedBox(width: 8),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
                            decoration: BoxDecoration(
                              color: Colors.white10,
                              borderRadius: BorderRadius.circular(6),
                            ),
                            child: Text(currentGate, style: const TextStyle(color: Colors.white70, fontSize: 12)),
                          ),
                          if (classification != null && classification['rationale'] != null) ...[
                            const SizedBox(width: 10),
                            Tooltip(
                              message: classification['rationale'].toString(),
                              child: const Icon(Icons.info_outline_rounded, size: 16, color: Colors.white54),
                            ),
                          ],
                        ],
                      ),
                    ],
                  ),
                ),
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
                      decoration: BoxDecoration(
                        color: _getStatusColor(status).withValues(alpha: 0.18),
                        borderRadius: BorderRadius.circular(20),
                        border: Border.all(color: _getStatusColor(status).withValues(alpha: 0.5)),
                      ),
                      child: Text(
                        status,
                        style: TextStyle(color: _getStatusColor(status), fontSize: 12, fontWeight: FontWeight.bold),
                      ),
                    ),
                    const SizedBox(width: 8),
                    PopupMenuButton<String>(
                      icon: const Icon(Icons.more_vert_rounded, color: Colors.white60),
                      color: AppTheme.surfaceDark,
                      itemBuilder: (ctx) => [
                        const PopupMenuItem(value: 'classify', child: Row(children: [Icon(Icons.auto_awesome_rounded, size: 18, color: AppTheme.primaryLight), SizedBox(width: 8), Text('Phân loại AI')])),
                        const PopupMenuItem(value: 'methodology', child: Row(children: [Icon(Icons.alt_route_rounded, size: 18, color: AppTheme.secondaryLight), SizedBox(width: 8), Text('Lộ trình Phương pháp')])),
                        const PopupMenuItem(value: 'terra', child: Row(children: [Icon(Icons.psychology_alt_rounded, size: 18, color: Colors.amberAccent), SizedBox(width: 8), Text('Terra Export/Import')])),
                        const PopupMenuDivider(),
                        const PopupMenuItem(value: 'add_init', child: Row(children: [Icon(Icons.lightbulb_outline_rounded, size: 18), SizedBox(width: 8), Text('Thêm Sáng kiến')])),
                        const PopupMenuItem(value: 'edit', child: Row(children: [Icon(Icons.edit_outlined, size: 18), SizedBox(width: 8), Text('Chỉnh sửa')])),
                        const PopupMenuItem(value: 'delete', child: Row(children: [Icon(Icons.delete_outline_rounded, color: AppTheme.accent, size: 18), SizedBox(width: 8), Text('Xóa Dự án', style: TextStyle(color: AppTheme.accent))])),
                      ],
                      onSelected: (val) {
                        if (val == 'classify') {
                          _showClassifyDialog(context, proj);
                        } else if (val == 'methodology') {
                          _showMethodologyDialog(context, proj);
                        } else if (val == 'terra') {
                          _showTerraDialog(context, proj);
                        } else if (val == 'add_init') {
                          _showCreateInitiativeDialog(context, projectId);
                        } else if (val == 'edit') {
                          _showEditProjectDialog(context, proj);
                        } else if (val == 'delete') {
                          controller.deleteProject(projectId);
                        }
                      },
                    ),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 16),

            // Methodology Badges
            if (methodologies.isNotEmpty) ...[
              Wrap(
                spacing: 6,
                runSpacing: 6,
                children: methodologies.map((m) => Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                  decoration: BoxDecoration(
                    color: AppTheme.secondary.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(4),
                    border: Border.all(color: AppTheme.secondary.withValues(alpha: 0.3)),
                  ),
                  child: Text(
                    m.toString(),
                    style: const TextStyle(fontSize: 10, color: AppTheme.secondaryLight, fontWeight: FontWeight.w600),
                  ),
                )).toList(),
              ),
              const SizedBox(height: 14),
            ],

            // Progress Bar
            Row(
              children: [
                Expanded(
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(8),
                    child: LinearProgressIndicator(
                      value: progress,
                      backgroundColor: const Color(0xFF0B1120),
                      valueColor: AlwaysStoppedAnimation<Color>(_getStatusColor(status)),
                      minHeight: 8,
                    ),
                  ),
                ),
                const SizedBox(width: 16),
                Text(
                  '${(progress * 100).toInt()}%',
                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: Colors.white),
                ),
              ],
            ),

            // Quick action buttons
            const SizedBox(height: 16),
            Row(
              children: [
                OutlinedButton.icon(
                  onPressed: () => _showClassifyDialog(context, proj),
                  icon: const Icon(Icons.auto_awesome_rounded, size: 14, color: AppTheme.primaryLight),
                  label: const Text('Phân loại AI', style: TextStyle(fontSize: 12, color: AppTheme.primaryLight)),
                  style: OutlinedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    side: BorderSide(color: AppTheme.primary.withValues(alpha: 0.4)),
                  ),
                ),
                const SizedBox(width: 8),
                OutlinedButton.icon(
                  onPressed: () => _showMethodologyDialog(context, proj),
                  icon: const Icon(Icons.alt_route_rounded, size: 14, color: AppTheme.secondaryLight),
                  label: const Text('Phương pháp', style: TextStyle(fontSize: 12, color: AppTheme.secondaryLight)),
                  style: OutlinedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    side: BorderSide(color: AppTheme.secondary.withValues(alpha: 0.4)),
                  ),
                ),
                const SizedBox(width: 8),
                OutlinedButton.icon(
                  onPressed: () => _showTerraDialog(context, proj),
                  icon: const Icon(Icons.psychology_alt_rounded, size: 14, color: Colors.amberAccent),
                  label: const Text('Terra Sync', style: TextStyle(fontSize: 12, color: Colors.amberAccent)),
                  style: OutlinedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    side: BorderSide(color: Colors.amber.withValues(alpha: 0.4)),
                  ),
                ),
              ],
            ),

            // Initiatives sub-list
            if (initiatives.isNotEmpty) ...[
              const SizedBox(height: 16),
              const Divider(color: Colors.white12),
              const SizedBox(height: 8),
              const Text('Sáng kiến trực thuộc:', style: TextStyle(color: Colors.white70, fontSize: 12, fontWeight: FontWeight.w600)),
              const SizedBox(height: 8),
              ...initiatives.map((init) => Padding(
                padding: const EdgeInsets.symmetric(vertical: 4),
                child: Row(
                  children: [
                    const Icon(Icons.subdirectory_arrow_right_rounded, size: 16, color: AppTheme.secondaryLight),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        init['title'] ?? '',
                        style: const TextStyle(color: Colors.white, fontSize: 13),
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                      decoration: BoxDecoration(
                        color: Colors.white10,
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        (init['status'] ?? 'active').toString().toUpperCase(),
                        style: const TextStyle(fontSize: 10, color: Colors.white70, fontWeight: FontWeight.w600),
                      ),
                    ),
                  ],
                ),
              )),
            ],
          ],
        ),
      ),
    );
  }

  Color _getProjectTypeColor(String? ptype) {
    switch (ptype?.toUpperCase()) {
      case 'NEW_BUSINESS':
        return Colors.purpleAccent;
      case 'PRODUCT':
        return Colors.cyanAccent;
      case 'GROWTH':
        return Colors.greenAccent;
      case 'TECHNICAL':
        return Colors.blueAccent;
      case 'OPERATIONAL':
        return Colors.orangeAccent;
      case 'EXPERIMENT':
        return Colors.pinkAccent;
      case 'COMPLIANCE':
        return Colors.amberAccent;
      default:
        return AppTheme.primaryLight;
    }
  }

  Color _getStatusColor(String? status) {
    switch (status?.toUpperCase()) {
      case 'ON TRACK':
      case 'ACTIVE':
        return Colors.greenAccent;
      case 'AT RISK':
        return Colors.orangeAccent;
      case 'OFF TRACK':
        return Colors.redAccent;
      case 'COMPLETED':
      case 'DONE':
        return Colors.blueAccent;
      default:
        return Colors.white70;
    }
  }

  // ====================================================================
  // V12 Journey Dialogs: Classifier, Methodology Router, Terra Sync
  // ====================================================================

  void _showClassifyDialog(BuildContext context, dynamic proj) {
    final projectId = proj['id']?.toString() ?? '';
    final title = proj['title'] ?? proj['name'] ?? '';
    final classification = proj['classification'] as Map<String, dynamic>?;

    AppModalDialog.show(
      context: context,
      title: 'Phân Loại Dự Án Bằng AI (Project Classifier)',
      subtitle: 'Tự động nhận diện loại hình, mức độ bất định và đề xuất phương pháp phù hợp',
      icon: Icons.auto_awesome_rounded,
      maxWidth: 640,
      content: StatefulBuilder(
        builder: (context, setState) => Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Dự án: $title', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: Colors.white)),
            const SizedBox(height: 14),
            if (classification != null) ...[
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: AppTheme.surfaceDark.withValues(alpha: 0.5),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Colors.white12),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text('Loại hình: ${classification['project_type']}', style: const TextStyle(color: AppTheme.primaryLight, fontWeight: FontWeight.bold)),
                        Text('Độ tin cậy: ${((classification['confidence_score'] as num?)?.toDouble() ?? 0.85) * 100}%', style: const TextStyle(color: Colors.white70, fontSize: 12)),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text('Độ sâu chiến lược: ${classification['strategic_depth']} | Độ bất định: ${classification['uncertainty_level']} | Rủi ro: ${classification['risk_level']}', style: const TextStyle(color: Colors.white70, fontSize: 12)),
                    const SizedBox(height: 8),
                    Text('Lý do đề xuất: ${classification['rationale'] ?? 'N/A'}', style: const TextStyle(color: Colors.white, fontSize: 13)),
                  ],
                ),
              ),
              const SizedBox(height: 16),
            ],
            const Text('Nhấn "Bắt đầu Phân loại AI" để DeepSeek / Router phân tích tự động.', style: TextStyle(color: AppTheme.textMutedDark, fontSize: 13)),
          ],
        ),
      ),
      actions: [
        TextButton(onPressed: () => Get.back(), child: const Text('Đóng', style: TextStyle(color: Colors.white60))),
        const SizedBox(width: 12),
        ElevatedButton.icon(
          onPressed: () async {
            Get.back();
            await controller.classifyProject(projectId);
          },
          icon: const Icon(Icons.auto_awesome_rounded, size: 16),
          label: const Text('Bắt đầu Phân loại AI'),
          style: ElevatedButton.styleFrom(
            backgroundColor: AppTheme.primary,
            foregroundColor: const Color(0xFF04070E),
          ),
        ),
      ],
    );
  }

  void _showMethodologyDialog(BuildContext context, dynamic proj) {
    final projectId = proj['id']?.toString() ?? '';
    final plan = proj['methodology_plan'] as Map<String, dynamic>?;
    final currentMethods = ((plan?['selected_methodologies'] as List<dynamic>?) ?? ['VISION_MISSION', 'PESTEL', 'SWOT', 'TOWS', 'OKR', '12WY']).map((e) => e.toString()).toSet();

    final allPrimitives = [
      'VISION_MISSION', 'PESTEL', 'SWOT', 'TOWS', 'BSC', 'OKR', '12WY',
      'STAGE_GATE', 'LEAN_VALIDATION', 'EXPERIMENT_GATE', 'PLAYBOOK',
      'SOP', 'PDCA', 'TECHNICAL_WORKFLOW', 'CLAUDE_CODE', 'CHECKLIST'
    ];

    final selected = Set<String>.from(currentMethods);

    AppModalDialog.show(
      context: context,
      title: 'Lộ Trình Phương Pháp (AI Methodology Router)',
      subtitle: 'Tùy biến các module phương pháp chiến lược và thực thi cho dự án này',
      icon: Icons.alt_route_rounded,
      maxWidth: 700,
      content: StatefulBuilder(
        builder: (context, setState) => Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Chọn các phương pháp áp dụng:', style: TextStyle(color: Colors.white70, fontSize: 13)),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: allPrimitives.map((primitive) {
                final isChecked = selected.contains(primitive);
                return FilterChip(
                  label: Text(primitive),
                  selected: isChecked,
                  selectedColor: AppTheme.secondary.withValues(alpha: 0.3),
                  checkmarkColor: AppTheme.secondaryLight,
                  backgroundColor: AppTheme.surfaceDark,
                  labelStyle: TextStyle(
                    color: isChecked ? AppTheme.secondaryLight : Colors.white70,
                    fontWeight: isChecked ? FontWeight.bold : FontWeight.normal,
                    fontSize: 12,
                  ),
                  onSelected: (val) {
                    setState(() {
                      if (val) {
                        selected.add(primitive);
                      } else {
                        selected.remove(primitive);
                      }
                    });
                  },
                );
              }).toList(),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(onPressed: () => Get.back(), child: const Text('Huỷ', style: TextStyle(color: Colors.white60))),
        const SizedBox(width: 12),
        ElevatedButton(
          onPressed: () async {
            Get.back();
            await controller.routeMethodology(projectId, customMethodologies: selected.toList());
          },
          style: ElevatedButton.styleFrom(
            backgroundColor: AppTheme.secondary,
            foregroundColor: const Color(0xFF04070E),
          ),
          child: const Text('Lưu Lộ Trình'),
        ),
      ],
    );
  }

  void _showTerraDialog(BuildContext context, dynamic proj) {
    final projectId = proj?['id']?.toString();
    final rawController = TextEditingController();
    int activeTab = 0; // 0 = Export, 1 = Import

    AppModalDialog.show(
      context: context,
      title: 'ChatGPT Terra — Phân Tích Chiến Lược (Assisted Flow)',
      subtitle: 'Quy trình tương thích gói ChatGPT Plus (\$20/tháng): Xuất prompt và nhập kết quả phân tích',
      icon: Icons.psychology_alt_rounded,
      maxWidth: 720,
      content: StatefulBuilder(
        builder: (context, setState) => Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                ChoiceChip(
                  label: const Text('1. Xuất Prompt cho Terra'),
                  selected: activeTab == 0,
                  selectedColor: AppTheme.primary.withValues(alpha: 0.25),
                  labelStyle: TextStyle(color: activeTab == 0 ? AppTheme.primaryLight : Colors.white70),
                  onSelected: (val) => setState(() => activeTab = 0),
                ),
                const SizedBox(width: 10),
                ChoiceChip(
                  label: const Text('2. Nhập Kết quả JSON từ Terra'),
                  selected: activeTab == 1,
                  selectedColor: AppTheme.secondary.withValues(alpha: 0.25),
                  labelStyle: TextStyle(color: activeTab == 1 ? AppTheme.secondaryLight : Colors.white70),
                  onSelected: (val) => setState(() => activeTab = 1),
                ),
              ],
            ),
            const SizedBox(height: 16),
            if (activeTab == 0) ...[
              const Text('Bước 1: Nhấn nút bên dưới để tạo và sao chép cấu trúc prompt phân tích toàn diện vào bộ nhớ tạm (Clipboard).', style: TextStyle(color: Colors.white70, fontSize: 13)),
              const SizedBox(height: 10),
              const Text('Bước 2: Dán prompt vào ChatGPT (hồ sơ Terra) để thực hiện suy luận sâu 1-1-3.', style: TextStyle(color: AppTheme.textMutedDark, fontSize: 12)),
              const SizedBox(height: 16),
              ElevatedButton.icon(
                onPressed: () async {
                  final exportRes = await controller.exportAnalysisPrompt(projectId: projectId);
                  if (exportRes != null && exportRes['prompt_text'] != null) {
                    await Clipboard.setData(ClipboardData(text: exportRes['prompt_text']));
                    Get.snackbar('Đã sao chép', 'Đã copy prompt ChatGPT Terra vào Clipboard!', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
                  }
                },
                icon: const Icon(Icons.copy_rounded, size: 16),
                label: const Text('Sao chép Prompt Terra vào Clipboard'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.primary,
                  foregroundColor: const Color(0xFF04070E),
                  padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                ),
              ),
            ] else ...[
              const Text('Dán khối JSON (hoặc Markdown codeblock ```json) trả về từ ChatGPT Terra vào đây:', style: TextStyle(color: Colors.white70, fontSize: 13)),
              const SizedBox(height: 12),
              TextField(
                controller: rawController,
                maxLines: 8,
                decoration: const InputDecoration(
                  hintText: '{\n  "schema_version": "1.0",\n  "pestel": [...],\n  "swot": [...],\n  "tows": [...]\n}',
                  border: OutlineInputBorder(),
                ),
                style: const TextStyle(fontFamily: 'monospace', fontSize: 12),
              ),
            ],
          ],
        ),
      ),
      actions: [
        TextButton(onPressed: () => Get.back(), child: const Text('Đóng', style: TextStyle(color: Colors.white60))),
        const SizedBox(width: 12),
        ElevatedButton(
          onPressed: () async {
            final text = rawController.text.trim();
            if (text.isEmpty) {
              Get.back();
              return;
            }
            Get.back();
            await controller.importAnalysisResult(text, projectId: projectId);
          },
          style: ElevatedButton.styleFrom(
            backgroundColor: AppTheme.secondary,
            foregroundColor: const Color(0xFF04070E),
          ),
          child: const Text('Nhập Dữ Liệu'),
        ),
      ],
    );
  }

  // ====================================================================
  // Standard Create/Edit Modals
  // ====================================================================

  void _showCreateProjectDialog(BuildContext context) {
    final titleController = TextEditingController();
    String phase = 'Phase 1 - Khởi động';
    String gate = 'Gate 1: Thẩm định ý tưởng';
    String status = 'On Track';
    String projectType = 'STRATEGIC';

    AppModalDialog.show(
      context: context,
      title: 'Tạo Dự Án Chiến Lược Mới',
      subtitle: 'Thiết lập danh mục dự án trọng điểm và quy trình phê duyệt giai đoạn',
      icon: Icons.folder_special_rounded,
      maxWidth: 620,
      content: StatefulBuilder(
        builder: (context, setState) => Column(
          children: [
            TextField(
              controller: titleController,
              decoration: const InputDecoration(
                labelText: 'Tên Dự án',
                hintText: 'Ví dụ: Tối ưu kiến trúc AI Engine Phase 2',
                prefixIcon: Icon(Icons.title_rounded, size: 20),
              ),
            ),
            const SizedBox(height: 16),
            DropdownButtonFormField<String>(
              initialValue: projectType,
              dropdownColor: AppTheme.surfaceDark,
              decoration: const InputDecoration(labelText: 'Loại hình dự án (Project Type)'),
              items: const [
                DropdownMenuItem(value: 'STRATEGIC', child: Text('Chiến lược trọng điểm (STRATEGIC)')),
                DropdownMenuItem(value: 'NEW_BUSINESS', child: Text('Kinh doanh mới / Thị trường mới (NEW_BUSINESS)')),
                DropdownMenuItem(value: 'PRODUCT', child: Text('Phát triển Sản phẩm / Tính năng (PRODUCT)')),
                DropdownMenuItem(value: 'GROWTH', child: Text('Tiếp thị & Tăng trưởng (GROWTH)')),
                DropdownMenuItem(value: 'OPERATIONAL', child: Text('Vận hành & Quy trình (OPERATIONAL)')),
                DropdownMenuItem(value: 'TECHNICAL', child: Text('Kỹ thuật & Hạ tầng (TECHNICAL)')),
                DropdownMenuItem(value: 'EXPERIMENT', child: Text('Thử nghiệm Giả thuyết (EXPERIMENT)')),
                DropdownMenuItem(value: 'COMPLIANCE', child: Text('Pháp lý & Tuân thủ (COMPLIANCE)')),
              ],
              onChanged: (v) => setState(() => projectType = v ?? 'STRATEGIC'),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: DropdownButtonFormField<String>(
                    initialValue: phase,
                    dropdownColor: AppTheme.surfaceDark,
                    decoration: const InputDecoration(labelText: 'Giai đoạn (Phase)'),
                    items: const [
                      DropdownMenuItem(value: 'Phase 1 - Khởi động', child: Text('Phase 1 - Khởi động')),
                      DropdownMenuItem(value: 'Phase 2 - Triển khai', child: Text('Phase 2 - Triển khai')),
                      DropdownMenuItem(value: 'Phase 3 - Mở rộng', child: Text('Phase 3 - Mở rộng')),
                    ],
                    onChanged: (v) => setState(() => phase = v ?? 'Phase 1 - Khởi động'),
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: DropdownButtonFormField<String>(
                    initialValue: gate,
                    dropdownColor: AppTheme.surfaceDark,
                    decoration: const InputDecoration(labelText: 'Cổng kiểm soát (Gate)'),
                    items: const [
                      DropdownMenuItem(value: 'Gate 1: Thẩm định ý tưởng', child: Text('Gate 1: Thẩm định')),
                      DropdownMenuItem(value: 'Gate 2: Thử nghiệm MVP', child: Text('Gate 2: MVP')),
                      DropdownMenuItem(value: 'Gate 3: Sẵn sàng Scale', child: Text('Gate 3: Scale')),
                    ],
                    onChanged: (v) => setState(() => gate = v ?? 'Gate 1: Thẩm định ý tưởng'),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            DropdownButtonFormField<String>(
              initialValue: status,
              dropdownColor: AppTheme.surfaceDark,
              decoration: const InputDecoration(labelText: 'Trạng thái dự án'),
              items: const [
                DropdownMenuItem(value: 'On Track', child: Text('Đúng tiến độ (On Track)')),
                DropdownMenuItem(value: 'At Risk', child: Text('Có rủi ro (At Risk)')),
                DropdownMenuItem(value: 'Off Track', child: Text('Chậm tiến độ (Off Track)')),
                DropdownMenuItem(value: 'Completed', child: Text('Đã hoàn thành (Completed)')),
              ],
              onChanged: (v) => setState(() => status = v ?? 'On Track'),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(onPressed: () => Get.back(), child: const Text('Huỷ', style: TextStyle(color: Colors.white60))),
        const SizedBox(width: 12),
        ElevatedButton(
          onPressed: () {
            final title = titleController.text.trim();
            if (title.isEmpty) return;
            controller.createProject(
              title: title,
              phase: phase,
              currentGate: gate,
              status: status,
            );
            Get.back();
          },
          style: ElevatedButton.styleFrom(
            backgroundColor: AppTheme.primary,
            foregroundColor: const Color(0xFF04070E),
          ),
          child: const Text('Tạo Dự án'),
        ),
      ],
    );
  }

  void _showEditProjectDialog(BuildContext context, dynamic proj) {
    final titleController = TextEditingController(text: proj['title'] ?? proj['name'] ?? '');
    String phase = proj['phase'] ?? 'Phase 1 - Khởi động';
    String gate = proj['current_gate'] ?? 'Gate 1: Thẩm định ý tưởng';
    String status = proj['status'] ?? 'On Track';

    AppModalDialog.show(
      context: context,
      title: 'Chỉnh Sửa Dự Án',
      subtitle: 'Cập nhật tiến độ và thông tin dự án',
      icon: Icons.edit_note_rounded,
      maxWidth: 620,
      content: StatefulBuilder(
        builder: (context, setState) => Column(
          children: [
            TextField(
              controller: titleController,
              decoration: const InputDecoration(labelText: 'Tên Dự án'),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: DropdownButtonFormField<String>(
                    initialValue: phase,
                    dropdownColor: AppTheme.surfaceDark,
                    decoration: const InputDecoration(labelText: 'Giai đoạn (Phase)'),
                    items: const [
                      DropdownMenuItem(value: 'Phase 1 - Khởi động', child: Text('Phase 1 - Khởi động')),
                      DropdownMenuItem(value: 'Phase 2 - Triển khai', child: Text('Phase 2 - Triển khai')),
                      DropdownMenuItem(value: 'Phase 3 - Mở rộng', child: Text('Phase 3 - Mở rộng')),
                    ],
                    onChanged: (v) => setState(() => phase = v ?? 'Phase 1 - Khởi động'),
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: DropdownButtonFormField<String>(
                    initialValue: gate,
                    dropdownColor: AppTheme.surfaceDark,
                    decoration: const InputDecoration(labelText: 'Cổng kiểm soát (Gate)'),
                    items: const [
                      DropdownMenuItem(value: 'Gate 1: Thẩm định ý tưởng', child: Text('Gate 1: Thẩm định')),
                      DropdownMenuItem(value: 'Gate 2: Thử nghiệm MVP', child: Text('Gate 2: MVP')),
                      DropdownMenuItem(value: 'Gate 3: Sẵn sàng Scale', child: Text('Gate 3: Scale')),
                    ],
                    onChanged: (v) => setState(() => gate = v ?? 'Gate 1: Thẩm định ý tưởng'),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            DropdownButtonFormField<String>(
              initialValue: status,
              dropdownColor: AppTheme.surfaceDark,
              decoration: const InputDecoration(labelText: 'Trạng thái dự án'),
              items: const [
                DropdownMenuItem(value: 'On Track', child: Text('Đúng tiến độ (On Track)')),
                DropdownMenuItem(value: 'At Risk', child: Text('Có rủi ro (At Risk)')),
                DropdownMenuItem(value: 'Off Track', child: Text('Chậm tiến độ (Off Track)')),
                DropdownMenuItem(value: 'Completed', child: Text('Đã hoàn thành (Completed)')),
              ],
              onChanged: (v) => setState(() => status = v ?? 'On Track'),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(onPressed: () => Get.back(), child: const Text('Huỷ', style: TextStyle(color: Colors.white60))),
        const SizedBox(width: 12),
        ElevatedButton(
          onPressed: () {
            final title = titleController.text.trim();
            if (title.isEmpty) return;
            controller.updateProject(
              proj['id'],
              title: title,
              phase: phase,
              currentGate: gate,
              status: status,
            );
            Get.back();
          },
          style: ElevatedButton.styleFrom(
            backgroundColor: AppTheme.secondary,
            foregroundColor: const Color(0xFF04070E),
          ),
          child: const Text('Lưu thay đổi'),
        ),
      ],
    );
  }

  void _showCreateInitiativeDialog(BuildContext context, String projectId) {
    final titleController = TextEditingController();

    AppModalDialog.show(
      context: context,
      title: 'Thêm Sáng Kiến Cho Dự Án',
      subtitle: 'Sáng kiến cụ thể cần triển khai trong phạm vi dự án',
      icon: Icons.lightbulb_outline_rounded,
      maxWidth: 560,
      content: TextField(
        controller: titleController,
        decoration: const InputDecoration(
          labelText: 'Tên Sáng kiến',
          hintText: 'Ví dụ: Triển khai công cụ Benchmarking tự động',
          prefixIcon: Icon(Icons.bolt_rounded, size: 20),
        ),
      ),
      actions: [
        TextButton(onPressed: () => Get.back(), child: const Text('Huỷ', style: TextStyle(color: Colors.white60))),
        const SizedBox(width: 12),
        ElevatedButton(
          onPressed: () {
            final title = titleController.text.trim();
            if (title.isEmpty) return;
            controller.createInitiative(title: title, projectId: projectId);
            Get.back();
          },
          style: ElevatedButton.styleFrom(
            backgroundColor: AppTheme.primary,
            foregroundColor: const Color(0xFF04070E),
          ),
          child: const Text('Thêm Sáng kiến'),
        ),
      ],
    );
  }

  // ====================================================================
  // mCOSA V12 Portfolio Intelligence & Shared PESTEL Dialogs (Sprint 6)
  // ====================================================================

  void _showPortfoliosDialog(BuildContext context) {
    controller.loadPortfolios();
    final nameController = TextEditingController();
    final focusController = TextEditingController();

    AppModalDialog.show(
      context: context,
      title: 'Quản Trị Danh Mục & Shared PESTEL (Portfolio Intelligence)',
      subtitle: 'Quản trị tập trung nhiều dự án, chia sẻ bối cảnh vĩ mô và ma trận tác động chéo (Spec §21–24)',
      icon: Icons.dashboard_customize_rounded,
      maxWidth: 820,
      content: Obx(() {
        final portfolios = controller.portfolios;
        final selectedId = controller.selectedPortfolioId.value;
        final projectsInPortfolio = controller.currentPortfolioProjects;
        final pestelItems = controller.currentPortfolioPestel;

        return SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Create / Select Portfolio Bar
              Row(
                children: [
                  Expanded(
                    child: DropdownButtonFormField<String>(
                      initialValue: selectedId,
                      dropdownColor: AppTheme.surfaceDark,

                      decoration: const InputDecoration(labelText: 'Chọn Portfolio đang quản trị'),
                      items: portfolios.map<DropdownMenuItem<String>>((p) {
                        return DropdownMenuItem<String>(
                          value: p['id'].toString(),
                          child: Text('${p['name']} (${p['strategic_focus'] ?? 'Đa ngành'})'),
                        );
                      }).toList(),
                      onChanged: (id) {
                        if (id != null) controller.selectPortfolio(id);
                      },
                    ),
                  ),
                  const SizedBox(width: 12),
                  ElevatedButton.icon(
                    onPressed: () => _showCreatePortfolioSubDialog(context, nameController, focusController),
                    icon: const Icon(Icons.add_rounded, size: 16),
                    label: const Text('Tạo Portfolio Mới'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.purpleAccent,
                      foregroundColor: const Color(0xFF04070E),
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 20),

              if (selectedId != null) ...[
                // Action Buttons for Portfolio
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      'Dự án trong Portfolio (${projectsInPortfolio.length})',
                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: Colors.white),
                    ),
                    Row(
                      children: [
                        OutlinedButton.icon(
                          onPressed: () => _showImpactMatrixDialog(context, selectedId),
                          icon: const Icon(Icons.grid_view_rounded, size: 16, color: Colors.cyanAccent),
                          label: const Text('Ma trận Tác động PESTEL', style: TextStyle(color: Colors.cyanAccent, fontSize: 12)),
                          style: OutlinedButton.styleFrom(
                            side: BorderSide(color: Colors.cyanAccent.withValues(alpha: 0.4)),
                          ),
                        ),
                        const SizedBox(width: 8),
                        ElevatedButton.icon(
                          onPressed: () => _showAddProjectToPortfolioDialog(context, selectedId),
                          icon: const Icon(Icons.add_link_rounded, size: 16),
                          label: const Text('Gắn Dự Án', style: TextStyle(fontSize: 12)),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: AppTheme.secondary,
                            foregroundColor: const Color(0xFF04070E),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
                const SizedBox(height: 12),

                // Projects List in Portfolio
                if (projectsInPortfolio.isEmpty)
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: AppTheme.surfaceDark,
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Center(
                      child: Text('Chưa có dự án nào trong Portfolio này. Hãy bấm "Gắn Dự Án".', style: TextStyle(color: Colors.white60, fontSize: 12)),
                    ),
                  )
                else
                  ...projectsInPortfolio.map((pp) {
                    final projName = pp['project_name'] ?? 'Dự án';
                    final priority = pp['strategic_priority'] ?? 'core';
                    final capAlloc = pp['capacity_allocation'] ?? 0.0;
                    final founderHrs = pp['founder_attention_hours'] ?? 0.0;

                    return Container(
                      margin: const EdgeInsets.only(bottom: 8),
                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                      decoration: BoxDecoration(
                        color: AppTheme.surfaceDark,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: Colors.white.withValues(alpha: 0.06)),
                      ),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Row(
                            children: [
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                                decoration: BoxDecoration(
                                  color: Colors.purple.withValues(alpha: 0.2),
                                  borderRadius: BorderRadius.circular(4),
                                ),
                                child: Text(priority.toUpperCase(), style: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: Colors.purpleAccent)),
                              ),
                              const SizedBox(width: 10),
                              Text(projName, style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.white, fontSize: 13)),
                            ],
                          ),
                          Row(
                            children: [
                              Text('Phân bổ: ${capAlloc.toStringAsFixed(0)}% | Founder: ${founderHrs.toStringAsFixed(1)}h/w', style: const TextStyle(fontSize: 11, color: Colors.white60)),
                              const SizedBox(width: 8),
                              IconButton(
                                icon: const Icon(Icons.remove_circle_outline, size: 16, color: Colors.redAccent),
                                onPressed: () => controller.removeProjectFromPortfolio(selectedId, pp['project_id']),
                              ),
                            ],
                          ),
                        ],
                      ),
                    );
                  }),

                const SizedBox(height: 20),
                // Shared PESTEL Section
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      'Shared PESTEL dùng chung (${pestelItems.length})',
                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: Colors.white),
                    ),
                    TextButton.icon(
                      onPressed: () => _showAddPortfolioPestelDialog(context, selectedId),
                      icon: const Icon(Icons.add_rounded, size: 16, color: Colors.purpleAccent),
                      label: const Text('Thêm yếu tố PESTEL', style: TextStyle(color: Colors.purpleAccent, fontSize: 12)),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                if (pestelItems.isEmpty)
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: AppTheme.surfaceDark,
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Center(
                      child: Text('Chưa có yếu tố PESTEL dùng chung. Bấm "Thêm yếu tố PESTEL".', style: TextStyle(color: Colors.white60, fontSize: 12)),
                    ),
                  )
                else
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: pestelItems.map<Widget>((item) {
                        return Container(
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                          decoration: BoxDecoration(
                            color: AppTheme.surfaceDark,
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(color: Colors.purpleAccent.withValues(alpha: 0.3)),
                          ),
                          child: Text(
                            '[${item['factor']}] ${item['statement']}',
                            style: const TextStyle(fontSize: 11, color: Colors.white70),
                          ),
                        );
                      }).toList(),
                    ),

                const SizedBox(height: 24),
                const Divider(color: Colors.white12),
                const SizedBox(height: 12),

                // Synergies & Dependencies Section (Sprint 7)
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      'Cộng Hưởng & Phụ Thuộc giữa các Dự Án (${controller.currentPortfolioSynergies.length} Cộng hưởng | ${controller.currentPortfolioDependencies.length} Phụ thuộc)',
                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: Colors.amberAccent),
                    ),
                    TextButton.icon(
                      onPressed: () => _showAddSynergyDialog(context, selectedId),
                      icon: const Icon(Icons.hub_rounded, size: 16, color: Colors.amberAccent),
                      label: const Text('Thêm Cộng Hưởng', style: TextStyle(color: Colors.amberAccent, fontSize: 12)),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                if (controller.currentPortfolioSynergies.isEmpty)
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(color: AppTheme.surfaceDark, borderRadius: BorderRadius.circular(8)),
                    child: const Center(
                      child: Text('Chưa có ghi nhận cộng hưởng năng lực / doanh thu giữa các dự án.', style: TextStyle(color: Colors.white60, fontSize: 12)),
                    ),
                  )
                else
                  ...controller.currentPortfolioSynergies.map((syn) {
                    return Container(
                      margin: const EdgeInsets.only(bottom: 6),
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                      decoration: BoxDecoration(
                        color: AppTheme.surfaceDark,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: Colors.amberAccent.withValues(alpha: 0.2)),
                      ),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Row(
                            children: [
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                decoration: BoxDecoration(
                                  color: Colors.amber.withValues(alpha: 0.2),
                                  borderRadius: BorderRadius.circular(4),
                                ),
                                child: Text(syn['synergy_type'] ?? 'SHARED', style: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: Colors.amberAccent)),
                              ),
                              const SizedBox(width: 8),
                              Text(syn['description'] ?? '', style: const TextStyle(fontSize: 12, color: Colors.white)),
                            ],
                          ),
                          IconButton(
                            icon: const Icon(Icons.delete_outline_rounded, size: 16, color: Colors.redAccent),
                            onPressed: () => controller.deletePortfolioSynergy(selectedId, syn['id']),
                          ),
                        ],
                      ),
                    );
                  }),

                const SizedBox(height: 24),
                const Divider(color: Colors.white12),
                const SizedBox(height: 12),

                // Portfolio Strategic Options Section (Sprint 7)
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      'Tùy Chọn Chiến Lược cấp Portfolio (${controller.currentPortfolioOptions.length})',
                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: Colors.greenAccent),
                    ),
                    ElevatedButton.icon(
                      onPressed: () => _showAddPortfolioOptionDialog(context, selectedId),
                      icon: const Icon(Icons.alt_route_rounded, size: 16),
                      label: const Text('Thêm Option', style: TextStyle(fontSize: 12)),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.greenAccent,
                        foregroundColor: const Color(0xFF04070E),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                if (controller.currentPortfolioOptions.isEmpty)
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(color: AppTheme.surfaceDark, borderRadius: BorderRadius.circular(8)),
                    child: const Center(
                      child: Text('Chưa có Tùy chọn chiến lược cấp Portfolio. Bấm "Thêm Option" để đánh giá.', style: TextStyle(color: Colors.white60, fontSize: 12)),
                    ),
                  )
                else
                  ...controller.currentPortfolioOptions.map((opt) {
                    final fitScore = (opt['strategic_fit_score'] as num?)?.toDouble() ?? 0.8;
                    final feasScore = (opt['feasibility_score'] as num?)?.toDouble() ?? 0.7;
                    final optStatus = opt['status'] ?? 'draft';

                    return Container(
                      margin: const EdgeInsets.only(bottom: 8),
                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                      decoration: BoxDecoration(
                        color: AppTheme.surfaceDark,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: Colors.greenAccent.withValues(alpha: 0.3)),
                      ),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(opt['title'] ?? 'Option', style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.white, fontSize: 13)),
                              const SizedBox(height: 2),
                              Text('Phù hợp: ${(fitScore * 100).toInt()}% | Khả thi: ${(feasScore * 100).toInt()}% | Rủi ro: ${opt['risk_level']}', style: const TextStyle(fontSize: 11, color: Colors.white60)),
                            ],
                          ),
                          DropdownButton<String>(
                            value: optStatus,
                            dropdownColor: AppTheme.surfaceDark,
                            style: const TextStyle(fontSize: 11, color: Colors.greenAccent),
                            underline: const SizedBox(),
                            items: const [
                              DropdownMenuItem(value: 'draft', child: Text('DRAFT')),
                              DropdownMenuItem(value: 'under_review', child: Text('REVIEW')),
                              DropdownMenuItem(value: 'selected', child: Text('SELECTED')),
                              DropdownMenuItem(value: 'rejected', child: Text('REJECTED')),
                            ],
                            onChanged: (v) {
                              if (v != null) controller.updatePortfolioOptionStatus(selectedId, opt['id'], v);
                            },
                          ),
                        ],
                      ),
                    );
                  }),

                const SizedBox(height: 24),
                const Divider(color: Colors.white12),
                const SizedBox(height: 12),

                // Founder Profile & WIP Limit Section (Sprint 8 Spec §31)
                Builder(
                  builder: (context) {
                    final fp = controller.founderProfile.value;
                    final maxWip = fp?['max_active_strategic_projects'] ?? 3;
                    final capHours = (fp?['weekly_capacity_hours'] as num?)?.toDouble() ?? 40.0;
                    final activeCount = projectsInPortfolio.length;
                    final isOverWip = activeCount > maxWip;

                    return Container(
                      padding: const EdgeInsets.all(14),
                      decoration: BoxDecoration(
                        color: isOverWip ? Colors.red.withValues(alpha: 0.15) : AppTheme.surfaceDark,
                        borderRadius: BorderRadius.circular(10),
                        border: Border.all(color: isOverWip ? Colors.redAccent.withValues(alpha: 0.5) : Colors.white12),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Row(
                                children: [
                                  Icon(Icons.shield_rounded, size: 18, color: isOverWip ? Colors.redAccent : Colors.lightBlueAccent),
                                  const SizedBox(width: 8),
                                  Text(
                                    'Founder Capacity & WIP Limit (§31)',
                                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: isOverWip ? Colors.redAccent : Colors.white),
                                  ),
                                ],
                              ),
                              TextButton.icon(
                                onPressed: () => _showEditFounderWipDialog(context, maxWip, capHours),
                                icon: const Icon(Icons.tune_rounded, size: 14, color: Colors.lightBlueAccent),
                                label: const Text('Cấu hình WIP', style: TextStyle(color: Colors.lightBlueAccent, fontSize: 11)),
                              ),
                            ],
                          ),
                          const SizedBox(height: 6),
                          Text(
                            'Số dự án active trong Portfolio: $activeCount / $maxWip (Hạn mức WIP) | Năng lực: ${capHours.toInt()}h/tuần',
                            style: TextStyle(fontSize: 12, color: isOverWip ? Colors.redAccent : Colors.white70),
                          ),
                          if (isOverWip)
                            const Padding(
                              padding: EdgeInsets.only(top: 4),
                              child: Text(
                                '⚠️ CẢNH BÁO: Số dự án đang chạy vượt quá WIP Limit! Việc kích hoạt chu kỳ danh mục sẽ bị khóa cho đến khi hạ bớt dự án active.',
                                style: TextStyle(fontSize: 11, color: Colors.redAccent, fontWeight: FontWeight.bold),
                              ),
                            ),
                        ],
                      ),
                    );
                  },
                ),

                const SizedBox(height: 24),
                const Divider(color: Colors.white12),
                const SizedBox(height: 12),

                // Portfolio 12WY Cycles Section (Sprint 8 Spec §28-30)
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      'Chu Kỳ Danh Mục 12 Tuần (Portfolio 12WY Cycles: ${controller.currentPortfolioCycles.length})',
                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: Colors.lightBlueAccent),
                    ),
                    ElevatedButton.icon(
                      onPressed: () => _showCreatePortfolioCycleDialog(context, selectedId),
                      icon: const Icon(Icons.flag_rounded, size: 16),
                      label: const Text('Tạo Chu Kỳ Mới', style: TextStyle(fontSize: 12)),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.lightBlueAccent,
                        foregroundColor: const Color(0xFF04070E),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                if (controller.currentPortfolioCycles.isEmpty)
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(color: AppTheme.surfaceDark, borderRadius: BorderRadius.circular(8)),
                    child: const Center(
                      child: Text('Chưa có chu kỳ 12WY nào cấp Portfolio. Bấm "Tạo Chu Kỳ Mới".', style: TextStyle(color: Colors.white60, fontSize: 12)),
                    ),
                  )
                else
                  ...controller.currentPortfolioCycles.map((cyc) {
                    final status = cyc['status'] ?? 'draft';
                    final isActive = status == 'active';

                    return Container(
                      margin: const EdgeInsets.only(bottom: 8),
                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                      decoration: BoxDecoration(
                        color: AppTheme.surfaceDark,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: isActive ? Colors.lightBlueAccent.withValues(alpha: 0.5) : Colors.white12),
                      ),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Row(
                            children: [
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                                decoration: BoxDecoration(
                                  color: isActive ? Colors.lightBlueAccent.withValues(alpha: 0.2) : Colors.white10,
                                  borderRadius: BorderRadius.circular(4),
                                ),
                                child: Text(status.toUpperCase(), style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: isActive ? Colors.lightBlueAccent : Colors.white60)),
                              ),
                              const SizedBox(width: 10),
                              Text(cyc['title'] ?? 'Chu kỳ 12WY', style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.white, fontSize: 13)),
                            ],
                          ),
                          if (!isActive)
                            ElevatedButton.icon(
                              onPressed: () => controller.activatePortfolioCycle(selectedId, cyc['id']),
                              icon: const Icon(Icons.play_arrow_rounded, size: 14),
                              label: const Text('Kích Hoạt (WIP Gate)', style: TextStyle(fontSize: 11)),
                              style: ElevatedButton.styleFrom(
                                backgroundColor: Colors.lightBlueAccent,
                                foregroundColor: const Color(0xFF04070E),
                                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                              ),
                            ),
                        ],
                      ),
                    );
                  }),
              ],
            ],
          ),
        );
      }),


      actions: [
        TextButton(onPressed: () => Get.back(), child: const Text('Đóng', style: TextStyle(color: Colors.white60))),
      ],
    );
  }

  void _showCreatePortfolioSubDialog(BuildContext context, TextEditingController nameCtrl, TextEditingController focusCtrl) {
    AppModalDialog.show(
      context: context,
      title: 'Tạo Danh Mục Chiến Lược (Portfolio)',
      subtitle: 'Nhóm các dự án có chung trọng tâm hoặc chia sẻ năng lực điều hành',
      icon: Icons.create_new_folder_rounded,
      maxWidth: 500,
      content: Column(
        children: [
          TextField(controller: nameCtrl, decoration: const InputDecoration(labelText: 'Tên Danh mục (Portfolio Name)')),
          const SizedBox(height: 12),
          TextField(controller: focusCtrl, decoration: const InputDecoration(labelText: 'Trọng tâm Chiến lược (Strategic Focus)')),
        ],
      ),
      actions: [
        TextButton(onPressed: () => Get.back(), child: const Text('Huỷ', style: TextStyle(color: Colors.white60))),
        const SizedBox(width: 12),
        ElevatedButton(
          onPressed: () async {
            if (nameCtrl.text.trim().isEmpty) return;
            Get.back();
            await controller.createPortfolio(
              name: nameCtrl.text.trim(),
              strategicFocus: focusCtrl.text.trim().isNotEmpty ? focusCtrl.text.trim() : null,
            );
          },
          style: ElevatedButton.styleFrom(backgroundColor: Colors.purpleAccent, foregroundColor: const Color(0xFF04070E)),
          child: const Text('Lưu Portfolio'),
        ),
      ],
    );
  }

  void _showAddProjectToPortfolioDialog(BuildContext context, String portfolioId) {
    String? selectedProjId;
    String priority = 'core';
    double capAlloc = 40.0;
    double founderHrs = 15.0;

    AppModalDialog.show(
      context: context,
      title: 'Gắn Dự Án Vào Portfolio',
      subtitle: 'Xác định thứ tự ưu tiên và phân bổ năng lực sáng lập',
      icon: Icons.link_rounded,
      maxWidth: 540,
      content: StatefulBuilder(
        builder: (context, setState) {
          final allProjects = controller.projects;
          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              DropdownButtonFormField<String>(
                initialValue: selectedProjId,
                dropdownColor: AppTheme.surfaceDark,
                decoration: const InputDecoration(labelText: 'Chọn Dự án'),
                items: allProjects.map<DropdownMenuItem<String>>((p) {
                  return DropdownMenuItem(value: p['id'].toString(), child: Text(p['title'] ?? 'Dự án'));
                }).toList(),
                onChanged: (id) => setState(() => selectedProjId = id),
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<String>(
                initialValue: priority,
                dropdownColor: AppTheme.surfaceDark,
                decoration: const InputDecoration(labelText: 'Độ Ưu Tiên Chiến Lược'),
                items: const [
                  DropdownMenuItem(value: 'core', child: Text('CORE — Dự án cốt lõi sinh dòng tiền / nền tảng')),
                  DropdownMenuItem(value: 'growth', child: Text('GROWTH — Dự án tăng trưởng mở rộng')),
                  DropdownMenuItem(value: 'experimental', child: Text('EXPERIMENTAL — Thử nghiệm đổi mới sáng tạo')),
                  DropdownMenuItem(value: 'maintenance', child: Text('MAINTENANCE — Duy trì vận hành')),
                ],
                onChanged: (v) => setState(() => priority = v ?? 'core'),
              ),
              const SizedBox(height: 14),
              Text('Phân bổ Năng lực (% Capacity): ${capAlloc.toInt()}%', style: const TextStyle(fontSize: 12, color: Colors.white70)),
              Slider(value: capAlloc, min: 0, max: 100, divisions: 20, activeColor: AppTheme.secondary, onChanged: (v) => setState(() => capAlloc = v)),
              const SizedBox(height: 8),
              Text('Thời gian Founder tập trung: ${founderHrs.toStringAsFixed(1)} giờ/tuần', style: const TextStyle(fontSize: 12, color: Colors.white70)),
              Slider(value: founderHrs, min: 0, max: 40, divisions: 20, activeColor: AppTheme.primary, onChanged: (v) => setState(() => founderHrs = v)),
            ],
          );
        },
      ),
      actions: [
        TextButton(onPressed: () => Get.back(), child: const Text('Huỷ', style: TextStyle(color: Colors.white60))),
        const SizedBox(width: 12),
        ElevatedButton(
          onPressed: () async {
            if (selectedProjId == null) return;
            Get.back();
            await controller.addProjectToPortfolio(
              portfolioId,
              projectId: selectedProjId!,
              strategicPriority: priority,
              capacityAllocation: capAlloc,
              founderAttentionHours: founderHrs,
            );
          },
          style: ElevatedButton.styleFrom(backgroundColor: AppTheme.secondary, foregroundColor: const Color(0xFF04070E)),
          child: const Text('Thêm vào Portfolio'),
        ),
      ],
    );
  }

  void _showAddPortfolioPestelDialog(BuildContext context, String portfolioId) {
    String factor = 'TECHNOLOGY';
    final statementCtrl = TextEditingController();

    AppModalDialog.show(
      context: context,
      title: 'Thêm Yếu Tố Shared PESTEL Cho Danh Mục',
      subtitle: 'Yếu tố môi trường vĩ mô tác động chéo lên nhiều dự án',
      icon: Icons.public_rounded,
      maxWidth: 540,
      content: StatefulBuilder(
        builder: (context, setState) => Column(
          children: [
            DropdownButtonFormField<String>(
              initialValue: factor,
              dropdownColor: AppTheme.surfaceDark,
              decoration: const InputDecoration(labelText: 'Khía cạnh PESTEL'),
              items: const [
                DropdownMenuItem(value: 'POLITICAL', child: Text('POLITICAL — Thể chế & Chính sách')),
                DropdownMenuItem(value: 'ECONOMIC', child: Text('ECONOMIC — Kinh tế & Thị trường')),
                DropdownMenuItem(value: 'SOCIAL', child: Text('SOCIAL — Xã hội & Hành vi người dùng')),
                DropdownMenuItem(value: 'TECHNOLOGY', child: Text('TECHNOLOGY — Công nghệ & AI')),
                DropdownMenuItem(value: 'ENVIRONMENT', child: Text('ENVIRONMENT — Môi trường & Bền vững')),
                DropdownMenuItem(value: 'LEGAL', child: Text('LEGAL — Pháp lý & Tiêu chuẩn')),
              ],
              onChanged: (v) => setState(() => factor = v ?? 'TECHNOLOGY'),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: statementCtrl,
              maxLines: 2,
              decoration: const InputDecoration(
                labelText: 'Mô tả Nhận định / Cơ hội / Thách thức',
                hintText: 'Ví dụ: Chi phí tính toán LLM giảm 10x tạo điều kiện triển khai AI Agents...',
              ),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(onPressed: () => Get.back(), child: const Text('Huỷ', style: TextStyle(color: Colors.white60))),
        const SizedBox(width: 12),
        ElevatedButton(
          onPressed: () async {
            if (statementCtrl.text.trim().isEmpty) return;
            Get.back();
            await controller.addPortfolioPestelItem(portfolioId, factor: factor, statement: statementCtrl.text.trim());
          },
          style: ElevatedButton.styleFrom(backgroundColor: Colors.purpleAccent, foregroundColor: const Color(0xFF04070E)),
          child: const Text('Lưu Yếu Tố PESTEL'),
        ),
      ],
    );
  }

  void _showImpactMatrixDialog(BuildContext context, String portfolioId) {
    controller.loadPortfolioImpactMatrix(portfolioId);

    AppModalDialog.show(
      context: context,
      title: 'Ma Trận Tác Động PESTEL Lên Từng Dự Án (Impact Matrix)',
      subtitle: 'Đánh giá mức độ tác động tích cực/tiêu cực của các yếu tố vĩ mô lên danh mục dự án (Spec §24)',
      icon: Icons.grid_view_rounded,
      maxWidth: 900,
      content: Obx(() {
        final matrix = controller.currentImpactMatrix.value;
        final projects = matrix?['projects'] as List<dynamic>? ?? [];
        final pestel = matrix?['pestel_items'] as List<dynamic>? ?? [];
        final impacts = matrix?['impacts'] as List<dynamic>? ?? [];

        if (projects.isEmpty || pestel.isEmpty) {
          return Container(
            padding: const EdgeInsets.all(24),
            decoration: BoxDecoration(
              color: AppTheme.surfaceDark,
              borderRadius: BorderRadius.circular(10),
            ),
            child: const Center(
              child: Text(
                'Cần có ít nhất 1 Dự án và 1 yếu tố Shared PESTEL trong Portfolio để hiển thị Ma trận tác động.',
                style: TextStyle(color: Colors.white60),
                textAlign: TextAlign.center,
              ),
            ),
          );
        }

        return SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: DataTable(
            headingRowColor: WidgetStateProperty.all(Colors.purple.withValues(alpha: 0.15)),
            columns: [
              const DataColumn(label: Text('Yếu tố PESTEL', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.purpleAccent))),
              ...projects.map((p) => DataColumn(
                label: Text(p['project_name'] ?? 'Dự án', style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.cyanAccent)),
              )),
            ],
            rows: pestel.map((pi) {
              final pestelId = pi['id'].toString();
              return DataRow(
                cells: [
                  DataCell(Text('[${pi['factor']}] ${pi['statement']}', style: const TextStyle(fontSize: 12, color: Colors.white70))),
                  ...projects.map((p) {
                    final projId = p['project_id'].toString();
                    final match = impacts.firstWhereOrNull(
                      (imp) => imp['project_id'].toString() == projId && imp['pestel_item_id'].toString() == pestelId,
                    );

                    final impactType = match?['impact_type'] ?? 'NEUTRAL';
                    final color = impactType == 'POSITIVE' ? Colors.greenAccent : (impactType == 'NEGATIVE' ? Colors.redAccent : Colors.white38);

                    return DataCell(
                      InkWell(
                        onTap: () => _showEditImpactCellDialog(context, projId, pestelId, p['project_name'] ?? 'Dự án', pi['statement'] ?? ''),
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                          decoration: BoxDecoration(
                            color: color.withValues(alpha: 0.15),
                            borderRadius: BorderRadius.circular(6),
                            border: Border.all(color: color.withValues(alpha: 0.4)),
                          ),
                          child: Text(impactType, style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: color)),
                        ),
                      ),
                    );
                  }),
                ],
              );
            }).toList(),
          ),
        );
      }),
      actions: [
        TextButton(onPressed: () => Get.back(), child: const Text('Đóng', style: TextStyle(color: Colors.white60))),
      ],
    );
  }

  void _showEditImpactCellDialog(BuildContext context, String projId, String pestelId, String projName, String pestelStatement) {
    String impactType = 'POSITIVE';
    String magnitude = 'HIGH';
    final analysisCtrl = TextEditingController();

    AppModalDialog.show(
      context: context,
      title: 'Đánh Giá Tác Động PESTEL → Dự Án',
      subtitle: '$projName ⟵ "$pestelStatement"',
      icon: Icons.edit_note_rounded,
      maxWidth: 520,
      content: StatefulBuilder(
        builder: (context, setState) => Column(
          children: [
            DropdownButtonFormField<String>(
              initialValue: impactType,
              dropdownColor: AppTheme.surfaceDark,
              decoration: const InputDecoration(labelText: 'Loại Tác Động'),
              items: const [
                DropdownMenuItem(value: 'POSITIVE', child: Text('POSITIVE — Tác động tích cực / Cơ hội')),
                DropdownMenuItem(value: 'NEGATIVE', child: Text('NEGATIVE — Tác động tiêu cực / Rủi ro')),
                DropdownMenuItem(value: 'NEUTRAL', child: Text('NEUTRAL — Trung tính / Ít ảnh hưởng')),
              ],
              onChanged: (v) => setState(() => impactType = v ?? 'POSITIVE'),
            ),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              initialValue: magnitude,
              dropdownColor: AppTheme.surfaceDark,
              decoration: const InputDecoration(labelText: 'Mức Độ Tác Động'),
              items: const [
                DropdownMenuItem(value: 'HIGH', child: Text('HIGH — Rất lớn')),
                DropdownMenuItem(value: 'MEDIUM', child: Text('MEDIUM — Vừa phải')),
                DropdownMenuItem(value: 'LOW', child: Text('LOW — Nhỏ')),
              ],
              onChanged: (v) => setState(() => magnitude = v ?? 'HIGH'),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: analysisCtrl,
              maxLines: 2,
              decoration: const InputDecoration(labelText: 'Phân tích & Biện pháp giảm thiểu/tận dụng'),
            ),
          ],
        ),
      ),

      actions: [
        TextButton(onPressed: () => Get.back(), child: const Text('Huỷ', style: TextStyle(color: Colors.white60))),
        const SizedBox(width: 12),
        ElevatedButton(
          onPressed: () async {
            Get.back();
            await controller.setProjectPestelImpact(
              projId,
              pestelItemId: pestelId,
              impactType: impactType,
              impactMagnitude: magnitude,
              impactAnalysis: analysisCtrl.text.trim().isNotEmpty ? analysisCtrl.text.trim() : null,
            );
          },
          style: ElevatedButton.styleFrom(backgroundColor: AppTheme.primary, foregroundColor: const Color(0xFF04070E)),
          child: const Text('Lưu Tác Động'),
        ),
      ],
    );
  }

  void _showAddSynergyDialog(BuildContext context, String portfolioId) {
    String? sourceId;
    String? targetId;
    String synergyType = 'SHARED_CAPABILITY';
    final descCtrl = TextEditingController();

    AppModalDialog.show(
      context: context,
      title: 'Ghi Nhận Cộng Hưởng Năng Lực (Synergies)',
      subtitle: 'Xác định điểm cộng hưởng giá trị/doanh thu/năng lực giữa 2 dự án trong Danh mục',
      icon: Icons.hub_rounded,
      maxWidth: 540,
      content: StatefulBuilder(
        builder: (context, setState) {
          final projects = controller.projects;
          return Column(
            children: [
              DropdownButtonFormField<String>(
                initialValue: sourceId,
                dropdownColor: AppTheme.surfaceDark,
                decoration: const InputDecoration(labelText: 'Dự án Nguồn (Source Project)'),
                items: projects.map<DropdownMenuItem<String>>((p) {
                  return DropdownMenuItem(value: p['id'].toString(), child: Text(p['title'] ?? 'Dự án A'));
                }).toList(),
                onChanged: (v) => setState(() => sourceId = v),
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<String>(
                initialValue: targetId,
                dropdownColor: AppTheme.surfaceDark,
                decoration: const InputDecoration(labelText: 'Dự án Đích (Target Project)'),
                items: projects.map<DropdownMenuItem<String>>((p) {
                  return DropdownMenuItem(value: p['id'].toString(), child: Text(p['title'] ?? 'Dự án B'));
                }).toList(),
                onChanged: (v) => setState(() => targetId = v),
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<String>(
                initialValue: synergyType,
                dropdownColor: AppTheme.surfaceDark,
                decoration: const InputDecoration(labelText: 'Loại Cộng Hưởng'),
                items: const [
                  DropdownMenuItem(value: 'SHARED_CAPABILITY', child: Text('SHARED_CAPABILITY — Dùng chung hạ tầng / nhân sự')),
                  DropdownMenuItem(value: 'REVENUE', child: Text('REVENUE — Bán chéo / Tăng giá trị khách hàng')),
                  DropdownMenuItem(value: 'COST_SAVING', child: Text('COST_SAVING — Tiết kiệm chi phí quy mô')),
                  DropdownMenuItem(value: 'DATA_NETWORK', child: Text('DATA_NETWORK — Tác động mạng lưới dữ liệu')),
                ],
                onChanged: (v) => setState(() => synergyType = v ?? 'SHARED_CAPABILITY'),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: descCtrl,
                decoration: const InputDecoration(labelText: 'Mô tả chi tiết điểm cộng hưởng'),
              ),
            ],
          );
        },
      ),
      actions: [
        TextButton(onPressed: () => Get.back(), child: const Text('Huỷ', style: TextStyle(color: Colors.white60))),
        const SizedBox(width: 12),
        ElevatedButton(
          onPressed: () async {
            if (sourceId == null || targetId == null || descCtrl.text.trim().isEmpty) return;
            Get.back();
            await controller.addPortfolioSynergy(
              portfolioId,
              sourceProjectId: sourceId!,
              targetProjectId: targetId!,
              synergyType: synergyType,
              description: descCtrl.text.trim(),
            );
          },
          style: ElevatedButton.styleFrom(backgroundColor: Colors.amberAccent, foregroundColor: const Color(0xFF04070E)),
          child: const Text('Lưu Cộng Hưởng'),
        ),
      ],
    );
  }

  void _showAddPortfolioOptionDialog(BuildContext context, String portfolioId) {
    final titleCtrl = TextEditingController();
    final descCtrl = TextEditingController();
    double fitScore = 0.8;
    double feasScore = 0.7;
    String risk = 'MEDIUM';

    AppModalDialog.show(
      context: context,
      title: 'Tạo Tùy Chọn Chiến Lược Portfolio (Portfolio Strategic Option)',
      subtitle: 'Xây dựng các phương án / hướng đi chiến lược ở quy mô danh mục dự án',
      icon: Icons.alt_route_rounded,
      maxWidth: 540,
      content: StatefulBuilder(
        builder: (context, setState) => Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            TextField(controller: titleCtrl, decoration: const InputDecoration(labelText: 'Tên Tùy Chọn Chiến Lược')),
            const SizedBox(height: 12),
            TextField(controller: descCtrl, decoration: const InputDecoration(labelText: 'Mô tả Phương án / Trade-offs')),
            const SizedBox(height: 14),
            Text('Mức độ Phù hợp Chiến lược (Strategic Fit): ${(fitScore * 100).toInt()}%', style: const TextStyle(fontSize: 12, color: Colors.white70)),
            Slider(value: fitScore, min: 0, max: 1.0, divisions: 10, activeColor: Colors.greenAccent, onChanged: (v) => setState(() => fitScore = v)),
            const SizedBox(height: 8),
            Text('Mức độ Khả thi (Feasibility Score): ${(feasScore * 100).toInt()}%', style: const TextStyle(fontSize: 12, color: Colors.white70)),
            Slider(value: feasScore, min: 0, max: 1.0, divisions: 10, activeColor: AppTheme.secondary, onChanged: (v) => setState(() => feasScore = v)),
            const SizedBox(height: 8),
            DropdownButtonFormField<String>(
              initialValue: risk,
              dropdownColor: AppTheme.surfaceDark,
              decoration: const InputDecoration(labelText: 'Mức Rủi Ro'),
              items: const [
                DropdownMenuItem(value: 'LOW', child: Text('LOW — Rủi ro thấp')),
                DropdownMenuItem(value: 'MEDIUM', child: Text('MEDIUM — Rủi ro vừa phải')),
                DropdownMenuItem(value: 'HIGH', child: Text('HIGH — Rủi ro cao')),
              ],
              onChanged: (v) => setState(() => risk = v ?? 'MEDIUM'),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(onPressed: () => Get.back(), child: const Text('Huỷ', style: TextStyle(color: Colors.white60))),
        const SizedBox(width: 12),
        ElevatedButton(
          onPressed: () async {
            if (titleCtrl.text.trim().isEmpty) return;
            Get.back();
            await controller.createPortfolioOption(
              portfolioId,
              title: titleCtrl.text.trim(),
              description: descCtrl.text.trim().isNotEmpty ? descCtrl.text.trim() : null,
              strategicFitScore: fitScore,
              feasibilityScore: feasScore,
              riskLevel: risk,
            );
          },
          style: ElevatedButton.styleFrom(backgroundColor: Colors.greenAccent, foregroundColor: const Color(0xFF04070E)),
          child: const Text('Lưu Strategic Option'),
        ),
      ],
    );
  }

  void _showEditFounderWipDialog(BuildContext context, int currentWip, double currentCapacity) {
    int wip = currentWip;
    double cap = currentCapacity;

    AppModalDialog.show(
      context: context,
      title: 'Cấu Hình WIP Limit & Founder Attention Capacity',
      subtitle: 'Quy định số lượng dự án chiến lược song song tối đa (Spec §31)',
      icon: Icons.tune_rounded,
      maxWidth: 500,
      content: StatefulBuilder(
        builder: (context, setState) => Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Hạn mức Dự án Active Tối Đa (WIP Limit): $wip dự án', style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.white, fontSize: 13)),
            const SizedBox(height: 4),
            const Text('Khuyến nghị theo phương pháp 12WY: Tối đa 2-3 dự án cốt lõi để tránh phân tán nguồn lực.', style: TextStyle(fontSize: 11, color: Colors.white60)),
            Slider(value: wip.toDouble(), min: 1, max: 10, divisions: 9, activeColor: Colors.lightBlueAccent, onChanged: (v) => setState(() => wip = v.toInt())),
            const SizedBox(height: 14),
            Text('Tổng thời gian Founder tập trung: ${cap.toInt()} giờ/tuần', style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.white, fontSize: 13)),
            Slider(value: cap, min: 10, max: 80, divisions: 14, activeColor: AppTheme.primary, onChanged: (v) => setState(() => cap = v)),
          ],
        ),
      ),
      actions: [
        TextButton(onPressed: () => Get.back(), child: const Text('Huỷ', style: TextStyle(color: Colors.white60))),
        const SizedBox(width: 12),
        ElevatedButton(
          onPressed: () async {
            Get.back();
            await controller.updateFounderProfile(weeklyCapacityHours: cap, maxActiveStrategicProjects: wip);
          },
          style: ElevatedButton.styleFrom(backgroundColor: Colors.lightBlueAccent, foregroundColor: const Color(0xFF04070E)),
          child: const Text('Lưu Cấu Hình'),
        ),
      ],
    );
  }

  void _showCreatePortfolioCycleDialog(BuildContext context, String portfolioId) {
    final titleCtrl = TextEditingController(text: 'Chu Kỳ 12 Tuần ${DateTime.now().year} Q${((DateTime.now().month - 1) ~/ 3) + 1}');

    AppModalDialog.show(
      context: context,
      title: 'Khởi Tạo Chu Kỳ 12 Tuần Cho Portfolio (12WY Cycle)',
      subtitle: 'Thiết lập chu kỳ thực thi cấp danh mục dự án',
      icon: Icons.flag_rounded,
      maxWidth: 500,
      content: TextField(
        controller: titleCtrl,
        decoration: const InputDecoration(labelText: 'Tên Chu kỳ 12 Tuần'),
      ),
      actions: [
        TextButton(onPressed: () => Get.back(), child: const Text('Huỷ', style: TextStyle(color: Colors.white60))),
        const SizedBox(width: 12),
        ElevatedButton(
          onPressed: () async {
            if (titleCtrl.text.trim().isEmpty) return;
            Get.back();
            await controller.createPortfolioCycle(portfolioId, title: titleCtrl.text.trim());
          },
          style: ElevatedButton.styleFrom(backgroundColor: Colors.lightBlueAccent, foregroundColor: const Color(0xFF04070E)),
          child: const Text('Tạo Chu Kỳ'),
        ),
      ],
    );
  }

  // ====================================================================
  // mCOSA V12 Sprint 10 — Living PESTEL & Model Profiles (Spec §48, §56)
  // ====================================================================

  void _showLivingPestelDialog(BuildContext context) {
    controller.loadPestelSignals();
    controller.loadModelProfiles();
    controller.loadModelRunsAudit();

    AppModalDialog.show(
      context: context,
      title: 'Living PESTEL & Vận Hành Mô Hình AI',
      subtitle: 'Tín hiệu vĩ mô trực tiếp (Spec §48), Model Profiles Terra/DeepSeek/Claude & Nhật ký kiểm toán (Spec §56)',
      icon: Icons.travel_explore_rounded,
      maxWidth: 780,
      content: SizedBox(
        width: double.infinity,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text('Tín Hiệu Vĩ Mô (PESTEL Signals)', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.tealAccent, fontSize: 14)),
                TextButton.icon(
                  onPressed: () => _showIngestPestelSignalDialog(context),
                  icon: const Icon(Icons.add_alert_rounded, size: 16, color: Colors.tealAccent),
                  label: const Text('Ghi Nhận Tín Hiệu Mới', style: TextStyle(color: Colors.tealAccent, fontSize: 12)),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Obx(() {
              final signals = controller.pestelSignals;
              if (signals.isEmpty) {
                return const Padding(
                  padding: EdgeInsets.symmetric(vertical: 12),
                  child: Text('Chưa có tín hiệu vĩ mô nào được ghi nhận.', style: TextStyle(color: Colors.white38, fontSize: 12)),
                );
              }
              return Container(
                constraints: const BoxConstraints(maxHeight: 160),
                decoration: BoxDecoration(
                  color: AppTheme.surfaceDark.withValues(alpha: 0.3),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: ListView.builder(
                  shrinkWrap: true,
                  itemCount: signals.length,
                  itemBuilder: (context, i) {
                    final s = signals[i];
                    final isMaterial = s['is_material_change'] == true;
                    final magColor = s['magnitude'] == 'CRITICAL' ? Colors.redAccent : (s['magnitude'] == 'HIGH' ? Colors.orangeAccent : Colors.white54);
                    return ListTile(
                      dense: true,
                      leading: Icon(isMaterial ? Icons.warning_amber_rounded : Icons.info_outline_rounded, color: magColor, size: 18),
                      title: Text(s['signal_title'] ?? '', style: const TextStyle(fontSize: 13, color: Colors.white)),
                      subtitle: Text('[${s['pestel_category']}] ${s['magnitude']}', style: TextStyle(fontSize: 11, color: magColor)),
                    );
                  },
                ),
              );
            }),
            const SizedBox(height: 20),
            const Text('Model Profiles Logic (STRATEGIC_ANALYZER / CONVERSATION_ROUTER / DEVELOPER_WORKER)', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.cyanAccent, fontSize: 14)),
            const SizedBox(height: 8),
            Obx(() {
              final profiles = controller.modelProfiles;
              if (profiles.isEmpty) {
                return const Padding(
                  padding: EdgeInsets.symmetric(vertical: 12),
                  child: Text('Đang tải Model Profiles…', style: TextStyle(color: Colors.white38, fontSize: 12)),
                );
              }
              return Column(
                children: profiles.map<Widget>((p) {
                  final active = p['is_active'] != false;
                  return Container(
                    margin: const EdgeInsets.only(bottom: 8),
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: AppTheme.surfaceDark.withValues(alpha: 0.3),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: (active ? Colors.cyanAccent : Colors.white24).withValues(alpha: 0.3)),
                    ),
                    child: Row(
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(p['display_name'] ?? p['profile'] ?? '', style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.white, fontSize: 13)),
                              const SizedBox(height: 2),
                              Text(
                                '${p['profile']} → ${p['provider']}/${p['model']}${p['configured'] == false ? " (chưa cấu hình API key)" : ""}',
                                style: TextStyle(fontSize: 11, color: p['configured'] == false ? Colors.orangeAccent : Colors.white54),
                              ),
                            ],
                          ),
                        ),
                        if (!active)
                          const Padding(
                            padding: EdgeInsets.only(right: 8),
                            child: Text('TẮT', style: TextStyle(color: Colors.redAccent, fontSize: 10, fontWeight: FontWeight.bold)),
                          ),
                        IconButton(
                          onPressed: () => _showEditModelProfileDialog(context, p),
                          icon: const Icon(Icons.tune_rounded, size: 18, color: Colors.cyanAccent),
                          tooltip: 'Cấu hình',
                        ),
                      ],
                    ),
                  );
                }).toList(),
              );
            }),
            const SizedBox(height: 20),
            const Text('Nhật Ký Kiểm Toán Mô Hình AI (Model Runs Audit)', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white70, fontSize: 14)),
            const SizedBox(height: 8),
            Obx(() {
              final audits = controller.modelRunsAudit;
              if (audits.isEmpty) {
                return const Padding(
                  padding: EdgeInsets.symmetric(vertical: 12),
                  child: Text('Chưa có nhật ký thực thi mô hình nào.', style: TextStyle(color: Colors.white38, fontSize: 12)),
                );
              }
              return Container(
                constraints: const BoxConstraints(maxHeight: 140),
                decoration: BoxDecoration(
                  color: AppTheme.surfaceDark.withValues(alpha: 0.3),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: ListView.builder(
                  shrinkWrap: true,
                  itemCount: audits.length,
                  itemBuilder: (context, i) {
                    final a = audits[i];
                    return ListTile(
                      dense: true,
                      leading: const Icon(Icons.receipt_long_rounded, size: 16, color: Colors.white38),
                      title: Text(a['model_profile'] ?? '', style: const TextStyle(fontSize: 12, color: Colors.white70)),
                      trailing: Text(
                        '${a['prompt_tokens'] ?? 0}+${a['completion_tokens'] ?? 0} tok · ${a['latency_ms'] ?? 0}ms',
                        style: const TextStyle(fontSize: 11, color: Colors.white38),
                      ),
                    );
                  },
                ),
              );
            }),
          ],
        ),
      ),
      actions: [
        TextButton(onPressed: () => Get.back(), child: const Text('Đóng', style: TextStyle(color: Colors.white60))),
      ],
    );
  }

  void _showIngestPestelSignalDialog(BuildContext context) {
    final titleCtrl = TextEditingController();
    final summaryCtrl = TextEditingController();
    String category = 'ECONOMIC';
    String magnitude = 'MEDIUM';

    AppModalDialog.show(
      context: context,
      title: 'Ghi Nhận Tín Hiệu Vĩ Mô Living PESTEL',
      subtitle: 'Tín hiệu HIGH/CRITICAL sẽ tự động kích hoạt Material Change Flow (Spec §48)',
      icon: Icons.add_alert_rounded,
      maxWidth: 520,
      content: StatefulBuilder(
        builder: (context, setState) => Column(
          children: [
            TextField(
              controller: titleCtrl,
              decoration: const InputDecoration(labelText: 'Tiêu đề tín hiệu'),
            ),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              initialValue: category,
              dropdownColor: AppTheme.surfaceDark,
              decoration: const InputDecoration(labelText: 'Yếu tố PESTEL'),
              items: const [
                DropdownMenuItem(value: 'POLITICAL', child: Text('POLITICAL')),
                DropdownMenuItem(value: 'ECONOMIC', child: Text('ECONOMIC')),
                DropdownMenuItem(value: 'SOCIAL', child: Text('SOCIAL')),
                DropdownMenuItem(value: 'TECHNOLOGICAL', child: Text('TECHNOLOGICAL')),
                DropdownMenuItem(value: 'ENVIRONMENTAL', child: Text('ENVIRONMENTAL')),
                DropdownMenuItem(value: 'LEGAL', child: Text('LEGAL')),
              ],
              onChanged: (v) => setState(() => category = v ?? 'ECONOMIC'),
            ),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              initialValue: magnitude,
              dropdownColor: AppTheme.surfaceDark,
              decoration: const InputDecoration(labelText: 'Mức Độ Biến Động'),
              items: const [
                DropdownMenuItem(value: 'LOW', child: Text('LOW')),
                DropdownMenuItem(value: 'MEDIUM', child: Text('MEDIUM')),
                DropdownMenuItem(value: 'HIGH', child: Text('HIGH — Kích hoạt Material Change')),
                DropdownMenuItem(value: 'CRITICAL', child: Text('CRITICAL — Kích hoạt Material Change')),
              ],
              onChanged: (v) => setState(() => magnitude = v ?? 'MEDIUM'),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: summaryCtrl,
              maxLines: 2,
              decoration: const InputDecoration(labelText: 'Tóm tắt bối cảnh (tuỳ chọn)'),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(onPressed: () => Get.back(), child: const Text('Huỷ', style: TextStyle(color: Colors.white60))),
        const SizedBox(width: 12),
        ElevatedButton(
          onPressed: () async {
            if (titleCtrl.text.trim().isEmpty) return;
            Get.back();
            await controller.ingestPestelSignal(
              signalTitle: titleCtrl.text.trim(),
              pestelCategory: category,
              magnitude: magnitude,
              signalSummary: summaryCtrl.text.trim().isNotEmpty ? summaryCtrl.text.trim() : null,
            );
          },
          style: ElevatedButton.styleFrom(backgroundColor: Colors.tealAccent, foregroundColor: const Color(0xFF04070E)),
          child: const Text('Ghi Nhận Tín Hiệu'),
        ),
      ],
    );
  }

  void _showEditModelProfileDialog(BuildContext context, dynamic profile) {
    final nameCtrl = TextEditingController(text: profile['display_name'] ?? profile['profile'] ?? '');
    double temperature = (profile['temperature'] as num?)?.toDouble() ?? 0.7;
    bool isActive = profile['is_active'] != false;

    AppModalDialog.show(
      context: context,
      title: 'Cấu Hình Model Profile — ${profile['profile']}',
      subtitle: 'Điều chỉnh tên hiển thị, độ sáng tạo (temperature) và trạng thái kích hoạt',
      icon: Icons.tune_rounded,
      maxWidth: 480,
      content: StatefulBuilder(
        builder: (context, setState) => Column(
          children: [
            TextField(
              controller: nameCtrl,
              decoration: const InputDecoration(labelText: 'Tên hiển thị'),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                const Text('Temperature', style: TextStyle(color: Colors.white70, fontSize: 13)),
                const Spacer(),
                Text(temperature.toStringAsFixed(2), style: const TextStyle(color: Colors.cyanAccent, fontSize: 13)),
              ],
            ),
            Slider(
              value: temperature,
              min: 0.0,
              max: 1.0,
              divisions: 20,
              activeColor: Colors.cyanAccent,
              onChanged: (v) => setState(() => temperature = v),
            ),
            SwitchListTile(
              value: isActive,
              onChanged: (v) => setState(() => isActive = v),
              title: const Text('Kích hoạt Profile', style: TextStyle(color: Colors.white, fontSize: 13)),
              activeThumbColor: Colors.cyanAccent,
              contentPadding: EdgeInsets.zero,
            ),
          ],
        ),
      ),
      actions: [
        TextButton(onPressed: () => Get.back(), child: const Text('Huỷ', style: TextStyle(color: Colors.white60))),
        const SizedBox(width: 12),
        ElevatedButton(
          onPressed: () async {
            Get.back();
            await controller.updateModelProfile(
              profile['profile'].toString(),
              displayName: nameCtrl.text.trim().isNotEmpty ? nameCtrl.text.trim() : null,
              temperature: temperature,
              isActive: isActive,
            );
          },
          style: ElevatedButton.styleFrom(backgroundColor: Colors.cyanAccent, foregroundColor: const Color(0xFF04070E)),
          child: const Text('Lưu Cấu Hình'),
        ),
      ],
    );
  }
}



