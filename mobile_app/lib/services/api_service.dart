import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import '../models/models.dart';

class ApiService {
  static const String baseUrl = "https://stokvigil-backend-xxxx.a.run.app"; // Cloud Run URL

  Future<bool> saveIciciCredentials({
    required String userId,
    required String appKey,
    required String secretKey,
    required String sessionToken,
  }) async {
    try {
      final res = await http.post(
        Uri.parse('$baseUrl/api/user/credentials'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'user_id': userId,
          'app_key': appKey,
          'secret_key': secretKey,
          'session_token': sessionToken,
        }),
      );
      return res.statusCode == 200;
    } catch (e) {
      debugPrint("API Error saving credentials: $e");
      return false;
    }
  }

  Future<Map<String, dynamic>> fetchPortfolioSummary(String userId) async {
    try {
      final res = await http.get(Uri.parse('$baseUrl/api/user/portfolio?user_id=$userId'));
      if (res.statusCode == 200) {
        return jsonDecode(res.body);
      }
    } catch (e) {
      debugPrint("API Error fetching portfolio: $e");
    }
    return {
      "has_credentials": false,
      "total_portfolio_value": 0.0,
      "total_pnl": 0.0,
      "total_pnl_percent": 0.0,
      "holdings": []
    };
  }

  Future<List<StokAlert>> fetchAlerts(String userId) async {
    try {
      final res = await http.get(Uri.parse('$baseUrl/api/user/alerts?user_id=$userId'));
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        final list = (data['alerts'] as List? ?? []);
        return list.map((item) => StokAlert.fromJson(item)).toList();
      }
    } catch (e) {
      debugPrint("API Error fetching alerts: $e");
    }
    return [];
  }

  Future<bool> registerDeviceToken({
    required String userId,
    String? fcmToken,
    String? telegramChatId,
    bool? telegramEnabled,
  }) async {
    try {
      final res = await http.post(
        Uri.parse('$baseUrl/api/auth/register-device'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'user_id': userId,
          if (fcmToken != null) 'fcm_device_token': fcmToken,
          if (telegramChatId != null) 'telegram_chat_id': telegramChatId,
          if (telegramEnabled != null) 'telegram_enabled': telegramEnabled,
        }),
      );
      return res.statusCode == 200;
    } catch (e) {
      debugPrint("API Error registering device token: $e");
      return false;
    }
  }
}
