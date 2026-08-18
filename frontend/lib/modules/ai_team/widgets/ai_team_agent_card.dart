import 'package:flutter/material.dart';
import '../../../../core/theme/app_theme.dart';
import '../controllers/ai_team_controller.dart';
import 'ai_team_agent_detail_modal.dart';
import 'ai_team_helpers.dart';

class AiTeamAgentCard extends StatelessWidget {
  final Map<String, dynamic> agent;
  final AiTeamController controller;

  const AiTeamAgentCard({
    super.key,
    required this.agent,
    required this.controller,
  });

  @override
  Widget build(BuildContext context) {
    final name = agent['name'] ?? agent['key'] ?? 'AI Agent';
    final role = agent['role_title'] ?? agent['role'] ?? 'Specialist';
    final dept = agent['department'] ?? 'general';
    final desc = agent['description'] ?? '';
    final isSystem = agent['is_system'] != false;
    final isEnabled = agent['enabled'] ?? true;
    final isOrchestrator = agent['agent_type'] == 'orchestrator';
    final level = isOrchestrator
        ? 'TỔNG ĐIỀU PHỐI'
        : ((agent['risk_level'] != null && agent['risk_level'] >= 2)
            ? 'CHUYÊN GIA'
            : 'CHUYÊN VIÊN');
    final provider = agent['runtime_provider'] ?? 'gemini';
    final model =
        agent['default_model_profile'] ?? agent['model_name'] ?? 'reasoning';
    final modelDisplay = AiTeamHelpers.translateModelProfile(model.toString());
    final health =
        isEnabled ? (agent['health_status']?.toString() ?? 'HEALTHY') : 'OFFLINE';
    final promptKey = AiTeamHelpers.getAgentPromptKey(agent);
    final tools = AiTeamHelpers.getAgentToolsList(agent);

    // Simplified color palette – muted/gray tones
    const iconBg = Color(0xFF2A2D3A);
    const iconColor = Color(0xFF8B90A0);
    const badgeBg = Color(0xFF242630);
    const badgeBorder = Color(0xFF373A4A);
    const badgeText = Color(0xFF8B90A0);
    const tagBg = Color(0xFF1E2029);
    const tagBorder = Color(0xFF32364A);
    const tagText = Color(0xFF8B90A0);

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: () => AiTeamAgentDetailModal.show(context, agent, controller),
        borderRadius: BorderRadius.circular(14),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
          decoration: BoxDecoration(
            color: isEnabled
                ? AppTheme.surfaceDark
                : AppTheme.surfaceDark.withValues(alpha: 0.5),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(
              color: isEnabled
                  ? const Color(0xFF2E3144)
                  : const Color(0xFF1E202A),
            ),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.12),
                blurRadius: 5,
                offset: const Offset(0, 2),
              ),
            ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              // 1. Header: Avatar + Tên + Chức danh + Badge
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.center,
                    children: [
                      Expanded(
                        child: Row(
                          children: [
                            Stack(
                              children: [
                                Container(
                                  width: 36,
                                  height: 36,
                                  decoration: BoxDecoration(
                                    color: iconBg,
                                    borderRadius: BorderRadius.circular(9),
                                    border: Border.all(
                                        color: const Color(0xFF363A50)),
                                  ),
                                  child: Center(
                                    child: Icon(
                                      AiTeamHelpers.getDepartmentIcon(dept),
                                      color: iconColor,
                                      size: 18,
                                    ),
                                  ),
                                ),
                                // Health dot
                                Positioned(
                                  right: 0,
                                  bottom: 0,
                                  child: Container(
                                    width: 9,
                                    height: 9,
                                    decoration: BoxDecoration(
                                      color: health == 'HEALTHY'
                                          ? const Color(0xFF34D399)
                                          : (health == 'OFFLINE'
                                              ? const Color(0xFF4B5060)
                                              : const Color(0xFFFBBF24)),
                                      shape: BoxShape.circle,
                                      border: Border.all(
                                          color: AppTheme.surfaceDark,
                                          width: 1.5),
                                    ),
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    name,
                                    style: TextStyle(
                                      fontWeight: FontWeight.w600,
                                      fontSize: 14,
                                      color: isEnabled
                                          ? AppTheme.textDark
                                          : AppTheme.textMutedDark,
                                    ),
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                  const SizedBox(height: 1.5),
                                  Text(
                                    role,
                                    style: const TextStyle(
                                        color: Color(0xFF5E6278), fontSize: 11.5),
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(width: 6),
                      // System / Custom Badge – muted style
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 6, vertical: 2.5),
                        decoration: BoxDecoration(
                          color: badgeBg,
                          borderRadius: BorderRadius.circular(5),
                          border: Border.all(color: badgeBorder),
                        ),
                        child: Text(
                          isSystem ? 'Core · $level' : 'Tùy biến',
                          style: const TextStyle(
                            fontSize: 9.5,
                            fontWeight: FontWeight.w600,
                            color: badgeText,
                          ),
                        ),
                      ),
                      const SizedBox(width: 4),
                      // Quick action menu
                      PopupMenuButton<String>(
                        icon: const Icon(Icons.more_vert_rounded,
                            size: 18, color: Color(0xFF545870)),
                        color: AppTheme.surfaceDarkElevated,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(10),
                          side: const BorderSide(color: AppTheme.borderDark),
                        ),
                        onSelected: (val) {
                          if (val == 'edit') {
                            AiTeamAgentDetailModal.show(
                                context, agent, controller);
                          } else if (val == 'clone') {
                            AiTeamAgentDetailModal.showCloneAgentDialog(
                                context, agent, controller);
                          } else if (val == 'toggle') {
                            controller.toggleAgentStatus(agent);
                          } else if (val == 'delete') {
                            AiTeamAgentDetailModal.showDeleteAgentConfirmDialog(
                                context, agent, controller);
                          }
                        },
                        itemBuilder: (ctx) => [
                          const PopupMenuItem(
                            value: 'edit',
                            child: Row(children: [
                              Icon(Icons.tune_rounded,
                                  size: 16, color: Color(0xFF7B7E9A)),
                              SizedBox(width: 8),
                              Text('Xem & Sửa System Prompt',
                                  style: TextStyle(fontSize: 12.5)),
                            ]),
                          ),
                          const PopupMenuItem(
                            value: 'clone',
                            child: Row(children: [
                              Icon(Icons.copy_rounded,
                                  size: 16, color: Color(0xFF7B7E9A)),
                              SizedBox(width: 8),
                              Text('Nhân bản (Clone)',
                                  style: TextStyle(fontSize: 12.5)),
                            ]),
                          ),
                          PopupMenuItem(
                            value: 'toggle',
                            child: Row(children: [
                              Icon(
                                isEnabled
                                    ? Icons.pause_circle_outline
                                    : Icons.play_circle_outline,
                                size: 16,
                                color: isEnabled
                                    ? AppTheme.warning
                                    : AppTheme.success,
                              ),
                              const SizedBox(width: 8),
                              Text(
                                  isEnabled ? 'Tạm dừng Agent' : 'Kích hoạt Agent',
                                  style: const TextStyle(fontSize: 12.5)),
                            ]),
                          ),
                          if (!isSystem)
                            const PopupMenuItem(
                              value: 'delete',
                              child: Row(children: [
                                Icon(Icons.delete_outline,
                                    size: 16, color: AppTheme.error),
                                SizedBox(width: 8),
                                Text('Xóa Agent',
                                    style: TextStyle(
                                        fontSize: 12.5, color: AppTheme.error)),
                              ]),
                            ),
                        ],
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),

                  // 2. Mô tả nhiệm vụ – 1 dòng gọn cho tổng quan
                  if (desc.isNotEmpty)
                    Text(
                      desc,
                      style: const TextStyle(
                        fontSize: 12,
                        color: AppTheme.textMutedDark,
                        height: 1.4,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  const SizedBox(height: 10),
                ],
              ),

              // 3. Danh sách Tools / Kỹ năng – 1 dòng cố định
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Single-row badge strip: hiển thị tối đa 3 tool, còn lại gộp vào +N
                  Row(
                    children: [
                      ...tools.take(3).map((tool) => Padding(
                        padding: const EdgeInsets.only(right: 4),
                        child: Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 6, vertical: 2),
                          decoration: BoxDecoration(
                            color: tagBg,
                            borderRadius: BorderRadius.circular(5),
                            border: Border.all(color: tagBorder),
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              const Icon(Icons.bolt_rounded,
                                  size: 10, color: Color(0xFF4A4E65)),
                              const SizedBox(width: 3),
                              Text(
                                tool,
                                style: const TextStyle(
                                    fontSize: 10,
                                    color: tagText,
                                    fontWeight: FontWeight.w500),
                              ),
                            ],
                          ),
                        ),
                      )),
                      if (tools.length > 3)
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 6, vertical: 2),
                          decoration: BoxDecoration(
                            color: tagBg,
                            borderRadius: BorderRadius.circular(5),
                            border: Border.all(color: tagBorder),
                          ),
                          child: Text(
                            '+${tools.length - 3}',
                            style: const TextStyle(
                                fontSize: 10,
                                color: Color(0xFF6366A0),
                                fontWeight: FontWeight.bold),
                          ),
                        ),
                    ],
                  ),
                  const SizedBox(height: 10),

                  // 4. Footer: Engine (gọn cho tổng quan)
                  Row(
                    children: [
                      const Icon(Icons.memory_rounded,
                          size: 11, color: Color(0xFF4E5168)),
                      const SizedBox(width: 4),
                      Text(
                        '$provider · $modelDisplay',
                        style: const TextStyle(
                            fontSize: 10.5, color: Color(0xFF5E6278)),
                      ),
                      const Spacer(),
                      // Health status text
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: health == 'HEALTHY'
                              ? const Color(0xFF0D2A1E)
                              : (health == 'OFFLINE'
                                  ? const Color(0xFF1A1C27)
                                  : const Color(0xFF2A2010)),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Text(
                          health == 'HEALTHY'
                              ? 'Online'
                              : (health == 'OFFLINE' ? 'Offline' : 'Warning'),
                          style: TextStyle(
                            fontSize: 10,
                            fontWeight: FontWeight.w600,
                            color: health == 'HEALTHY'
                                ? const Color(0xFF34D399)
                                : (health == 'OFFLINE'
                                    ? const Color(0xFF5E6278)
                                    : const Color(0xFFFBBF24)),
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
