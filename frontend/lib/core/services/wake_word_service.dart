import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:speech_to_text/speech_recognition_error.dart';
import 'package:speech_to_text/speech_recognition_result.dart';
import 'package:speech_to_text/speech_to_text.dart';

abstract class IWakeWordService {
  Future<bool> initialize({required void Function(String wakeWord) onWakeWord});
  Future<void> startListening();
  Future<void> stopListening();
  bool get isListening;
  bool get isAvailable;
  bool matchesWakeWord(String text);
  void dispose();
}

/// Hands-free Wake Word Detection Service (mCOSA V12.1 §17).
///
/// Listens locally on device for hotwords such as:
/// - "Chào COSA", "Chao COSA", "Chào cô sa"
/// - "Hi COSA", "Hey COSA", "Hello COSA"
/// - "COSA ơi", "Cosa oi", "Cô sa ơi"
///
/// Runs offline on device, triggers [onWakeWord] callback to wake the hologram
/// and initiate LiveKit Realtime Voice.
class WakeWordService implements IWakeWordService {
  static final WakeWordService _instance = WakeWordService._internal();
  factory WakeWordService({SpeechToText? speechToText}) {
    if (speechToText != null) {
      return WakeWordService._withSpeechToText(speechToText);
    }
    return _instance;
  }

  WakeWordService._internal() : _speech = SpeechToText();
  WakeWordService._withSpeechToText(this._speech);

  final SpeechToText _speech;
  void Function(String wakeWord)? _onWakeWord;
  bool _isAvailable = false;
  bool _shouldBeListening = false;
  String? _preferredLocaleId;
  Timer? _restartTimer;

  static const List<String> defaultWakeWords = [
    // Chao / Xin Chao / Hello variations
    'xin chao',
    'chao',
    'hello',
    'hi',
    'he lo',
    'alo',
    'xin chao cosa',
    'xin chao co sa',
    'chao cosa',
    'chao co sa',
    'chao co xa',
    'chao kosa',
    'chao ca sa',
    'chao co ta',
    'hi cosa',
    'hi co sa',
    'hi co xa',
    'hi kosa',
    'hey cosa',
    'hey co sa',
    'hey co xa',
    'hey kosa',
    'hello cosa',
    'hello co sa',
    'hello co xa',
    'alo cosa',
    'alo co sa',
    'alo co xa',
    'e cosa',
    'e co sa',

    // "COSA ơi" variations
    'cosa oi',
    'co sa oi',
    'co xa oi',
    'kosa oi',
    'ca sa oi',
    'co ta oi',
    'kho sa oi',

    // Standalone keyword variations
    'cosa',
    'co sa',
    'co xa',
    'kosa',
    'ca sa',
    'kho sa',
    'tro ly cosa',
    'tro ly co sa',
  ];

  @override
  bool get isListening => _speech.isListening;

  @override
  bool get isAvailable => _isAvailable;

  @override
  Future<bool> initialize({required void Function(String wakeWord) onWakeWord}) async {
    _onWakeWord = onWakeWord;

    if (kIsWeb) {
      debugPrint('[WakeWordService] Speech recognition passive listening not enabled on web.');
      return false;
    }

    try {
      _isAvailable = await _speech.initialize(
        onError: _onError,
        onStatus: _onStatus,
      );

      if (_isAvailable) {
        try {
          final locales = await _speech.locales();
          for (final l in locales) {
            if (l.localeId.toLowerCase().startsWith('vi')) {
              _preferredLocaleId = l.localeId;
              break;
            }
          }
        } catch (_) {}
      }

      debugPrint('[WakeWordService] Initialized. Available: $_isAvailable (locale: $_preferredLocaleId)');
      return _isAvailable;
    } catch (e) {
      debugPrint('[WakeWordService] Initialization failed: $e');
      _isAvailable = false;
      return false;
    }
  }

