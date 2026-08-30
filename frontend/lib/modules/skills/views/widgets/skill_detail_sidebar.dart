import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../../core/theme/app_theme.dart';
import '../../controllers/skill_registry_controller.dart';

/// Sidebar chi tiết Kỹ năng bên phải - Hỗ trợ xem và chỉnh sửa trực tiếp (Inline Edit)
class SkillDetailSidebar extends StatefulWidget {
  final Map<String, dynamic> skill;
  final VoidCallback onClose;

  const SkillDetailSidebar({
    super.key,
    required this.skill,
    required this.onClose,
  });

  @override
  State<SkillDetailSidebar> createState() => _SkillDetailSidebarState();
}

class _SkillDetailSidebarState extends State<SkillDetailSidebar> {
  bool _isEditing = false;
  late TextEditingController _nameController;
  late TextEditingController _descController;
  late TextEditingController _instructionsController;
  late TextEditingController _toolsController;

  @override
  void initState() {
    super.initState();
    _initControllers();
  }

  @override
  void didUpdateWidget(covariant SkillDetailSidebar oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.skill['id'] != widget.skill['id'] || oldWidget.skill['updated_at'] != widget.skill['updated_at']) {
      _initControllers();
      _isEditing = false;
    }
  }

  void _initControllers() {
    _nameController = TextEditingController(text: widget.skill['name']?.toString() ?? '');
    _descController = TextEditingController(text: widget.skill['description']?.toString() ?? '');
    _instructionsController = TextEditingController(text: widget.skill['instructions']?.toString() ?? '');
    final tools = (widget.skill['tool_permissions'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [];
    _toolsController = TextEditingController(text: tools.join(', '));
  }

  @override
  void dispose() {
    _nameController.dispose();
    _descController.dispose();
    _instructionsController.dispose();
    _toolsController.dispose();
    super.dispose();
  }

  Future<void> _handleSave() async {
    final controller = Get.find<SkillRegistryController>();
    final skillId = widget.skill['id']?.toString() ?? '';
    final toolsList = _toolsController.text
        .split(',')
        .map((e) => e.trim())
        .where((e) => e.isNotEmpty)
        .toList();

    await controller.updateSkill(
      skillId: skillId,
      name: _nameController.text.trim(),
      description: _descController.text.trim(),
      instructions: _instructionsController.text.trim(),
      toolPermissions: toolsList,
    );

    setState(() {
      _isEditing = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    final controller = Get.find<SkillRegistryController>();
    final skill = widget.skill;
    final name = skill['name']?.toString() ?? 'Kỹ năng';
    final domain = (skill['domain']?.toString() ?? 'general').toLowerCase();
    final status = (skill['status']?.toString() ?? 'candidate').toLowerCase();
    final version = skill['version']?.toString() ?? '1.0.0';
    final description = skill['description']?.toString() ?? 'Không có mô tả.';
    final instructions = skill['instructions']?.toString() ?? 'Không có hướng dẫn SOP.';
    final successRate = ((skill['success_rate'] as num?)?.toDouble() ?? 1.0) * 100;
    final usageCount = (skill['usage_count'] as num?)?.toInt() ?? 0;
    final positive = (skill['positive_feedback'] as num?)?.toInt() ?? 0;
    final negative = (skill['negative_feedback'] as num?)?.toInt() ?? 0;
    final createdBy = skill['created_by_agent']?.toString() ?? 'human_admin';
    final approvedBy = skill['approved_by_user_id']?.toString();
    final skillId = skill['id']?.toString() ?? '';
    final tools = (skill['required_capabilities'] as List<dynamic>?)?.map((e) => e.toString()).toList() ??
        (skill['tool_permissions'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [];

    IconData domainIcon;
    Color domainColor;
    String domainLabel;

    switch (domain) {
      case 'sales':
        domainIcon = Icons.point_of_sale_rounded;
        domainColor = Colors.blueAccent;
        domainLabel = 'BÁN HÀNG & CRM';
        break;
      case 'marketing':
        domainIcon = Icons.campaign_rounded;
        domainColor = Colors.purpleAccent;
        domainLabel = 'MARKETING & LEADS';
        break;
      case 'finance':
        domainIcon = Icons.account_balance_wallet_rounded;
        domainColor = Colors.amberAccent;
        domainLabel = 'TÀI CHÍNH TT68';
        break;
      case 'legal':
        domainIcon = Icons.gavel_rounded;
        domainColor = Colors.pinkAccent;
        domainLabel = 'PHÁP LÝ & HỢP ĐỒNG';
        break;
      case 'operations':
        domainIcon = Icons.precision_manufacturing_rounded;
        domainColor = const Color(0xFF10B981);
        domainLabel = 'VẬN HÀNH';
        break;
      case 'tech':
        domainIcon = Icons.terminal_rounded;
        domainColor = const Color(0xFF00E5FF);
        domainLabel = 'KỸ THUẬT';
        break;
      case 'strategy':
        domainIcon = Icons.insights_rounded;
        domainColor = const Color(0xFF38BDF8);
        domainLabel = 'CHIẾN LƯỢC';
        break;
      default:
        domainIcon = Icons.psychology_rounded;
        domainColor = Colors.tealAccent;
        domainLabel = domain.toUpperCase();
    }

    Color statusColor = const Color(0xFF94A3B8);
    String statusLabel = 'ỨNG VIÊN';
    if (status == 'candidate' || status == 'draft') {
      statusColor = const Color(0xFFF59E0B);
      statusLabel = 'CANDIDATE';
    } else if (status == 'evaluation' || status == 'evaluated') {
      statusColor = const Color(0xFF00E5FF);
      statusLabel = 'EVALUATION';
    } else if (status == 'active' || status == 'published' || status == 'approved') {
      statusColor = const Color(0xFF10B981);
      statusLabel = 'CHÍNH THỨC';
    } else if (status == 'deprecated' || status == 'retired') {
      statusColor = const Color(0xFFEF4444);
      statusLabel = 'ĐÃ NGƯNG';
    }

    final origin = skill['origin']?.toString() ?? skill['references']?['origin']?.toString();
    final adaptedFromSha = skill['adapted_from_sha']?.toString() ?? skill['references']?['upstream_commit']?.toString();
    final definitionHash = skill['definition_hash']?.toString();

    return Container(
      width: 470,
      decoration: BoxDecoration(
        color: AppTheme.surfaceDark,
        border: Border(
          left: BorderSide(color: AppTheme.borderDark, width: 1.5),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // ── Sidebar Header ────────────────────────────────────────
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: BoxDecoration(
              color: const Color(0xFF0B1222),
              border: Border(
                bottom: BorderSide(color: AppTheme.borderDark),
              ),
            ),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(7),
                  decoration: BoxDecoration(
                    color: domainColor.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Icon(domainIcon, color: domainColor, size: 19),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        name,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 15.5,
                          fontWeight: FontWeight.bold,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      const SizedBox(height: 2),
                      Text(
                        '$domainLabel • v$version',
                        style: TextStyle(
                          color: domainColor,
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2.5),
                  decoration: BoxDecoration(
                    color: statusColor.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: statusColor.withValues(alpha: 0.3)),
                  ),
                  child: Text(
                    statusLabel,
                    style: TextStyle(
                      color: statusColor,
                      fontSize: 10.5,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
                const SizedBox(width: 6),
                IconButton(
                  icon: const Icon(Icons.close_rounded, size: 20, color: AppTheme.textMutedDark),
                  tooltip: 'Đóng chi tiết',
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(minWidth: 30, minHeight: 30),
                  onPressed: widget.onClose,
                ),
              ],
            ),
          ),

          // ── Scrollable Body (View or Edit Mode) ────────────────────
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: _isEditing ? _buildEditForm() : _buildViewContent(
                name: name,
                description: description,
                instructions: instructions,
                tools: tools,
                successRate: successRate,
                usageCount: usageCount,
                positive: positive,
                negative: negative,
                statusColor: statusColor,
                skillId: skillId,
                createdBy: createdBy,
                approvedBy: approvedBy,
                origin: origin,
                adaptedFromSha: adaptedFromSha,
                definitionHash: definitionHash,
              ),
            ),
          ),

          // ── Action Footer ─────────────────────────────────────────
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: BoxDecoration(
              color: const Color(0xFF0B1222),
              border: Border(
                top: BorderSide(color: AppTheme.borderDark),
              ),
            ),
            child: _isEditing
                ? Row(
                    children: [
                      OutlinedButton(
                        style: OutlinedButton.styleFrom(
                          foregroundColor: AppTheme.textMutedDark,
                          side: const BorderSide(color: Color(0xFF334155)),
                          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                        ),
                        onPressed: () {
                          _initControllers();
                          setState(() {
                            _isEditing = false;
                          });
                        },
                        child: const Text('Hủy bỏ', style: TextStyle(fontSize: 13)),
                      ),
                      const Spacer(),
                      ElevatedButton.icon(
                        style: ElevatedButton.styleFrom(
                          backgroundColor: AppTheme.primary,
                          foregroundColor: const Color(0xFF04070E),
                          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                        ),
                        icon: const Icon(Icons.check_rounded, size: 16),
                        label: const Text('Lưu thay đổi', style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold)),
                        onPressed: _handleSave,
                      ),
                    ],
                  )
                : Row(
                    children: [
                      // Edit Button
                      OutlinedButton.icon(
                        style: OutlinedButton.styleFrom(
                          foregroundColor: AppTheme.primaryLight,
                          side: BorderSide(color: AppTheme.primaryLight.withValues(alpha: 0.5)),
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                        ),
                        icon: const Icon(Icons.edit_note_rounded, size: 16),
                        label: const Text('Chỉnh sửa SOP', style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600)),
                        onPressed: () {
                          setState(() {
                            _isEditing = true;
                          });
                        },
                      ),
                      const SizedBox(width: 8),
                      if (status != 'deprecated') ...[
                        OutlinedButton.icon(
                          style: OutlinedButton.styleFrom(
                            foregroundColor: const Color(0xFFEF4444),
                            side: const BorderSide(color: Color(0xFFEF4444)),
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 9),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                          ),
                          icon: const Icon(Icons.archive_outlined, size: 14),
                          label: const Text('Ngưng dùng', style: TextStyle(fontSize: 12.5)),
                          onPressed: () {
                            controller.deprecateSkill(skillId, reason: 'Ngưng dùng theo yêu cầu quản trị');
                            widget.onClose();
                          },
                        ),
                        const SizedBox(width: 8),
                      ],
                      const Spacer(),
                      if (status == 'candidate' || status == 'evaluation') ...[
                        ElevatedButton.icon(
                          style: ElevatedButton.styleFrom(
                            backgroundColor: const Color(0xFF00E5FF),
                            foregroundColor: Colors.black,
                            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                          ),
                          icon: const Icon(Icons.science_outlined, size: 15),
                          label: const Text('Eval Test', style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.bold)),
                          onPressed: () {
                            controller.evaluateSkill(skillId, 0.95);
                          },
                        ),
                        const SizedBox(width: 8),
                      ],
                      if (status != 'active') ...[
                        ElevatedButton.icon(
                          style: ElevatedButton.styleFrom(
                            backgroundColor: const Color(0xFF10B981),
                            foregroundColor: Colors.white,
                            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                          ),
                          icon: const Icon(Icons.check_circle_outline, size: 15),
                          label: const Text('Duyệt Active', style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.bold)),
                          onPressed: () {
                            controller.promoteSkill(skillId);
                          },
                        ),
                      ],
                    ],
                  ),
          ),
        ],
      ),
    );
  }

  Widget _buildViewContent({
    required String name,
    required String description,
    required String instructions,
    required List<String> tools,
    required double successRate,
    required int usageCount,
    required int positive,
    required int negative,
    required Color statusColor,
    required String skillId,
    required String createdBy,
    required String? approvedBy,
    String? origin,
    String? adaptedFromSha,
    String? definitionHash,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Performance Metrics Strip
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          decoration: BoxDecoration(
            color: const Color(0xFF0F172A),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: Colors.white.withValues(alpha: 0.05)),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              _buildMetric('Tỷ lệ thành công', '${successRate.toInt()}%', statusColor),
              _buildDivider(),
              _buildMetric('Số lần gọi', '$usageCount', Colors.white),
              _buildDivider(),
              _buildMetric('Đánh giá tốt', '+$positive', const Color(0xFF34D399)),
              _buildDivider(),
              _buildMetric('Phản hồi lỗi', '-$negative', const Color(0xFFF87171)),
            ],
          ),
        ),
        const SizedBox(height: 14),

        // Metadata Info
        Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: Colors.white.withValues(alpha: 0.02),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: Colors.white.withValues(alpha: 0.04)),
          ),
          child: Column(
            children: [
              _buildInfoRow('Mã Kỹ năng (ID)', skillId.isNotEmpty ? skillId : '—'),
              const SizedBox(height: 4),
              _buildInfoRow('Giai đoạn (Stages)', (widget.skill['project_stages'] as List<dynamic>?)?.join(', ') ?? '—'),
              const SizedBox(height: 4),
              _buildInfoRow('Quyền tự chủ (Autonomy)', '${widget.skill['autonomy_ceiling'] ?? 'L0_OBSERVE'} (${widget.skill['side_effect_class'] ?? 'R'})'),
              const SizedBox(height: 4),
              _buildInfoRow('Bằng chứng tối thiểu', '${widget.skill['min_source_refs'] ?? 0} refs'),
              const SizedBox(height: 4),
              _buildInfoRow('Nguồn gốc (Origin)', origin != null && origin.isNotEmpty ? origin : createdBy),
              if (adaptedFromSha != null && adaptedFromSha.isNotEmpty) ...[
                const SizedBox(height: 4),
                _buildInfoRow('Adapted SHA', adaptedFromSha),
              ],
              if (definitionHash != null && definitionHash.isNotEmpty) ...[
                const SizedBox(height: 4),
                _buildInfoRow('Hash', definitionHash.length > 16 ? '${definitionHash.substring(0, 16)}...' : definitionHash),
              ],
              if (approvedBy != null) ...[
                const SizedBox(height: 4),
                _buildInfoRow('Người phê duyệt', 'User #$approvedBy'),
              ],
            ],
          ),
        ),
        const SizedBox(height: 14),

        // Description
        const Text(
          'Mô tả Kỹ năng:',
          style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: Colors.white70),
        ),
        const SizedBox(height: 4),
        Text(
          description,
          style: const TextStyle(fontSize: 13.5, color: Colors.white, height: 1.45),
        ),
        const SizedBox(height: 14),

        // Tool Permissions
        if (tools.isNotEmpty) ...[
          const Text(
            'Quyền hạn Tools được cấp:',
            style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: Colors.white70),
          ),
          const SizedBox(height: 6),
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: tools.map((t) {
              return Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.05),
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.build_outlined, size: 11, color: AppTheme.primaryLight),
                    const SizedBox(width: 5),
                    Text(
                      t,
                      style: const TextStyle(
                        fontSize: 12.5,
                        color: Colors.white70,
                        fontFamily: 'monospace',
                      ),
                    ),
                  ],
                ),
              );
            }).toList(),
          ),
          const SizedBox(height: 14),
        ],

        // SOP & Instructions
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Text(
              'Quy trình Thao tác Chuẩn (SOP) & Prompt:',
              style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: Colors.white70),
            ),
            IconButton(
              icon: const Icon(Icons.edit_outlined, size: 16, color: AppTheme.primaryLight),
              tooltip: 'Sửa nội dung SOP',
              padding: EdgeInsets.zero,
              constraints: const BoxConstraints(minWidth: 26, minHeight: 26),
              onPressed: () {
                setState(() {
                  _isEditing = true;
                });
              },
            ),
          ],
        ),
        const SizedBox(height: 6),
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: const Color(0xFF080D1A),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: Colors.white.withValues(alpha: 0.06)),
          ),
          child: SelectableText(
            instructions,
            style: const TextStyle(
              fontSize: 13,
              color: Colors.white70,
              fontFamily: 'monospace',
              height: 1.5,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildEditForm() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
          decoration: BoxDecoration(
            color: AppTheme.primary.withValues(alpha: 0.12),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: AppTheme.primary.withValues(alpha: 0.3)),
          ),
          child: const Row(
            children: [
              Icon(Icons.edit_note_rounded, size: 18, color: AppTheme.primaryLight),
              SizedBox(width: 8),
              Text(
                'Đang chỉnh sửa kịch bản & SOP',
                style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.bold, color: AppTheme.primaryLight),
              ),
            ],
          ),
        ),
        const SizedBox(height: 14),

        // Edit Name
        const Text('Tên Kỹ năng:', style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: Colors.white70)),
        const SizedBox(height: 6),
        TextFormField(
          controller: _nameController,
          style: const TextStyle(color: Colors.white, fontSize: 14),
          decoration: _inputDecoration('Nhập tên kỹ năng...'),
        ),
        const SizedBox(height: 14),

        // Edit Description
        const Text('Mô tả:', style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: Colors.white70)),
        const SizedBox(height: 6),
        TextFormField(
          controller: _descController,
          maxLines: 2,
          style: const TextStyle(color: Colors.white, fontSize: 13),
          decoration: _inputDecoration('Nhập mô tả tóm tắt kỹ năng...'),
        ),
        const SizedBox(height: 14),

        // Edit Tool Permissions
        const Text('Quyền hạn Tools (cách nhau bởi dấu phẩy):',
            style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: Colors.white70)),
        const SizedBox(height: 6),
        TextFormField(
          controller: _toolsController,
          style: const TextStyle(color: Colors.white, fontSize: 13, fontFamily: 'monospace'),
          decoration: _inputDecoration('crm.deal.read, email.draft, finance.post_entry...'),
        ),
        const SizedBox(height: 14),

        // Edit SOP & Instructions
        const Text('Quy trình SOP & Prompt Instructions (Markdown):',
            style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: Colors.white70)),
        const SizedBox(height: 6),
        TextFormField(
          controller: _instructionsController,
          maxLines: 12,
          style: const TextStyle(color: Colors.white70, fontSize: 13, fontFamily: 'monospace', height: 1.45),
          decoration: _inputDecoration('Nhập chi tiết các bước quy trình SOP...'),
        ),
      ],
    );
  }

  InputDecoration _inputDecoration(String hint) {
    return InputDecoration(
      hintText: hint,
      hintStyle: const TextStyle(color: Color(0xFF64748B), fontSize: 12.5),
      filled: true,
      fillColor: const Color(0xFF0D1424),
      contentPadding: const EdgeInsets.all(12),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: const BorderSide(color: Color(0xFF1E293B)),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: const BorderSide(color: Color(0xFF1E293B)),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: const BorderSide(color: AppTheme.primaryLight),
      ),
    );
  }

  Widget _buildMetric(String label, String value, Color color) {
    return Column(
      children: [
        Text(
          value,
          style: TextStyle(
            fontSize: 15.5,
            fontWeight: FontWeight.w800,
            color: color,
            fontFamily: 'monospace',
          ),
        ),
        const SizedBox(height: 2),
        Text(
          label,
          style: const TextStyle(
            fontSize: 11.5,
            color: AppTheme.textMutedDark,
          ),
        ),
      ],
    );
  }

  Widget _buildDivider() {
    return Container(
      width: 1,
      height: 24,
      color: Colors.white.withValues(alpha: 0.08),
    );
  }

  Widget _buildInfoRow(String label, String value) {
    return Row(
      children: [
        Text(
          '$label: ',
          style: const TextStyle(fontSize: 12, color: AppTheme.textMutedDark),
        ),
        Expanded(
          child: Text(
            value,
            style: const TextStyle(
              fontSize: 12,
              color: Colors.white70,
              fontFamily: 'monospace',
              fontWeight: FontWeight.w500,
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ),
      ],
    );
  }
}
