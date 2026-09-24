import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/modules/agents/views/widgets/agent_card.dart';

void main() {
  const agent = {
    'name': 'CFO Advisor',
    'department': 'Finance',
    'status': 'active',
    'key': 'finance',
  };

  testWidgets('AgentCard without onTestRun renders no Test Run button', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(body: SizedBox(width: 320, height: 420, child: AgentCard(agent: agent))),
      ),
    );

    expect(find.text('Test Run'), findsNothing);
  });

  testWidgets('AgentCard with onTestRun (Agents module) still renders it', (tester) async {
    var taps = 0;
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SizedBox(
            width: 320,
            height: 420,
            child: AgentCard(agent: agent, onTestRun: () => taps++),
          ),
        ),
      ),
    );

    await tester.tap(find.text('Test Run'));
    expect(taps, 1);
  });
}