  @override
  Future<void> startListening() async {
    if (!_isAvailable) {
      debugPrint('[WakeWordService] Cannot start listening: service not available.');
      return;
    }

    if (_speech.isListening) {
      return;
    }

    _shouldBeListening = true;
    _restartTimer?.cancel();

    try {
      await _speech.listen(
        onResult: _onResult,
        listenOptions: SpeechListenOptions(
          localeId: _preferredLocaleId,
          listenFor: const Duration(hours: 1),
          pauseFor: const Duration(seconds: 5),
          partialResults: true,
          cancelOnError: false,
          listenMode: ListenMode.dictation,
        ),
      );
      debugPrint('[WakeWordService] Passive listening started (locale: $_preferredLocaleId).');
    } catch (e) {
      debugPrint('[WakeWordService] Start listening error: $e');
      _scheduleRestart();
    }
  }

  @override
  Future<void> stopListening() async {
    _shouldBeListening = false;
    _restartTimer?.cancel();
    if (_speech.isListening) {
      await _speech.stop();
      debugPrint('[WakeWordService] Passive listening stopped.');
    }
  }

  void _onResult(SpeechRecognitionResult result) {
    final words = result.recognizedWords;
    if (words.isEmpty) return;

    debugPrint('[WakeWordService] Heard words: "$words"');
    if (matchesWakeWord(words)) {
      debugPrint('[WakeWordService] >>> Wake word detected in "$words"!');
      // Stop passive listener before triggering active session
      stopListening();
      _onWakeWord?.call(words);
    }
  }

  void _onError(SpeechRecognitionError error) {
    debugPrint('[WakeWordService] Error: ${error.errorMsg} (permanent: ${error.permanent})');
    if (_shouldBeListening && !error.permanent) {
      _scheduleRestart();
    }
  }

  void _onStatus(String status) {
    debugPrint('[WakeWordService] Status changed: $status');
    if (status == 'notListening' || status == 'done') {
      if (_shouldBeListening) {
        _scheduleRestart();
      }
    }
  }

  void _scheduleRestart() {
    _restartTimer?.cancel();
    if (!_shouldBeListening) return;

    _restartTimer = Timer(const Duration(milliseconds: 1000), () {
      if (_shouldBeListening && !_speech.isListening && _isAvailable) {
        startListening();
      }
    });
  }

  @override
  bool matchesWakeWord(String text) {
    final normalized = normalizeText(text);
    if (normalized.isEmpty) return false;

    for (final wakeWord in defaultWakeWords) {
      if (normalized.contains(wakeWord)) {
        return true;
      }
    }
    return false;
  }

  /// Removes Vietnamese diacritics and special characters for reliable matching
  static String normalizeText(String input) {
    var str = input.toLowerCase().trim();

    // Remove common punctuation
    str = str.replaceAll(RegExp(r'[^\w\s\u00C0-\u1EF9]'), ' ');

    const vietnameseMap = {
      'a': 'á|à|ả|ã|ạ|ă|ắ|ằ|ẳ|ẵ|ặ|â|ấ|ầ|ẩ|ẫ|ậ',
      'd': 'đ',
      'e': 'é|è|ẻ|ẽ|ẹ|ê|ế|ề|ể|ễ|ệ',
      'i': 'í|ì|ỉ|ĩ|ị',
      'o': 'ó|ò|ỏ|õ|ọ|ô|ố|ồ|ổ|ỗ|ộ|ơ|ớ|ờ|ở|ỡ|ợ',
      'u': 'ú|ù|ủ|ũ|ụ|ư|ứ|ừ|ử|ữ|ự',
      'y': 'ý|ỳ|ỷ|ỹ|ỵ',
    };

    for (final entry in vietnameseMap.entries) {
      str = str.replaceAll(RegExp(entry.value), entry.key);
    }

    // Collapse multi-spaces
    str = str.replaceAll(RegExp(r'\s+'), ' ').trim();
    return str;
  }

  @override
  void dispose() {
    _shouldBeListening = false;
    _restartTimer?.cancel();
    _speech.stop();
  }
}
