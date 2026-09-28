import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/modules/projects/models/ai_initiative_portfolio.dart';
import 'package:frontend/modules/projects/views/widgets/ai_initiative_portfolio_card.dart';

void main() {
  Widget cardFor(AiInitiativePortfolioItem item) {
    return MaterialApp(
      home: Scaffold(
        body: AiInitiativePortfolioCard(item: item),
      ),
    );
  }

  final missingBaselineInitiative = AiInitiativePortfolioItem(
    initiativeId: 'init_1',
    initiativeRevision: 1,
    title: 'Customer Support Pilot',
    lifecycleState: 'PILOT',
    riskTier: 'LOW',
    autonomyTier: 'A1',
    businessOwnerMemberId: 'mem_1',
    baselineMetricValue: null,
    targetMetricValue: '90%',
    latestOutcomeValue: null,
    costBudgetStatus: 'OK',
    adoptionStatus: 'NO_DATA',
    qualityStatus: 'PASSED',
    dataReadinessStatus: 'LEVEL_1',
    nextRequiredGate: 'VALIDATION_BASELINE_AND_METRICS',
    blockingReasons: ['Missing baseline metric'],
    authorizedActions: ['promote_to_validate'],
  );

  final scaledInitiative = AiInitiativePortfolioItem(
    initiativeId: 'init_2',
    initiativeRevision: 2,
    title: 'Code Review Copilot',
    lifecycleState: 'SCALE_CANDIDATE',
    riskTier: 'MEDIUM',
    autonomyTier: 'A2',
    businessOwnerMemberId: 'mem_2',
    baselineMetricValue: '45 mins',
    targetMetricValue: '15 mins',
    latestOutcomeValue: '18 mins',
    costBudgetStatus: 'OK',
    adoptionStatus: 'HEALTHY',
    qualityStatus: 'PASSED',
    dataReadinessStatus: 'LEVEL_2',
    nextRequiredGate: 'SCALED_HUMAN_ESCALATION',
    blockingReasons: [],
    authorizedActions: ['scale_initiative'],
  );

  testWidgets('renders Chưa có baseline instead of 0 and blocks scale CTA', (tester) async {
    await tester.pumpWidget(cardFor(missingBaselineInitiative));
    expect(find.text('Chưa có baseline'), findsOneWidget);
    expect(find.byKey(const Key('scale_initiative')), findsNothing);
  });

  testWidgets('renders baseline and allows scale CTA when authorized', (tester) async {
    await tester.pumpWidget(cardFor(scaledInitiative));
    expect(find.text('45 mins'), findsOneWidget);
    expect(find.byKey(const Key('scale_initiative')), findsOneWidget);
  });
}
