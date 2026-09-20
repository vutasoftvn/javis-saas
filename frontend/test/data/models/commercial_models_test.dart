import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/data/models/commercial_models.dart';
import 'package:frontend/data/models/source_value_state.dart';

void main() {
  group('LeadModel', () {
    test('preserves missing createdAt as unavailable without defaulting to DateTime.now()', () {
      final model = LeadModel.fromJson({
        'id': 'lead-1',
        'name': 'Acme Corp',
        'email': 'contact@acme.com',
      });
      expect(model.createdAtState, SourceValueState.unavailable);
      expect(model.createdAt, isNull);
    });

    test('preserves invalid createdAt as invalid without defaulting to DateTime.now()', () {
      final model = LeadModel.fromJson({
        'id': 'lead-2',
        'name': 'Acme Corp',
        'email': 'contact@acme.com',
        'created_at': 'not-a-valid-date',
      });
      expect(model.createdAtState, SourceValueState.invalid);
      expect(model.createdAt, isNull);
    });

    test('parses valid createdAt as present', () {
      final model = LeadModel.fromJson({
        'id': 'lead-3',
        'name': 'Acme Corp',
        'email': 'contact@acme.com',
        'created_at': '2026-09-19T12:00:00Z',
      });
      expect(model.createdAtState, SourceValueState.present);
      expect(model.createdAt, DateTime.parse('2026-09-19T12:00:00Z'));
    });
  });

  group('OpportunityModel', () {
    test('preserves missing amount as unavailable without defaulting to 0.0', () {
      final model = OpportunityModel.fromJson({
        'id': 'opp-1',
        'name': 'Series A Advisory',
        'account_id': 'acc-1',
      });
      expect(model.amountState, SourceValueState.unavailable);
      expect(model.amount, isNull);
      expect(model.createdAtState, SourceValueState.unavailable);
      expect(model.createdAt, isNull);
    });

    test('preserves exact decimal string for deal amount without IEEE-754 precision loss', () {
      final model = OpportunityModel.fromJson({
        'id': 'opp-2',
        'name': 'Platform License',
        'account_id': 'acc-2',
        'amount': '0.10',
        'currency': 'USD',
        'created_at': '2026-09-19T14:30:00Z',
      });
      expect(model.amountState, SourceValueState.present);
      expect(model.amount?.decimal, '0.10');
      expect(model.amount?.currency, 'USD');
      expect(model.createdAtState, SourceValueState.present);
      expect(model.createdAt, DateTime.parse('2026-09-19T14:30:00Z'));
    });

    test('marks unparseable deal amount as invalid', () {
      final model = OpportunityModel.fromJson({
        'id': 'opp-3',
        'name': 'Enterprise Plan',
        'account_id': 'acc-3',
        'amount': 'NaN',
      });
      expect(model.amountState, SourceValueState.invalid);
      expect(model.amount, isNull);
    });
  });

  group('CustomerModel', () {
    test('preserves missing and invalid MRR without defaulting to 0.0', () {
      final modelMissing = CustomerModel.fromJson({
        'id': 'cust-1',
        'account_id': 'acc-1',
        'name': 'Client 1',
      });
      expect(modelMissing.mrrState, SourceValueState.unavailable);
      expect(modelMissing.mrr, isNull);

      final modelPresent = CustomerModel.fromJson({
        'id': 'cust-2',
        'account_id': 'acc-2',
        'name': 'Client 2',
        'mrr': '25000000',
      });
      expect(modelPresent.mrrState, SourceValueState.present);
      expect(modelPresent.mrr?.decimal, '25000000');
    });
  });

  group('CampaignModel', () {
    test('preserves missing and invalid budget and spend without defaulting to 0.0', () {
      final model = CampaignModel.fromJson({
        'id': 'cmp-1',
        'name': 'Q3 Launch',
      });
      expect(model.budgetState, SourceValueState.unavailable);
      expect(model.budget, isNull);
      expect(model.spendState, SourceValueState.unavailable);
      expect(model.spend, isNull);
    });
  });
}
