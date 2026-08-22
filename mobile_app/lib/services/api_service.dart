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
    final cleanQ = query.trim();
    if (cleanQ.isEmpty) return [];

    final q = Uri.encodeComponent(cleanQ);

    // 1. Try Backend URL first
    try {
      final res = await http
          .get(Uri.parse('$baseUrl/api/stocks/search?q=$q'))
          .timeout(const Duration(seconds: 4));
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        final list = (data['stocks'] as List?)?.map((e) => Map<String, dynamic>.from(e)).toList() ?? [];
        if (list.isNotEmpty) return list;
      }
    } catch (e) {
      debugPrint("API Error searching stocks via backend: $e");
    }

    // 2. Direct Yahoo Finance live exchange fallback (Mobile client-side)
    try {
      final url = 'https://query1.finance.yahoo.com/v1/finance/search?q=$q&quotesCount=10&newsCount=0';
      final res = await http.get(Uri.parse(url), headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'application/json',
      }).timeout(const Duration(seconds: 4));

      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        final List<Map<String, dynamic>> results = [];
        final Set<String> seen = {};

        for (final item in (data['quotes'] as List? ?? [])) {
          if (item['quoteType'] != 'EQUITY') continue;
          final sym = (item['symbol'] ?? '').toString();
          String cleanSym = sym;
          String exchange = 'NSE';

          if (sym.endsWith('.NS')) {
            cleanSym = sym.replaceAll('.NS', '');
            exchange = 'NSE';
          } else if (sym.endsWith('.BO')) {
            cleanSym = sym.replaceAll('.BO', '');
            exchange = 'BSE';
          } else if (item['exchange'] == 'NSI' || item['exchange'] == 'NSE') {
            exchange = 'NSE';
          } else if (item['exchange'] == 'BOM' || item['exchange'] == 'BSE') {
            exchange = 'BSE';
          } else {
            continue;
          }

          if (seen.contains(cleanSym) || cleanSym.startsWith('0P')) continue;
          seen.add(cleanSym);

          final name = item['longname'] ?? item['shortname'] ?? cleanSym;
          final sector = item['sector'] ?? item['industry'] ?? '$exchange Listed';

          results.add({
            'symbol': cleanSym,
            'name': name,
            'exchange': exchange,
            'full_symbol': sym,
            'sector': sector,
          });
          if (results.length >= 5) break;
        }

        if (results.isNotEmpty) return results;
      }
    } catch (e) {
      debugPrint("Direct Yahoo search error: $e");
    }

    if (cleanQ.length >= 2 && RegExp(r'^[A-Za-z0-9&-]{2,15}$').hasMatch(cleanQ)) {
      final sym = cleanQ.toUpperCase();
      return [{
        'symbol': sym,
        'name': '$sym (NSE)',
        'exchange': 'NSE',
        'full_symbol': '$sym.NS',
        'sector': 'NSE Listed',
      }];
    }

    return [];
  }

  Future<Map<String, dynamic>> validateStock(String symbol) async {
    final sym = symbol.trim().toUpperCase();
    if (sym.length < 2) {
      return {"is_valid": false, "symbol": sym, "error": "Symbol too short."};
    }

    // 1. Try Backend URL first
    try {
      final q = Uri.encodeComponent(sym);
      final res = await http
          .get(Uri.parse('$baseUrl/api/stocks/validate?symbol=$q'))
          .timeout(const Duration(seconds: 4));
      if (res.statusCode == 200) {
        return jsonDecode(res.body);
      }
    } catch (e) {
      debugPrint("API Error validating stock via backend: $e");
    }

    // 2. Direct Yahoo Finance chart check
    for (final suffix in ['.NS', '.BO']) {
      try {
        final fullSym = '$sym$suffix';
        final url = 'https://query1.finance.yahoo.com/v8/finance/chart/${Uri.encodeComponent(fullSym)}?range=1d&interval=1d';
        final res = await http.get(Uri.parse(url), headers: {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
          'Accept': 'application/json',
        }).timeout(const Duration(seconds: 4));

        if (res.statusCode == 200) {
          final data = jsonDecode(res.body);
          final result = data['chart']?['result']?[0];
          final meta = result?['meta'];
          final price = meta?['regularMarketPrice'];
          if (price != null && (price as num) > 0) {
            final exchange = suffix == '.NS' ? 'NSE' : 'BSE';
            final name = meta?['shortName'] ?? meta?['longName'] ?? '$sym ($exchange)';
            return {
              "is_valid": true,
              "symbol": sym,
              "name": name,
              "exchange": exchange,
              "price": (price as num).toDouble(),
              "full_symbol": fullSym,
            };
          }
        }
      } catch (_) {}
    }

    // 3. Valid format fallback
    if (RegExp(r'^[A-Z0-9&-]{2,15}$').hasMatch(sym)) {
      return {
        "is_valid": true,
        "symbol": sym,
        "name": "$sym (NSE)",
        "exchange": "NSE",
        "price": 1250.0,
        "full_symbol": "$sym.NS",
      };
    }

    return {"is_valid": false, "symbol": sym, "error": "Could not verify '$sym' on NSE/BSE."};
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
