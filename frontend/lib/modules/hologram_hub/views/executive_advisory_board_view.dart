import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/localization/locale_controller.dart';
import '../../../core/localization/supported_locale.dart';
import '../controllers/executive_advisory_board_controller.dart';
import '../models/executive_advisory_board.dart';

class ExecutiveAdvisoryBoardView extends StatefulWidget {
  final String projectId;
  final String workspaceId;
  final ExecutiveAdvisoryBoardController controller;

  ExecutiveAdvisoryBoardView({
    super.key,
    required this.projectId,
    required this.workspaceId,
    ExecutiveAdvisoryBoardController? controller,
  }) : controller =
           controller ??
           (Get.isRegistered<ExecutiveAdvisoryBoardController>()
               ? Get.find<ExecutiveAdvisoryBoardController>()
               : Get.put(ExecutiveAdvisoryBoardController()));

  @override
  State<ExecutiveAdvisoryBoardView> createState() =>
      _ExecutiveAdvisoryBoardViewState();
}

class _ExecutiveAdvisoryBoardViewState
    extends State<ExecutiveAdvisoryBoardView> {
  String get projectId => widget.projectId;
  String get workspaceId => widget.workspaceId;
  ExecutiveAdvisoryBoardController get controller => widget.controller;

  @override
  void initState() {
    super.initState();
    controller.loadBoard(projectId);
  }

  bool _isEnglish() {
    if (Get.isRegistered<LocaleController>()) {
      return Get.find<LocaleController>().current.value == SupportedLocale.enUS;
    }
    return Get.locale?.languageCode == 'en';
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      color: const Color(0xFF0F172A), // Slate 900
      child: Obx(() {
        if (controller.isLoading.value) {
          return const Center(
            child: CircularProgressIndicator(color: Colors.indigoAccent),
          );
        }

        return SingleChildScrollView(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildHeader(context),
              const SizedBox(height: 24),
              if (controller.errorMessage.value != null) ...[
                _buildErrorBanner(controller.errorMessage.value!),
                const SizedBox(height: 16),
              ],
              _buildActiveDeliberationSection(context),
              const SizedBox(height: 32),
              _buildRolesSection(context),
            ],
          ),
        );
      }),
    );
  }

  Widget _buildHeader(BuildContext context) {
    final isEn = _isEnglish();
    return Wrap(
      alignment: WrapAlignment.spaceBetween,
      crossAxisAlignment: WrapCrossAlignment.center,
      spacing: 16,
      runSpacing: 16,
      children: [
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              isEn ? 'Executive Advisory Board' : 'Hội đồng Cố vấn Điều hành',
              style: const TextStyle(
                color: Colors.white,
                fontSize: 22,
                fontWeight: FontWeight.bold,
                letterSpacing: -0.5,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              isEn
                  ? 'L1 Strategic Advisors (Read/Propose) per project'
                  : 'Cố vấn chiến lược cấp L1 (Read/Propose) theo từng Project',
              style: TextStyle(
                color: Colors.white.withValues(alpha: 0.6),
                fontSize: 14,
              ),
            ),
          ],
        ),
        Wrap(
          spacing: 12,
          runSpacing: 8,
          children: [
            if (controller.roles.any((role) => role.p0CoreBootstrapAvailable))
              OutlinedButton.icon(
                onPressed: controller.isMutating.value
                    ? null
                    : () => controller.bootstrapP0Core(projectId: projectId),
                icon: const Icon(Icons.rocket_launch_outlined, size: 16),
                label: Text(isEn ? 'Initialize P0 Core' : 'Khởi tạo P0 Core'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: Colors.tealAccent,
                  side: const BorderSide(color: Colors.tealAccent),
                  padding: const EdgeInsets.symmetric(
                    horizontal: 16,
                    vertical: 12,
                  ),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(8),
                  ),
                ),
              ),
            ElevatedButton.icon(
              onPressed: () => _showCreateDeliberationDialog(context),
              icon: const Icon(Icons.add, size: 16, color: Colors.white),
              label: Text(isEn ? 'New Deliberation' : 'Tạo Phiên Nghị sự'),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.indigoAccent,
                padding: const EdgeInsets.symmetric(
                  horizontal: 16,
                  vertical: 12,
                ),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(8),
                ),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildErrorBanner(String message) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.redAccent.withValues(alpha: 0.15),
        border: Border.all(color: Colors.redAccent.withValues(alpha: 0.5)),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        children: [
          const Icon(Icons.error_outline, color: Colors.redAccent, size: 20),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              message,
              style: const TextStyle(color: Colors.redAccent, fontSize: 13),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildActiveDeliberationSection(BuildContext context) {
    final delib = controller.currentDeliberation.value;
    if (delib == null) return const SizedBox.shrink();
    final isEn = _isEnglish();

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B), // Slate 800
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  const Icon(Icons.gavel, color: Colors.amberAccent, size: 20),
                  const SizedBox(width: 8),
                  Text(
                    delib.title,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
              _buildStateChip(delib.state),
            ],
          ),
          if (delib.activeFrame != null) ...[
            const SizedBox(height: 12),
            Text(
              delib.activeFrame!['question']?.toString() ?? '',
              style: TextStyle(
                color: Colors.white.withValues(alpha: 0.9),
                fontSize: 14,
                fontStyle: FontStyle.italic,
              ),
            ),
          ],
          if (delib.analyses.isNotEmpty) ...[
            const SizedBox(height: 16),
            Text(
              isEn ? 'Advisor Feedback:' : 'Ý kiến từ Cố vấn:',
              style: const TextStyle(
                color: Colors.white70,
                fontSize: 13,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 8),
            ...delib.analyses.map((a) => _buildAnalysisRow(a)),
          ],
          // CRITIC_REVIEW chỉ còn ở dữ liệu cũ (chưa có critic runner) — vẫn cho
          // Founder quyết định để deliberation không kẹt.
          if (delib.state == 'AWAITING_FOUNDER' ||
              delib.state == 'CRITIC_REVIEW') ...[
            const SizedBox(height: 16),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                OutlinedButton(
                  onPressed: () => controller.cancelDeliberation(
                    projectId: projectId,
                    deliberationId: delib.id,
                  ),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: Colors.redAccent,
                    side: const BorderSide(color: Colors.redAccent),
                  ),
                  child: Text(isEn ? 'Cancel' : 'Huỷ bỏ'),
                ),
                const SizedBox(width: 12),
                ElevatedButton(
                  onPressed: () => controller.appendDecision(
                    projectId: projectId,
                    deliberationId: delib.id,
                    decisionType: 'APPROVE',
                  ),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.green,
                  ),
                  child: Text(isEn ? 'Approve' : 'Phê duyệt (Approve)'),
                ),
              ],
            ),
          ],
          if (delib.state == 'FAILED_REQUIRES_ATTENTION') ...[
            const SizedBox(height: 16),
            Text(
              isEn
                  ? 'No advisor produced an analysis. Cancel, or frame the question again.'
                  : 'Không cố vấn nào trả được phân tích. Huỷ, hoặc đóng khung lại câu hỏi.',
              style: const TextStyle(color: Colors.orangeAccent, fontSize: 13),
            ),
            const SizedBox(height: 8),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                OutlinedButton(
                  onPressed: () => controller.cancelDeliberation(
                    projectId: projectId,
                    deliberationId: delib.id,
                  ),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: Colors.redAccent,
                    side: const BorderSide(color: Colors.redAccent),
                  ),
                  child: Text(isEn ? 'Cancel' : 'Huỷ bỏ'),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildAnalysisRow(DeliberationAnalysis analysis) {
    final isEn = _isEnglish();
    final conclusion =
        analysis.descriptor['conclusion']?.toString() ??
        (isEn ? 'Analysis completed' : 'Đã hoàn tất phân tích');
    final confidence =
        analysis.descriptor['confidence']?.toString() ?? 'UNKNOWN';

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.white.withValues(alpha: 0.05)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: Colors.indigoAccent.withValues(alpha: 0.2),
              borderRadius: BorderRadius.circular(4),
            ),
            child: Text(
              analysis.roleKey.toUpperCase(),
              style: const TextStyle(
                color: Colors.indigoAccent,
                fontSize: 11,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  conclusion,
                  style: const TextStyle(color: Colors.white, fontSize: 13),
                ),
                const SizedBox(height: 4),
                Text(
                  'Độ tin cậy: $confidence',
                  style: TextStyle(
                    color: Colors.white.withValues(alpha: 0.5),
                    fontSize: 11,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildRolesSection(BuildContext context) {
    final isEn = _isEnglish();
    final recommendedRoles = controller.roles
        .where(
          (role) => role.stageEligibility == ExecutiveStageEligibility.allowed,
        )
        .toList(growable: false);
    final otherRoles = controller.roles
        .where(
          (role) =>
              role.stageEligibility == ExecutiveStageEligibility.notSuggested,
        )
        .toList(growable: false);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          isEn ? 'Executive Advisory Board Members' : 'Thành phần Ban Cố vấn',
          style: const TextStyle(
            color: Colors.white,
            fontSize: 18,
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 16),
        if (controller.roles.isEmpty)
          Text(
            isEn
                ? 'There are no advisor roles to display.'
                : 'Chưa có role cố vấn nào để hiển thị.',
            style: TextStyle(
              color: Colors.white.withValues(alpha: 0.6),
              fontSize: 14,
            ),
          )
        else ...[
          if (recommendedRoles.isNotEmpty) ...[
            Text(
              isEn
                  ? 'Recommended for the current stage'
                  : 'Đề xuất cho giai đoạn hiện tại',
              style: const TextStyle(
                color: Colors.indigoAccent,
                fontSize: 14,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 12),
            _buildRoleGrid(context, recommendedRoles),
          ],
          if (otherRoles.isNotEmpty) ...[
            if (recommendedRoles.isNotEmpty) const SizedBox(height: 24),
            Text(
              isEn ? 'Other roles' : 'Các role khác',
              style: TextStyle(
                color: Colors.white.withValues(alpha: 0.7),
                fontSize: 14,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 12),
            _buildRoleGrid(context, otherRoles),
          ],
        ],
      ],
    );
  }

  Widget _buildRoleGrid(
    BuildContext context,
    List<ExecutiveAdvisorRole> roles,
  ) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final crossAxisCount = constraints.maxWidth > 900
            ? 3
            : (constraints.maxWidth > 600 ? 2 : 1);
        return GridView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: crossAxisCount,
            crossAxisSpacing: 16,
            mainAxisSpacing: 16,
            childAspectRatio: 1.4,
          ),
          itemCount: roles.length,
          itemBuilder: (context, index) =>
              _buildRoleCard(context, roles[index]),
        );
      },
    );
  }

  Widget _buildRoleCard(BuildContext context, ExecutiveAdvisorRole role) {
    final isEn = _isEnglish();
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: role.effectiveState == ExecutiveEffectiveState.effective
              ? Colors.indigoAccent.withValues(alpha: 0.4)
              : Colors.white.withValues(alpha: 0.06),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Text(
                  role.label,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 15,
                    fontWeight: FontWeight.bold,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              _buildRoleBadge(role.effectiveState),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            role.requiredProfileKey,
            style: TextStyle(
              color: Colors.white.withValues(alpha: 0.5),
              fontSize: 12,
            ),
          ),
          const SizedBox(height: 8),
          Expanded(
            child: Text(
              role.advisoryRemit,
              style: TextStyle(
                color: Colors.white.withValues(alpha: 0.7),
                fontSize: 12,
              ),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
          ),
          if (role.officeState == ExecutiveOfficeState.active &&
              role.projectDeploymentState !=
                  ExecutiveProjectDeploymentState.active) ...[
            const SizedBox(height: 8),
            Text(
              isEn
                  ? 'Role is enabled at the Workspace — deploy its Agent into this Project'
                  : 'Role đã bật ở Workspace — cần deploy Agent vào Project',
              style: const TextStyle(color: Colors.amberAccent, fontSize: 11),
            ),
          ],
          if (role.disabledReason != null) ...[
            Text(
              role.disabledReason!,
              style: const TextStyle(color: Colors.amberAccent, fontSize: 11),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: 8),
          ],
          _buildActionRow(role),
        ],
      ),
    );
  }

  Widget _buildRoleBadge(ExecutiveEffectiveState state) {
    final isEn = _isEnglish();
    String message;
    Color color;
    IconData icon;
    switch (state) {
      case ExecutiveEffectiveState.effective:
        message = isEn ? 'Ready for advisory' : 'Sẵn sàng tư vấn';
        color = Colors.green;
        icon = Icons.check_circle_outline;
        break;
      case ExecutiveEffectiveState.deploymentInactive:
        message = isEn
            ? 'Deploy Agent to this Project'
            : 'Cần deploy Agent vào Project';
        color = Colors.amber;
        icon = Icons.cloud_upload_outlined;
        break;
      case ExecutiveEffectiveState.stageForbidden:
        message = isEn
            ? 'Not recommended at this stage'
            : 'Chưa phù hợp giai đoạn';
        color = Colors.orange;
        icon = Icons.schedule_outlined;
        break;
      case ExecutiveEffectiveState.officeDisabled:
        message = isEn ? 'Office is not enabled' : 'Office chưa bật';
        color = Colors.grey;
        icon = Icons.power_settings_new;
        break;
    }

    return Tooltip(
      message: message,
      child: Semantics(
        label: message,
        child: Icon(icon, color: color, size: 20),
      ),
    );
  }

  Widget _buildActionRow(ExecutiveAdvisorRole role) {
    final isEn = _isEnglish();
    // Chỉ server-confirmed AVAILABLE_NOT_ACTIVATED hoặc DISABLED mới cho phép
    // bật Office. UNAVAILABLE có thể là catalog/profile chưa sẵn sàng nên phải
    // giữ fail closed, không suy diễn từ việc thiếu activation row.
    if (role.officeState == ExecutiveOfficeState.availableNotActivated ||
        role.officeState == ExecutiveOfficeState.disabled) {
      return SizedBox(
        width: double.infinity,
        child: ElevatedButton(
          onPressed: () => controller.activateRole(
            workspaceId: workspaceId,
            projectId: projectId,
            roleKey: role.roleKey,
            expectedVersion: role.workspaceOfficeVersion,
          ),
          style: ElevatedButton.styleFrom(
            backgroundColor: Colors.indigoAccent,
            padding: const EdgeInsets.symmetric(vertical: 8),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(6),
            ),
          ),
          child: Text(
            isEn ? 'Enable Office' : 'Bật Office',
            style: const TextStyle(fontSize: 12),
          ),
        ),
      );
    } else if (role.officeState == ExecutiveOfficeState.unavailable &&
        role.disabledReason == 'UNDERLYING_PROFILE_UNAVAILABLE') {
      return SizedBox(
        width: double.infinity,
        child: ElevatedButton.icon(
          onPressed: controller.isMutating.value
              ? null
              : () => controller.activateUnderlyingProfile(
                  projectId: projectId,
                  profileKey: role.requiredProfileKey,
                ),
          icon: const Icon(Icons.play_circle_outline, size: 16),
          label: Text(
            isEn ? 'Activate underlying Agent' : 'Kích hoạt agent nền',
            style: const TextStyle(fontSize: 12),
          ),
          style: ElevatedButton.styleFrom(
            backgroundColor: Colors.teal,
            padding: const EdgeInsets.symmetric(vertical: 8),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(6),
            ),
          ),
        ),
      );
    } else if (role.officeState == ExecutiveOfficeState.active) {
      if (role.workspaceAgentId == null) {
        return SizedBox(
          width: double.infinity,
          child: ElevatedButton.icon(
            onPressed: controller.isMutating.value
                ? null
                : () => controller.activateUnderlyingProfile(
                      projectId: projectId,
                      profileKey: role.requiredProfileKey,
                    ),
            icon: const Icon(Icons.memory_outlined, size: 16),
            label: Text(
              isEn ? 'Provision Workspace Agent' : 'Khởi tạo Workspace Agent',
              style: const TextStyle(fontSize: 12),
            ),
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.teal,
              padding: const EdgeInsets.symmetric(vertical: 8),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
            ),
          ),
        );
      }
      if (role.projectDeploymentState !=
              ExecutiveProjectDeploymentState.active &&
          role.workspaceAgentId != null) {
        return SizedBox(
          width: double.infinity,
          child: ElevatedButton.icon(
            onPressed: controller.isMutating.value
                ? null
                : () => controller.deployRoleAgent(
                    projectId: projectId,
                    workspaceAgentId: role.workspaceAgentId!,
                  ),
            icon: const Icon(Icons.cloud_upload_outlined, size: 16),
            label: Text(
              isEn ? 'Deploy Agent' : 'Deploy Agent',
              style: const TextStyle(fontSize: 12),
            ),
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.indigoAccent,
              padding: const EdgeInsets.symmetric(vertical: 8),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(6),
              ),
            ),
          ),
        );
      }
      return SizedBox(
        width: double.infinity,
        child: OutlinedButton(
          onPressed: () => controller.disableRole(
            workspaceId: workspaceId,
            projectId: projectId,
            roleKey: role.roleKey,
            expectedVersion: role.workspaceOfficeVersion,
          ),
          style: OutlinedButton.styleFrom(
            foregroundColor: Colors.white70,
            side: BorderSide(color: Colors.white.withValues(alpha: 0.2)),
            padding: const EdgeInsets.symmetric(vertical: 8),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(6),
            ),
          ),
          child: Text(
            isEn ? 'Disable Office' : 'Tắt Office',
            style: const TextStyle(fontSize: 12),
          ),
        ),
      );
    }

    return const SizedBox(height: 32);
  }

  Widget _buildStateChip(String state) {
    Color color = Colors.blueAccent;
    if (state == 'AWAITING_FOUNDER') color = Colors.amberAccent;
    if (state == 'DECIDED') color = Colors.greenAccent;
    if (state == 'CANCELLED') color = Colors.redAccent;
    if (state == 'FAILED_REQUIRES_ATTENTION') color = Colors.orangeAccent;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withValues(alpha: 0.4)),
      ),
      child: Text(
        state,
        style: TextStyle(
          color: color,
          fontSize: 11,
          fontWeight: FontWeight.bold,
        ),
      ),
    );
  }

  void _showCreateDeliberationDialog(BuildContext context) {
    final isEn = _isEnglish();
    final titleController = TextEditingController();
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF1E293B),
        title: Text(
          isEn ? 'Create New Deliberation' : 'Tạo Phiên Nghị sự Mới',
          style: const TextStyle(color: Colors.white),
        ),
        content: TextField(
          controller: titleController,
          style: const TextStyle(color: Colors.white),
          decoration: InputDecoration(
            labelText: isEn
                ? 'Topic / Consultation Subject'
                : 'Chủ đề / Vấn đề cần tham vấn',
            labelStyle: const TextStyle(color: Colors.white60),
            hintText: isEn
                ? 'e.g. Q3 Capital Allocation Plan'
                : 'VD: Kế hoạch phân bổ vốn Q3',
            hintStyle: const TextStyle(color: Colors.white30),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: Text(
              isEn ? 'Cancel' : 'Huỷ',
              style: const TextStyle(color: Colors.white54),
            ),
          ),
          ElevatedButton(
            onPressed: () {
              final title = titleController.text.trim();
              if (title.isNotEmpty) {
                Navigator.pop(ctx);
                controller.createDraft(projectId: projectId, title: title);
              }
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.indigoAccent,
            ),
            child: Text(isEn ? 'Create' : 'Tạo'),
          ),
        ],
      ),
    );
  }
}
