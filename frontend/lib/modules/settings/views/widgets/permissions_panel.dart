import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../controllers/permissions_controller.dart';

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
                    ],
                  ),
                ),
              ],
              if (controller.successMessage.isNotEmpty) ...[
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.green.shade50,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: Colors.green.shade300),
                  ),
                  child: Text(
                    controller.successMessage.value,
                    style: TextStyle(color: Colors.green.shade900),
                  ),
                ),
              ],
              const SizedBox(height: 20),
              // Ma trận phân quyền
              const Text(
                'Ma trận vai trò × Hành động',
                style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 10),
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: DataTable(
                  columnSpacing: 24,
                  columns: [
                    const DataColumn(label: Text('Hành động (Permission)')),
                    ...data.roles.map((r) => DataColumn(
                          label: Text(r.name, style: const TextStyle(fontWeight: FontWeight.bold)),
                        )),
                    const DataColumn(label: Text('Hiệu lực (Caller)')),
                  ],
                  rows: data.catalog.map((perm) {
                    final effective = data.effectivePermissions[perm.permissionKey] ?? 'DENY';
                    return DataRow(
                      cells: [
                        DataCell(
                          Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Text(
                                perm.permissionKey,
                                style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13),
                              ),
                              if (perm.description != null)
                                Text(
                                  perm.description!,
                                  style: TextStyle(
                                    fontSize: 11,
                                    color: theme.colorScheme.onSurfaceVariant,
                                  ),
                                ),
                            ],
                          ),
                        ),
                        ...data.roles.map((r) {
                          final currentEffect = controller.getPermissionEffect(
                            r.id,
                            perm.permissionKey,
                          );
                          return DataCell(
                            DropdownButton<String>(
                              key: ValueKey('dropdown-${r.id}-${perm.permissionKey}'),
                              value: currentEffect,
                              underline: const SizedBox(),
                              items: const [
                                DropdownMenuItem(value: 'ALLOW', child: Text('ALLOW', style: TextStyle(color: Colors.green, fontSize: 12))),
                                DropdownMenuItem(value: 'REQUIRE_APPROVAL', child: Text('APPROVAL', style: TextStyle(color: Colors.orange, fontSize: 12))),
                                DropdownMenuItem(value: 'DENY', child: Text('DENY', style: TextStyle(color: Colors.red, fontSize: 12))),
                              ],
                              onChanged: (val) {
                                if (val != null) {
                                  controller.updateDraftPermission(r.id, perm.permissionKey, val);
                                }
                              },
                            ),
                          );
                        }),
                        DataCell(
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                            decoration: BoxDecoration(
                              color: effective == 'ALLOW'
                                  ? Colors.green.shade100
                                  : effective == 'REQUIRE_APPROVAL'
                                      ? Colors.orange.shade100
                                      : Colors.red.shade100,
                              borderRadius: BorderRadius.circular(4),
                            ),
                            child: Text(
                              effective,
                              style: TextStyle(
                                fontSize: 11,
                                fontWeight: FontWeight.bold,
                                color: effective == 'ALLOW'
                                    ? Colors.green.shade900
                                    : effective == 'REQUIRE_APPROVAL'
                                        ? Colors.orange.shade900
                                        : Colors.red.shade900,
                              ),
                            ),
                          ),
                        ),
                      ],
                    );
                  }).toList(),
                ),
              ),
              const SizedBox(height: 24),
              // Simulation Panel (Giải thích quyết định)
              Container(
                key: const ValueKey('permission-simulation'),
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: theme.colorScheme.surfaceContainerHighest.withValues(alpha: 0.5),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: theme.colorScheme.outlineVariant),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Icon(Icons.psychology_alt_outlined, size: 20),
                        const SizedBox(width: 8),
                        const Flexible(
                          child: Text(
                            'Mô phỏng & Giải thích quyết định (Policy Simulation)',
                            style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Expanded(
                          child: DropdownButtonFormField<String>(
                            initialValue: controller.selectedSimulationAction.value.isEmpty
                                ? data.catalog.firstOrNull?.permissionKey
                                : controller.selectedSimulationAction.value,
                            decoration: const InputDecoration(
                              labelText: 'Chọn hành động kiểm tra',
                              border: OutlineInputBorder(),
                              contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                            ),
                            items: data.catalog
                                .map((c) => DropdownMenuItem(
                                      value: c.permissionKey,
                                      child: Text(c.permissionKey, style: const TextStyle(fontSize: 13)),
                                    ))
                                .toList(),
                            onChanged: (val) {
                              if (val != null) {
                                controller.selectedSimulationAction.value = val;
                              }
                            },
                          ),
                        ),
                        const SizedBox(width: 12),
                        ElevatedButton(
                          onPressed: controller.isSimulating.value
                              ? null
                              : () => controller.simulateAction(
                                    controller.selectedSimulationAction.value,
                                  ),
                          child: controller.isSimulating.value
                              ? const SizedBox(
                                  width: 16,
                                  height: 16,
                                  child: CircularProgressIndicator(strokeWidth: 2),
                                )
                              : const Text('Mô phỏng'),
                        ),
                      ],
                    ),
                    if (controller.simulationResult.value != null) ...[
                      const SizedBox(height: 16),
                      const Divider(),
                      const SizedBox(height: 8),
                      const Text(
                        'Kết quả phân tích quyết định:',
                        style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
                      ),
                      const SizedBox(height: 8),
                      ...controller.simulationResult.value!.impacts.map((impact) {
                        return Container(
                          margin: const EdgeInsets.only(bottom: 8),
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: theme.colorScheme.surface,
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(color: theme.colorScheme.outlineVariant),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                children: [
                                  Text(
                                    'Hành động: ${impact.action}',
                                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
                                  ),
                                  const Spacer(),
                                  Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                                    decoration: BoxDecoration(
                                      color: impact.effect == 'ALLOW'
                                          ? Colors.green.shade100
                                          : impact.effect == 'REQUIRE_APPROVAL'
                                              ? Colors.orange.shade100
                                              : Colors.red.shade100,
                                      borderRadius: BorderRadius.circular(4),
                                    ),
                                    child: Text(
                                      impact.effect,
                                      style: TextStyle(
                                        fontSize: 11,
                                        fontWeight: FontWeight.bold,
                                        color: impact.effect == 'ALLOW'
                                            ? Colors.green.shade900
                                            : impact.effect == 'REQUIRE_APPROVAL'
                                                ? Colors.orange.shade900
                                                : Colors.red.shade900,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 4),
                              Text(
                                'Giải thích: ${impact.reason}',
                                style: TextStyle(fontSize: 12, color: theme.colorScheme.onSurfaceVariant),
                              ),
                            ],
                          ),
                        );
                      }),
                    ],
                  ],
                ),
              ),
            ],
          );
        }),
      ),
    );
  }
}
