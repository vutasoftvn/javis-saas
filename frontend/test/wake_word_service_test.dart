import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/services/wake_word_service.dart';

void main() {
  group('WakeWordService Phrase Matching & Normalization', () {
    late WakeWordService service;

    setUp(() {
      service = WakeWordService();
    });

    test('normalizes Vietnamese diacritics and casing correctly', () {
      expect(WakeWordService.normalizeText('Chào COSA'), equals('chao cosa'));
      expect(WakeWordService.normalizeText('COSA ơi!'), equals('cosa oi'));
      expect(WakeWordService.normalizeText('Chào cô sa...'), equals('chao co sa'));
      expect(WakeWordService.normalizeText('   HÉ LÔ  COSA   '), equals('he lo cosa'));
    });

    test('matches various "Chào COSA" phrases', () {
      expect(service.matchesWakeWord('Chào COSA'), isTrue);
      expect(service.matchesWakeWord('chao cosa'), isTrue);
      expect(service.matchesWakeWord('Chào cô sa'), isTrue);
      expect(service.matchesWakeWord('Alo, chào cosa nhé!'), isTrue);
    });

    test('matches "COSA ơi" phrases', () {
      expect(service.matchesWakeWord('COSA ơi'), isTrue);
      expect(service.matchesWakeWord('cosa oi'), isTrue);
      expect(service.matchesWakeWord('cô sa ơi'), isTrue);
      expect(service.matchesWakeWord('Này cosa ơi giúp mình với'), isTrue);
    });

    test('matches "Hi COSA" and "Hey COSA" phrases', () {
      expect(service.matchesWakeWord('Hi COSA'), isTrue);
      expect(service.matchesWakeWord('hi co sa'), isTrue);
      expect(service.matchesWakeWord('Hey cosa'), isTrue);
      expect(service.matchesWakeWord('Hello COSA'), isTrue);
      expect(service.matchesWakeWord('Alo cô xa'), isTrue);
      expect(service.matchesWakeWord('chào cô xa'), isTrue);
      expect(service.matchesWakeWord('cô xa ơi'), isTrue);
    });

    test('does not trigger on unrelated sentences', () {
      expect(service.matchesWakeWord('Hôm nay thời tiết thế nào'), isFalse);
      expect(service.matchesWakeWord('Báo cáo doanh thu tháng này'), isFalse);
      expect(service.matchesWakeWord(''), isFalse);
    });
  });
}
