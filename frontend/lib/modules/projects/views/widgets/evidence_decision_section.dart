import 'package:flutter/material.dart';
import '../../models/project_operating_loop.dart';
import '../../controllers/project_operating_loop_controller.dart';

class EvidenceDecisionSection extends StatelessWidget {
  final ProjectOperatingLoopController controller;
  final List<LoopEvidence> evidence;
  final List<LoopDecision> decisions;

  const EvidenceDecisionSection({
    super.key,
    required this.controller,
    this.evidence = const [],
    this.decisions = const [],
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Padding(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Evidence & Decisions',
            style: theme.textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 16),
          Text(
            'Evidence (${evidence.length})',
            style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 8),
          if (evidence.isEmpty)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Center(
                  child: Text(
                    'No evidence recorded for this project yet.',
                    style: theme.textTheme.bodyMedium?.copyWith(color: theme.hintColor),
                  ),
                ),
              ),
            )
          else
            ListView.builder(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: evidence.length,
              itemBuilder: (context, index) {
                final ev = evidence[index];
                return Card(
                  margin: const EdgeInsets.only(bottom: 8),
                  child: ListTile(
                    key: Key('evidence_${ev.id}'),
                    leading: const Icon(Icons.verified_outlined),
                    title: Text(ev.title),
                    subtitle: Text('Source: ${ev.sourceType} · Status: ${ev.status.toUpperCase()}'),
                  ),
                );
              },
            ),
          const SizedBox(height: 16),
          Text(
            'Decisions (${decisions.length})',
            style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 8),
          if (decisions.isEmpty)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Center(
                  child: Text(
                    'No decisions recorded for this project yet.',
                    style: theme.textTheme.bodyMedium?.copyWith(color: theme.hintColor),
                  ),
                ),
              ),
            )
          else
            ListView.builder(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: decisions.length,
              itemBuilder: (context, index) {
                final dec = decisions[index];
                return Card(
                  margin: const EdgeInsets.only(bottom: 8),
                  child: ListTile(
                    key: Key('decision_${dec.id}'),
                    leading: const Icon(Icons.gavel_outlined),
                    title: Text(dec.title),
                    subtitle: Text('Status: ${dec.status.toUpperCase()}'),
                  ),
                );
              },
            ),
        ],
      ),
    );
  }
}
