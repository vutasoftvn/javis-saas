import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../controllers/permissions_controller.dart';
import '../../models/permission_models.dart';

class PermissionsPanel extends StatelessWidget {
  const PermissionsPanel({super.key});

  @override
  Widget build(BuildContext context) {
    final controller = Get.isRegistered<PermissionsController>()
        ? Get.find<PermissionsController>()
        : Get.put(PermissionsController());

    final theme = Theme.of(context);

    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(color: theme.colorScheme.outlineVariant),
      ),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Obx(() {
          if (controller.isLoading.value) {
            return const Center(
              child: Padding(
                padding: EdgeInsets.all(32),
                child: CircularProgressIndicator(),
              ),
            );
          }

          if (!controller.isFounder.value) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(Icons.lock_outline, color: theme.colorScheme.error, size: 24),
                    const SizedBox(width: 8),
                    const Text(
                      'Founder Authority Only',
                      style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text(
                  'Chỉ Founder mới có quyền quản lý phân quyền và lực lượng lao động.',
                  style: TextStyle(color: theme.colorScheme.onSurfaceVariant),
                ),
                const SizedBox(height: 12),
                ElevatedButton(
                  onPressed: () => controller.loadPermissions(),
                  child: const Text('Thử lại'),
                ),
              ],
            );
          }

