import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/data/models/finance_legal_models.dart';
import 'package:frontend/data/models/source_value_state.dart';

void main() {
  group('FinancialTransactionModel', () {
    test('financial transaction preserves missing amount as unavailable', () {
      final model = FinancialTransactionModel.fromJson({
        'id': 'tx-1',
        'transactionDate': 'bad',
      });
      expect(model.amountState, SourceValueState.unavailable);
      expect(model.amount, isNull);
      expect(model.transactionDateState, SourceValueState.invalid);
      expect(model.transactionDate, isNull);
    });

    test('preserves exact decimal string representation without binary double loss', () {
      final model = FinancialTransactionModel.fromJson({
        'id': 'tx-2',
        'amount': '0.10',
        'currency': 'USD',
        'transaction_date': '2026-09-19T10:00:00Z',
      });
      expect(model.amountState, SourceValueState.present);
      expect(model.amount?.decimal, '0.10');
      expect(model.amount?.currency, 'USD');
      expect(model.transactionDateState, SourceValueState.present);
      expect(model.transactionDate, DateTime.parse('2026-09-19T10:00:00Z'));
    });

    test('marks unparseable amount as invalid', () {
      final model = FinancialTransactionModel.fromJson({
        'id': 'tx-3',
        'amount': 'not-a-number',
        'transaction_date': '2026-09-19T10:00:00Z',
      });
      expect(model.amountState, SourceValueState.invalid);
      expect(model.amount, isNull);
    });

    test('handles numeric amount properly', () {
      final model = FinancialTransactionModel.fromJson({
        'id': 'tx-4',
        'amount': 500000,
        'currency': 'VND',
        'transaction_date': '2026-09-19T10:00:00Z',
      });
      expect(model.amountState, SourceValueState.present);
      expect(model.amount?.decimal, '500000');
      expect(model.amount?.currency, 'VND');
    });
  });

  group('AccountingPeriodModel', () {
    test('preserves missing and invalid dates without defaulting to DateTime.now()', () {
      final model = AccountingPeriodModel.fromJson({
        'id': 'p-1',
        'endDate': 'invalid-date',
      });
      expect(model.startDateState, SourceValueState.unavailable);
      expect(model.startDate, isNull);
      expect(model.endDateState, SourceValueState.invalid);
      expect(model.endDate, isNull);
    });

    test('parses valid dates as present', () {
      final model = AccountingPeriodModel.fromJson({
        'id': 'p-2',
        'start_date': '2026-01-01T00:00:00Z',
        'end_date': '2026-01-31T23:59:59Z',
        'status': 'open',
      });
      expect(model.startDateState, SourceValueState.present);
      expect(model.startDate, DateTime.parse('2026-01-01T00:00:00Z'));
      expect(model.endDateState, SourceValueState.present);
      expect(model.endDate, DateTime.parse('2026-01-31T23:59:59Z'));
    });
  });

  group('FinanceSnapshotModel', () {
    test('preserves missing amounts and generatedAt as unavailable', () {
      final model = FinanceSnapshotModel.fromJson({
        'period_id': 'p-1',
      });
      expect(model.totalIncomeState, SourceValueState.unavailable);
      expect(model.totalIncome, isNull);
      expect(model.totalExpenseState, SourceValueState.unavailable);
      expect(model.totalExpense, isNull);
      expect(model.netCashflowState, SourceValueState.unavailable);
      expect(model.netCashflow, isNull);
      expect(model.generatedAtState, SourceValueState.unavailable);
      expect(model.generatedAt, isNull);
    });

    test('preserves exact decimal for financial summary', () {
      final model = FinanceSnapshotModel.fromJson({
        'period_id': 'p-2',
        'total_income': '150000.50',
        'total_expense': '80000.25',
        'net_cashflow': '70000.25',
        'runway_months': '12.5',
        'generated_at': '2026-09-19T00:00:00Z',
      });
      expect(model.totalIncomeState, SourceValueState.present);
      expect(model.totalIncome?.decimal, '150000.50');
      expect(model.totalExpenseState, SourceValueState.present);
      expect(model.totalExpense?.decimal, '80000.25');
      expect(model.netCashflowState, SourceValueState.present);
      expect(model.netCashflow?.decimal, '70000.25');
      expect(model.runwayMonthsState, SourceValueState.present);
      expect(model.runwayMonths, 12.5);
      expect(model.generatedAtState, SourceValueState.present);
    });
  });

  group('LegalObligationModel', () {
    test('preserves missing and invalid due dates', () {
      final modelMissing = LegalObligationModel.fromJson({
        'id': 'leg-1',
        'title': 'Tax filing',
      });
      expect(modelMissing.dueDateState, SourceValueState.unavailable);
      expect(modelMissing.dueDate, isNull);

      final modelInvalid = LegalObligationModel.fromJson({
        'id': 'leg-2',
        'title': 'Tax filing',
        'due_date': 'unparseable',
      });
      expect(modelInvalid.dueDateState, SourceValueState.invalid);
      expect(modelInvalid.dueDate, isNull);
    });
  });
}
