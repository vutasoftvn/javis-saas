import 'package:flutter/material.dart';
import '../../../data/models/pmf_scoreboard_model.dart';
import '../../../data/models/evidence_model.dart';

class EvidenceBackboneTab extends StatelessWidget {
  final List<MetricContract> contracts;
  final List<MetricSnapshot> snapshots;
  final List<EvidenceItem> evidences;
  final bool isLoading;

  const EvidenceBackboneTab({
    super.key,
    this.contracts = const [],
    this.snapshots = const [],
    this.evidences = const [],
    this.isLoading = false,
  });

  @override
  Widget build(BuildContext context) {
    if (isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    return DefaultTabController(
      length: 3,
      child: Column(
        children: [
          const TabBar(
            tabs: [
              Tab(text: 'Metric Contracts', icon: Icon(Icons.description_outlined)),
              Tab(text: 'Telemetry Snapshots', icon: Icon(Icons.analytics_outlined)),
              Tab(text: 'Reviewed Evidence', icon: Icon(Icons.fact_check_outlined)),
            ],
          ),
          Expanded(
            child: TabBarView(
              children: [
                // Tab 1: Contracts
                contracts.isEmpty
                    ? const Center(child: Text('Chưa có Metric Contract nào.'))
                    : ListView.builder(
                        padding: const EdgeInsets.all(12),
                        itemCount: contracts.length,
                        itemBuilder: (context, index) {
                          final c = contracts[index];
                          return Card(
                            child: ListTile(
                              leading: const Icon(Icons.verified, color: Colors.blue),
                              title: Text(c.displayName, style: const TextStyle(fontWeight: FontWeight.bold)),
                              subtitle: Text('${c.metricKey} (v${c.versionNumber}) • ${c.cadence}'),
                              trailing: Chip(
                                label: Text(c.status.name.toUpperCase()),
                                backgroundColor: c.status == MetricContractStatus.active
                                    ? Colors.green.shade100
                                    : Colors.grey.shade200,
                              ),
                            ),
                          );
                        },
                      ),

                // Tab 2: Snapshots
                snapshots.isEmpty
                    ? const Center(child: Text('Chưa có Metric Snapshot nào.'))
                    : ListView.builder(
                        padding: const EdgeInsets.all(12),
                        itemCount: snapshots.length,
                        itemBuilder: (context, index) {
                          final s = snapshots[index];
                          final isStale = s.qualityStatus == MetricSnapshotQuality.stale;
                          return Card(
                            child: ListTile(
                              leading: Icon(
                                isStale ? Icons.warning_amber : Icons.check_circle,
                                color: isStale ? Colors.orange : Colors.green,
                              ),
                              title: Text('Value: ${(s.value * 100).toStringAsFixed(1)}% (${s.sourceSystem})'),
                              subtitle: Text('Window: ${s.sourceWindow} • Record: ${s.sourceRecordId}'),
                              trailing: Chip(
                                label: Text(s.qualityStatus.name.toUpperCase()),
                                backgroundColor: isStale ? Colors.orange.shade100 : Colors.green.shade100,
                              ),
                            ),
                          );
                        },
                      ),

                // Tab 3: Reviewed Evidences
                evidences.isEmpty
                    ? const Center(child: Text('Chưa có Evidence nào.'))
                    : ListView.builder(
                        padding: const EdgeInsets.all(12),
                        itemCount: evidences.length,
                        itemBuilder: (context, index) {
                          final e = evidences[index];
                          return Card(
                            child: ListTile(
                              leading: Icon(
                                e.supportsOrRefutes == 'supports' ? Icons.thumb_up : Icons.thumb_down,
                                color: e.supportsOrRefutes == 'supports' ? Colors.green : Colors.red,
                              ),
                              title: Text(e.claim, maxLines: 2, overflow: TextOverflow.ellipsis),
                              subtitle: Text('Source: ${e.sourceType} • Status: ${e.status}'),
                            ),
                          );
                        },
                      ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