          final data = controller.permissionsData.value;
          if (data == null) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Quản lý phân quyền và Governance',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 8),
                if (controller.conflictMessage.isNotEmpty)
                  Container(
                    key: const ValueKey('permission-conflict'),
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: theme.colorScheme.errorContainer,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(
                      controller.conflictMessage.value,
                      style: TextStyle(color: theme.colorScheme.onErrorContainer),
                    ),
                  ),
                const SizedBox(height: 12),
                ElevatedButton(
                  onPressed: () => controller.loadPermissions(),
                  child: const Text('Tải lại'),
                ),
              ],
            );
          }

          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            const Icon(Icons.shield_outlined, size: 22),
                            const SizedBox(width: 8),
                            Flexible(
                              child: Text(
                                'Phân quyền & Governance (Policy v${data.version})',
                                style: const TextStyle(
                                  fontSize: 18,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 4),
                        Text(
                          'Founder quản trị quyền thống nhất cho người và AI agent. DENY luôn chiếm ưu thế.',
                          style: TextStyle(
                            fontSize: 13,
                            color: theme.colorScheme.onSurfaceVariant,
                          ),
                        ),
                      ],
                    ),
                  ),
                  Row(
                    children: [
                      ElevatedButton.icon(
                        key: const ValueKey('permission-save'),
                        onPressed: controller.isSaving.value
                            ? null
                            : () => controller.savePermissions(),
                        icon: controller.isSaving.value
                            ? const SizedBox(
                                width: 16,
                                height: 16,
                                child: CircularProgressIndicator(strokeWidth: 2),
                              )
                            : const Icon(Icons.save_outlined, size: 18),
                        label: const Text('Lưu quyền'),
                      ),
                    ],
                  ),
                ],
              ),
              if (controller.conflictMessage.isNotEmpty) ...[
                const SizedBox(height: 12),
                Container(
                  key: const ValueKey('permission-conflict'),
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: theme.colorScheme.errorContainer,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: theme.colorScheme.error),
                  ),
                  child: Row(
                    children: [
                      Icon(Icons.warning_amber_rounded, color: theme.colorScheme.error),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          controller.conflictMessage.value,
                          style: TextStyle(
                            color: theme.colorScheme.onErrorContainer,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ),
                      TextButton(
                        onPressed: () => controller.loadPermissions(),
                        child: const Text('Tải lại'),
                      ),
                    ],
                  ),
                ),
              ],
              if (controller.successMessage.isNotEmpty) ...[
                const SizedBox(height: 12),
                Container(
                  key: const ValueKey('permission-success'),
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: theme.colorScheme.primaryContainer,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Row(
                    children: [
                      Icon(Icons.check_circle_outline, color: theme.colorScheme.primary),
                      const SizedBox(width: 8),
                      Text(
                        controller.successMessage.value,
                        style: TextStyle(
                          color: theme.colorScheme.onPrimaryContainer,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
              const SizedBox(height: 16),
              // Tabs navigation
              _buildTabSelector(context, controller),
              const SizedBox(height: 16),
              // Tab body
              _buildActiveTabContent(context, controller, data),
            ],
          );
        }),
      ),
    );
  }

  Widget _buildTabSelector(BuildContext context, PermissionsController controller) {
    final tabs = ['Policies', 'Members', 'AI workforce', 'Live control', 'Audit'];
    return Obx(() {
      return Wrap(
        spacing: 8,
        children: List.generate(tabs.length, (index) {
          final isSelected = controller.activeTab.value == index;
          return ChoiceChip(
            label: Text(tabs[index]),
            selected: isSelected,
            onSelected: (selected) {
              if (selected) controller.activeTab.value = index;
            },
          );
        }),
      );
    });
  }

  Widget _buildActiveTabContent(
    BuildContext context,
    PermissionsController controller,
    PermissionsDataModel data,
  ) {
    switch (controller.activeTab.value) {
      case 1:
        return _buildMembersTab(context, controller);
      case 2:
        return _buildAiWorkforceTab(context, controller);
      case 3:
        return _buildLiveControlTab(context, controller);
      case 4:
        return _buildAuditTab(context, controller);
      case 0:
      default:
        return _buildPoliciesTab(context, controller, data);
    }
  }

  Widget _buildPoliciesTab(
    BuildContext context,
    PermissionsController controller,
    PermissionsDataModel data,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _buildMatrixTable(context, controller, data),
        const SizedBox(height: 24),
        _buildSimulationCard(context, controller, data),
      ],
    );
  }

  Widget _buildMembersTab(BuildContext context, PermissionsController controller) {
    final overview = controller.overviewData.value;
    final members = (overview?.members ?? []).where((m) => m.memberType == 'HUMAN').toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Human Workforce Members',
          style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 8),
        if (members.isEmpty)
          const Text('Chưa có thành viên nào.')
        else
          DataTable(
            columns: const [
              DataColumn(label: Text('ID')),
              DataColumn(label: Text('Title')),
              DataColumn(label: Text('User ID')),
              DataColumn(label: Text('Status')),
            ],
            rows: members.map((m) {
              return DataRow(cells: [
                DataCell(Text(m.id)),
                DataCell(Text(m.roleTitle ?? '-')),
                DataCell(Text(m.humanUserId ?? '-')),
                DataCell(Text(m.status)),
              ]);
            }).toList(),
          ),
      ],
    );
  }

  Widget _buildAiWorkforceTab(BuildContext context, PermissionsController controller) {
    final overview = controller.overviewData.value;
    final agents = (overview?.members ?? []).where((m) => m.memberType == 'AI_AGENT').toList();
    final grants = overview?.grants ?? [];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'AI Workforce & Capability Grants',
          style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 4),
        const Text(
          'Chỉ founder mới có quyền cấp grant cho AI. AI Agent không thể giữ role founder.',
          style: TextStyle(fontSize: 13, color: Colors.grey),
        ),
        const SizedBox(height: 12),
        if (agents.isEmpty)
          const Text('Không có AI Agent nào trong workspace.')
        else
          ...agents.map((agent) {
            final agentGrants = grants.where((g) => g.agentWorkforceMemberId == agent.id).toList();
            return Card(
              margin: const EdgeInsets.only(bottom: 12),
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Icon(Icons.smart_toy_outlined, size: 20),
                        const SizedBox(width: 8),
                        Text(
                          '${agent.roleTitle ?? "AI Agent"} (${agent.agentSpecId ?? agent.id})',
                          style: const TextStyle(fontWeight: FontWeight.bold),
                        ),
                        const Spacer(),
                        Chip(label: Text(agent.status), visualDensity: VisualDensity.compact),
                      ],
                    ),
                    const Divider(),
                    const Text('Active Grants:', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
                    if (agentGrants.isEmpty)
                      const Text('Chưa có grant nào được cấp.', style: TextStyle(fontSize: 12, color: Colors.grey))
                    else
                      ...agentGrants.map((g) {
                        return ListTile(
                          dense: true,
                          title: Text(g.capabilityId),
                          subtitle: Text('Status: ${g.status} · From: ${g.validFrom}'),
                          trailing: g.status == 'ACTIVE'
                              ? TextButton(
                                  onPressed: () => controller.revokeGrant(
                                    grantId: g.id,
                                    reason: 'Founder revoked from UI',
                                  ),
                                  child: const Text('Thu hồi', style: TextStyle(color: Colors.red)),
                                )
                              : null,
                        );
                      }),
                  ],
                ),
              ),
            );
          }),
      ],
    );
  }

  Widget _buildLiveControlTab(BuildContext context, PermissionsController controller) {
    final overview = controller.overviewData.value;
    final epoch = overview?.authorizationEpoch ?? 1;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('Live Authorization Control Plane', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
        const SizedBox(height: 8),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                const Icon(Icons.flash_on_outlined, size: 32, color: Colors.amber),
                const SizedBox(width: 16),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Authorization Epoch: $epoch', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                    const Text('Mọi side effect rủi ro cao yêu cầu vé live ticket dùng 1 lần (TTL <= 60s).'),
                  ],
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildAuditTab(BuildContext context, PermissionsController controller) {
    final overview = controller.overviewData.value;
    final events = overview?.events ?? [];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('Audit Summary & Authorization Events', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
        const SizedBox(height: 8),
        if (events.isEmpty)
          const Text('Chưa có sự kiện authorization nào.')
        else
          ListView.builder(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: events.length,
            itemBuilder: (context, index) {
              final ev = events[index];
              return ListTile(
                dense: true,
                leading: const Icon(Icons.history_outlined),
                title: Text(ev['eventType']?.toString() ?? 'event'),
                subtitle: Text('ID: ${ev['id']} · Epoch: ${ev['authorizationEpoch'] ?? 1}'),
              );
            },
          ),
      ],
    );
  }

  Widget _buildMatrixTable(
    BuildContext context,
    PermissionsController controller,
    PermissionsDataModel data,
  ) {
    final theme = Theme.of(context);
    final roles = data.roles;
    final catalog = data.catalog;

    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Table(
        defaultColumnWidth: const IntrinsicColumnWidth(),
        border: TableBorder.all(color: theme.colorScheme.outlineVariant),
        children: [
          TableRow(
            decoration: BoxDecoration(color: theme.colorScheme.surfaceContainerHighest),
            children: [
              const Padding(
                padding: EdgeInsets.all(12),
                child: Text('Quyền hạn (Catalog)', style: TextStyle(fontWeight: FontWeight.bold)),
              ),
              ...roles.map(
                (role) => Padding(
                  padding: const EdgeInsets.all(12),
                  child: Text(
                    '${role.name}${role.isSystem ? " (Hệ thống)" : ""}',
                    style: const TextStyle(fontWeight: FontWeight.bold),
                  ),
                ),
              ),
            ],
          ),
          ...catalog.map((perm) {
            return TableRow(
              children: [
                Padding(
                  padding: const EdgeInsets.all(12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(perm.permissionKey, style: const TextStyle(fontWeight: FontWeight.w600)),
                      if (perm.description != null)
                        Text(
                          perm.description!,
                          style: TextStyle(fontSize: 12, color: theme.colorScheme.onSurfaceVariant),
                        ),
                    ],
                  ),
                ),
                ...roles.map((role) {
                  final currentEffect = controller.getPermissionEffect(role.id, perm.permissionKey);
                  return Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    child: DropdownButton<String>(
                      value: currentEffect,
                      underline: const SizedBox(),
                      items: const [
                        DropdownMenuItem(value: 'ALLOW', child: Text('ALLOW')),
                        DropdownMenuItem(value: 'REQUIRE_APPROVAL', child: Text('APPROVAL')),
                        DropdownMenuItem(value: 'DENY', child: Text('DENY')),
                      ],
                      onChanged: (newEffect) {
                        if (newEffect != null) {
                          controller.updateDraftPermission(role.id, perm.permissionKey, newEffect);
                        }
                      },
                    ),
                  );
                }),
              ],
            );
          }),
        ],
      ),
    );
  }

  Widget _buildSimulationCard(
    BuildContext context,
    PermissionsController controller,
    PermissionsDataModel data,
  ) {
    final theme = Theme.of(context);
    return Card(
      key: const ValueKey('permission-simulation'),
      color: theme.colorScheme.surfaceContainerLow,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Mô phỏng Policy & Governance',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: DropdownButtonFormField<String>(
                    initialValue: controller.selectedSimulationAction.value.isNotEmpty
                        ? controller.selectedSimulationAction.value
                        : null,

                    decoration: const InputDecoration(
                      labelText: 'Chọn quyền muốn mô phỏng',
                      border: OutlineInputBorder(),
                    ),
                    items: data.catalog.map((c) {
                      return DropdownMenuItem(value: c.permissionKey, child: Text(c.permissionKey));
                    }).toList(),
                    onChanged: (val) {
                      if (val != null) controller.selectedSimulationAction.value = val;
                    },
                  ),
                ),
                const SizedBox(width: 12),
                ElevatedButton(
                  onPressed: () => controller.simulateAction(
                    controller.selectedSimulationAction.value,
                    memberId: data.assignments.firstOrNull?.workforceMemberId,
                  ),
                  child: const Text('Mô phỏng'),
                ),
              ],
            ),
            if (controller.simulationResult.value != null) ...[
              const SizedBox(height: 12),
              const Text('Kết quả phân tích quyết định:', style: TextStyle(fontWeight: FontWeight.bold)),
              ...controller.simulationResult.value!.impacts.map((imp) {
                return ListTile(
                  dense: true,
                  title: Text('Member: ${imp.memberId} -> ${imp.effect}'),
                  subtitle: Text(imp.reason),
                );
              }),
            ],
          ],
        ),
      ),
    );
  }
}
