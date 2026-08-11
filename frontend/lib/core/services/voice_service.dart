import 'dart:async';
import 'dart:convert';
import 'dart:io' show File;
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:path_provider/path_provider.dart';
import 'package:record/record.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../network/api_client.dart';

abstract class IVoiceService {
  Future<bool> startRecording();
  Future<String?> stopRecordingAndTranscribe({String language = 'vi'});
  bool get isRecording;
}

class VoiceService implements IVoiceService {
  static final VoiceService _instance = VoiceService._internal();
  factory VoiceService() => _instance;
  VoiceService._internal();

  final AudioRecorder _recorder = AudioRecorder();
  bool _isRecording = false;

  @override
  bool get isRecording => _isRecording;

  @override
  Future<bool> startRecording() async {
    if (kIsWeb) {
      // record's web backend returns a blob URL rather than a real file
      // path - not wired up on this side yet, so fail honestly instead of
      // pretending to capture audio (push-to-talk MVP targets mobile/desktop
      // first per the roadmap; web is a later pass, not "fake it for now").
      debugPrint('[VoiceService] Mic capture not yet supported on web.');
      return false;
    }

    final granted = await _recorder.hasPermission();
    if (!granted) {
      debugPrint('[VoiceService] Microphone permission denied.');
      return false;
    }

    try {
      final dir = await getTemporaryDirectory();
      final path = '${dir.path}/voice_${DateTime.now().millisecondsSinceEpoch}.m4a';
      await _recorder.start(const RecordConfig(encoder: AudioEncoder.aacLc), path: path);
      _isRecording = true;
      debugPrint('[VoiceService] Started recording to $path');
      return true;
    } catch (e) {
      debugPrint('[VoiceService] Failed to start recording: $e');
      return false;
    }
  }

  @override
  Future<String?> stopRecordingAndTranscribe({String language = 'vi'}) async {
    if (!_isRecording) return null;
    _isRecording = false;

    final path = await _recorder.stop();
    if (path == null) {
      debugPrint('[VoiceService] Recorder returned no file path.');
      return null;
    }

    final prefs = await SharedPreferences.getInstance();
    final workspaceId = prefs.getString('workspace_id');
    final token = prefs.getString('auth_token');
    if (workspaceId == null) return null;

    final audioFile = File(path);
    try {
      if (!await audioFile.exists()) {
        debugPrint('[VoiceService] Recorded file does not exist: $path');
        return null;
      }
      final audioBytes = await audioFile.readAsBytes();
      if (audioBytes.isEmpty) {
        debugPrint('[VoiceService] Recorded 0 bytes - nothing to transcribe.');
        return null;
      }

      final apiUri = Uri.parse(ApiClient.baseUrl);
      final uri = apiUri.replace(
        path: '${apiUri.path}/chat/transcribe-voice',
        queryParameters: {'workspace_id': workspaceId},
      );

      final request = http.MultipartRequest('POST', uri);
      if (token != null && token.isNotEmpty) {
        request.headers['Authorization'] = 'Bearer $token';
      }
      request.files.add(
        http.MultipartFile.fromBytes('file', audioBytes, filename: 'voice_input.m4a'),
      );
      request.fields['language'] = language;

      final streamedResponse = await request.send();
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        final transcript = data['transcript'] as String?;
        debugPrint('[VoiceService] Recognized transcript: $transcript');
        return transcript;
      }
      debugPrint('[VoiceService] Transcription error: ${response.statusCode} ${response.body}');
      return null;
    } catch (e) {
      debugPrint('[VoiceService] Transcription exception: $e');
      return null;
    } finally {
      // Raw audio is not persisted by default (blueprint §34) - only the
      // resulting transcript, as a normal chat message. Delete the temp
      // recording regardless of whether the upload succeeded.
      unawaited(audioFile.delete().catchError((_) => audioFile));
    }
  }
}
