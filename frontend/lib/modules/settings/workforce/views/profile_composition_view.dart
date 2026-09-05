import 'package:flutter/material.dart';

class AgentReadinessItem {
  final String profileId;
  final String profileName;
  final List<String> missingCapabilities;
  final List<String> missingPermissions;
  final bool isReady;

  const AgentReadinessItem({
    required this.profileId,
    required this.profileName,
    this.missingCapabilities = const [],
    this.missingPermissions = const [],
    this.isReady = true,
  });
}

class ProfileCompositionView extends StatelessWidget {
  final List<AgentReadinessItem>? items;

  const ProfileCompositionView({
    super.key,
    this.items,
  });

  @override
  Widget build(BuildContext context) {
    final list = items ?? [];

    return Scaffold(
      appBar: AppBar(
        title: const Text('Profile Composition & Readiness'),
      ),
      body: list.isEmpty
          ? const Center(
              child: Text(
                'Danh sách profile và giải thích các tool không khả dụng sẽ hiển thị ở đây.',
              ),
            )
          : ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: list.length,
              itemBuilder: (context, index) {
                final item = list[index];
                return Card(
                  key: ValueKey('card_${item.profileId}'),
                  margin: const EdgeInsets.only(bottom: 16),
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Expanded(
                              child: Text(
                                item.profileName,
                                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                      fontWeight: FontWeight.bold,
                                    ),
                              ),
                            ),
                            if (item.missingCapabilities.isEmpty &&
                                item.missingPermissions.isEmpty)
                              Chip(
                                key: ValueKey('ready_${item.profileId}'),
                                label: const Text('Ready'),
                                backgroundColor: Colors.green.shade100,
                              )
                            else
                              Chip(
                                key: ValueKey('not_ready_${item.profileId}'),
                                label: const Text('Action Required'),
                                backgroundColor: Colors.amber.shade100,
                              ),
                          ],
                        ),
                        const SizedBox(height: 12),

                        // Phân tách rõ ràng: 1. Missing Capabilities (thiếu tools/code)
                        if (item.missingCapabilities.isNotEmpty) ...[
                          Row(
                            children: [
                              const Icon(Icons.build_circle_outlined, color: Colors.orange, size: 18),
                              const SizedBox(width: 8),
                              Text(
                                'Missing Capabilities (${item.missingCapabilities.length})',
                                style: const TextStyle(fontWeight: FontWeight.w600, color: Colors.orange),
                              ),
                            ],
                          ),
                          const SizedBox(height: 6),
                          Container(
                            key: ValueKey('missing_capabilities_${item.profileId}'),
                            padding: const EdgeInsets.all(8),
                            decoration: BoxDecoration(
                              color: Colors.orange.shade50,
                              borderRadius: BorderRadius.circular(6),
                              border: Border.all(color: Colors.orange.shade200),
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: item.missingCapabilities
                                  .map((c) => Text('• $c', style: const TextStyle(fontSize: 13)))
                                  .toList(),
                            ),
                          ),
                          const SizedBox(height: 12),
                        ],

                        // Phân tách rõ ràng: 2. Missing Permissions (thiếu quyền truy cập runtime)
                        if (item.missingPermissions.isNotEmpty) ...[
                          Row(
                            children: [
                              const Icon(Icons.lock_outline, color: Colors.redAccent, size: 18),
                              const SizedBox(width: 8),
                              Text(
                                'Missing Permissions (${item.missingPermissions.length})',
                                style: const TextStyle(fontWeight: FontWeight.w600, color: Colors.redAccent),
                              ),
                            ],
                          ),
                          const SizedBox(height: 6),
                          Container(
                            key: ValueKey('missing_permissions_${item.profileId}'),
                            padding: const EdgeInsets.all(8),
                            decoration: BoxDecoration(
                              color: Colors.red.shade50,
                              borderRadius: BorderRadius.circular(6),
                              border: Border.all(color: Colors.red.shade200),
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: item.missingPermissions
                                  .map((p) => Text('• $p', style: const TextStyle(fontSize: 13)))
                                  .toList(),
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                );
              },
            ),
    );
  }
}
