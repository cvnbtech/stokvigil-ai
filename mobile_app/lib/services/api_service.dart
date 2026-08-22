import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import '../models/models.dart';
import 'supabase_service.dart';

class ApiService {
  static const String baseUrl = String.fromEnvironment(
    'BACKEND_URL',
    defaultValue: String.fromEnvironment(
      'STOKVIGIL_BACKEND_URL',
      defaultValue: "https://stokvigil-backend-xxxx.a.run.app",
    ),
  );

  Map<String, String> _getAuthHeaders() {
    final token = SupabaseService().client.auth.currentSession?.accessToken;
    return {
      'Content-Type': 'application/json',
      if (token != null && token.isNotEmpty) 'Authorization': 'Bearer $token',
    };
  }

  Future<bool> saveIciciCredentials({
    required String userId,
    required String appKey,
    required String secretKey,
    required String sessionToken,
  }) async {
    try {
      final res = await http.post(
        Uri.parse('$baseUrl/api/user/credentials'),
        headers: _getAuthHeaders(),
        body: jsonEncode({
          'user_id': userId,
          'app_key': appKey,
          'secret_key': secretKey,
          'session_token': sessionToken,
        }),
      ).timeout(const Duration(seconds: 8));
      return res.statusCode == 200;
    } catch (e) {
      debugPrint("API Error saving credentials: $e");
      return false;
    }
  }

  Future<Map<String, dynamic>?> fetchUserCredentials(String userId) async {
    try {
      final res = await http
          .get(
            Uri.parse('$baseUrl/api/user/credentials?user_id=$userId'),
            headers: _getAuthHeaders(),
          )
          .timeout(const Duration(seconds: 6));
      if (res.statusCode == 200) {
        return jsonDecode(res.body);
      }
    } catch (e) {
      debugPrint("API Error fetching user credentials: $e");
    }
    return null;
  }

  Future<List<Map<String, dynamic>>> searchStocks(String query) async {
    if (query.trim().isEmpty) return [];
    try {
      final q = Uri.encodeComponent(query.trim());
      final res = await http
          .get(Uri.parse('$baseUrl/api/stocks/search?q=$q'))
          .timeout(const Duration(seconds: 4));
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        final list = (data['stocks'] as List?)?.map((e) => Map<String, dynamic>.from(e)).toList() ?? [];
        return list;
      }
    } catch (e) {
      debugPrint("API Error searching stocks: $e");
    }
    return [];
  }

  Future<Map<String, dynamic>> validateStock(String symbol) async {
    try {
      final sym = Uri.encodeComponent(symbol.trim().toUpperCase());
      final res = await http
          .get(Uri.parse('$baseUrl/api/stocks/validate?symbol=$sym'))
          .timeout(const Duration(seconds: 4));
      if (res.statusCode == 200) {
        return jsonDecode(res.body);
      }
    } catch (e) {
      debugPrint("API Error validating stock: $e");
    }
    return {"is_valid": true, "symbol": symbol.toUpperCase(), "exchange": "NSE"};
  }

  Future<bool> deleteUserAccount(String userId) async {
    try {
      final res = await http.post(
        Uri.parse('$baseUrl/api/user/delete-account'),
        headers: _getAuthHeaders(),
        body: jsonEncode({'user_id': userId}),
      ).timeout(const Duration(seconds: 10));
      return res.statusCode == 200;
    } catch (e) {
      debugPrint("API Error deleting account: $e");
      return false;
    }
  }

  Future<Map<String, dynamic>> fetchPortfolioSummary(String userId) async {
    try {
      final res = await http
          .get(
            Uri.parse('$baseUrl/api/user/portfolio?user_id=$userId'),
            headers: _getAuthHeaders(),
          )
          .timeout(const Duration(seconds: 8));
      if (res.statusCode == 200) {
        return jsonDecode(res.body);
      }
    } catch (e) {
      debugPrint("API Error fetching portfolio: $e");
    }

    // Check credentials directly via Supabase if backend is unreachable
    final creds = await SupabaseService().checkCredentials();
    return {
      "has_credentials": creds != null,
      "token_date": creds?['token_date'],
      "total_portfolio_value": 0.0,
      "total_investment_value": 0.0,
      "total_pnl": 0.0,
      "total_pnl_percent": 0.0,
      "holdings": []
    };
  }

  Future<List<StokAlert>> fetchAlerts(String userId) async {
    try {
      final res = await http
          .get(
            Uri.parse('$baseUrl/api/user/alerts?user_id=$userId'),
            headers: _getAuthHeaders(),
          )
          .timeout(const Duration(seconds: 6));
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        final list = (data['alerts'] as List? ?? []);
        if (list.isNotEmpty) {
          return list.map((item) => StokAlert.fromJson(item)).toList();
        }
      }
    } catch (e) {
      debugPrint("API Error fetching alerts from backend: $e");
    }

    // Direct Supabase query fallback (Live PostgreSQL RLS)
    return await SupabaseService().fetchAlerts();
  }

  Future<bool> registerDeviceToken({
    required String userId,
    String? fcmToken,
    bool? fcmEnabled,
    String? telegramChatId,
    bool? telegramEnabled,
    String? alertSensitivity,
    String? executionMode,
  }) async {
    // Update direct Supabase profile table first for instant reliability
    final profileUpdates = <String, dynamic>{};
    if (fcmToken != null) profileUpdates['fcm_device_token'] = fcmToken;
    if (fcmEnabled != null) profileUpdates['fcm_enabled'] = fcmEnabled;
    if (telegramChatId != null) profileUpdates['telegram_chat_id'] = telegramChatId;
    if (telegramEnabled != null) profileUpdates['telegram_enabled'] = telegramEnabled;
    if (alertSensitivity != null) profileUpdates['alert_sensitivity'] = alertSensitivity;
    if (executionMode != null) profileUpdates['execution_mode'] = executionMode;
    
    if (profileUpdates.isNotEmpty) {
      await SupabaseService().updateProfile(profileUpdates);
    }

    try {
      final res = await http.post(
        Uri.parse('$baseUrl/api/auth/register-device'),
        headers: _getAuthHeaders(),
        body: jsonEncode({
          'user_id': userId,
          if (fcmToken != null) 'fcm_device_token': fcmToken,
          if (fcmEnabled != null) 'fcm_enabled': fcmEnabled,
          if (telegramChatId != null) 'telegram_chat_id': telegramChatId,
          if (telegramEnabled != null) 'telegram_enabled': telegramEnabled,
          if (alertSensitivity != null) 'alert_sensitivity': alertSensitivity,
          if (executionMode != null) 'execution_mode': executionMode,
        }),
      ).timeout(const Duration(seconds: 6));
      return res.statusCode == 200;
    } catch (e) {
      debugPrint("API Error registering device token via HTTP: $e");
      return profileUpdates.isNotEmpty;
    }
  }
}
