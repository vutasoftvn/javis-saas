import 'dart:convert';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/data/models/doctor_report_model.dart';

class DiagnosticsService {
  static Future<DoctorReportModel?> runDoctorReport() async {
    try {
      final res = await ApiClient.get('/runtime/doctor');
      if (res.statusCode == 200) {
        final data = jsonDecode(utf8.decode(res.bodyBytes));
        return DoctorReportModel.fromJson(data);
      }
    } catch (_) {}
    return null;
  }
}
