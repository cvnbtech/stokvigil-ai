import 'dart:async';
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
      defaultValue: "https://stokvigil-ai.vercel.app",
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
      ).timeout(const Duration(seconds: 30));
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
          .timeout(const Duration(seconds: 30));
      if (res.statusCode == 200) {
        return jsonDecode(res.body);
      }
    } catch (e) {
      debugPrint("API Error fetching user credentials: $e");
    }
    return null;
  }

  Future<List<Map<String, dynamic>>> searchStocks(String query) async {
    final cleanQuery = query.trim();
    if (cleanQuery.isEmpty) return [];

    // 1. Try StokVigil API (Vercel Serverless / Cloud Run)
    try {
      final q = Uri.encodeComponent(cleanQuery);
      final res = await http
          .get(Uri.parse('$baseUrl/api/stocks/search?q=$q'))
          .timeout(const Duration(seconds: 10));
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        final list = (data['stocks'] as List?)?.map((e) => Map<String, dynamic>.from(e)).toList() ?? [];
        if (list.isNotEmpty) return list;
      }
    } catch (e) {
      debugPrint("Backend search unavailable, attempting direct exchange search: $e");
    }

    // 2. Direct Exchange Fallback (Zero-Auth Public Search)
    try {
      final q = Uri.encodeComponent(cleanQuery);
      final yRes = await http.get(
        Uri.parse('https://query1.finance.yahoo.com/v1/finance/search?q=$q&quotesCount=8&newsCount=0'),
        headers: {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
          'Accept': 'application/json, text/plain, */*',
        },
      ).timeout(const Duration(seconds: 8));

      if (yRes.statusCode == 200) {
        final data = jsonDecode(yRes.body);
        final quotes = (data['quotes'] as List? ?? []);
        final results = <Map<String, dynamic>>[];
        for (final item in quotes) {
          final rawSym = (item['symbol'] ?? '').toString();
          if (rawSym.endsWith('.NS') || rawSym.endsWith('.BO')) {
            final cleanSym = rawSym.replaceAll('.NS', '').replaceAll('.BO', '').toUpperCase();
            final name = (item['shortname'] ?? item['longname'] ?? cleanSym).toString();
            final exch = rawSym.endsWith('.NS') ? 'NSE' : 'BSE';
            final sector = (item['sector'] ?? item['industry'] ?? exch).toString();
            results.add({
              'symbol': cleanSym,
              'name': name,
              'exchange': exch,
              'sector': sector,
              'full_symbol': rawSym,
            });
          }
        }
        if (results.isNotEmpty) return results;
      }
    } catch (e) {
      debugPrint("Direct exchange search failed: $e");
    }

    return [];
  }

  Future<Map<String, dynamic>> validateStock(String symbol) async {
    final sym = symbol.trim().toUpperCase();
    if (sym.length < 2) {
      return {"is_valid": false, "symbol": sym, "error": "Symbol too short."};
    }

    // 1. Try StokVigil API (Vercel Serverless / Cloud Run)
    try {
      final q = Uri.encodeComponent(sym);
      final res = await http
          .get(Uri.parse('$baseUrl/api/stocks/validate?symbol=$q'))
          .timeout(const Duration(seconds: 10));
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        if (data['is_valid'] == true) {
          return data;
        }
      }
    } catch (e) {
      debugPrint("Backend unavailable, attempting direct exchange lookup for '$sym': $e");
    }

    // 2. Direct Exchange Validation Fallback (Zero-Auth Chart API for NSE and BSE)
    try {
      for (final suffix in ['.NS', '.BO']) {
        final exch = suffix == '.NS' ? 'NSE' : 'BSE';
        final yRes = await http.get(
          Uri.parse('https://query1.finance.yahoo.com/v8/finance/chart/$sym$suffix?range=1d&interval=1d'),
          headers: {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
          },
        ).timeout(const Duration(seconds: 8));

        if (yRes.statusCode == 200) {
          final data = jsonDecode(yRes.body);
          final resList = data['chart']?['result'] as List?;
          if (resList != null && resList.isNotEmpty) {
            final meta = resList[0]['meta'] as Map<String, dynamic>? ?? {};
            final price = meta['regularMarketPrice'];
            if (price != null && (price as num) > 0) {
              final name = meta['shortName'] ?? meta['longName'] ?? '$sym ($exch)';
              return {
                'is_valid': true,
                'symbol': sym,
                'name': name,
                'exchange': exch,
                'price': (price as num).toDouble(),
                'full_symbol': '$sym$suffix'
              };
            }
          }
        }
      }
    } catch (e) {
      debugPrint("Direct exchange validation failed for '$sym': $e");
    }

    return {"is_valid": false, "symbol": sym, "error": "Could not verify '$sym' on NSE/BSE."};
  }

  Future<Map<String, dynamic>> fetchBatchQuotes(List<String> symbols) async {
    if (symbols.isEmpty) return {};
    final clean = symbols.map((s) => s.trim().toUpperCase()).where((s) => s.isNotEmpty).toSet().toList();

    // 1. Try StokVigil API (Vercel Serverless / Cloud Run)
    try {
      final q = Uri.encodeComponent(clean.join(','));
      final res = await http
          .get(Uri.parse('$baseUrl/api/stocks/quotes?symbols=$q'))
          .timeout(const Duration(seconds: 15));
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        final quotes = Map<String, dynamic>.from(data['quotes'] ?? {});
        if (quotes.isNotEmpty) return quotes;
      }
    } catch (e) {
      debugPrint("Backend batch quotes unavailable, attempting direct exchange lookup: $e");
    }

    // 2. Direct Exchange Batch Fallback
    final results = <String, dynamic>{};
    await Future.wait(clean.map((sym) async {
      try {
        for (final suffix in ['.NS', '.BO']) {
          final exch = suffix == '.NS' ? 'NSE' : 'BSE';
          final yRes = await http.get(
            Uri.parse('https://query1.finance.yahoo.com/v8/finance/chart/$sym$suffix?range=1d&interval=1d'),
            headers: {
              'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            },
          ).timeout(const Duration(seconds: 8));

          if (yRes.statusCode == 200) {
            final data = jsonDecode(yRes.body);
            final resList = data['chart']?['result'] as List?;
            if (resList != null && resList.isNotEmpty) {
              final meta = resList[0]['meta'] as Map<String, dynamic>? ?? {};
              final p = meta['regularMarketPrice'];
              if (p != null && (p as num) > 0) {
                final price = (p as num).toDouble();
                final prev = (meta['chartPreviousClose'] ?? meta['previousClose'] ?? price) as num;
                final chgPct = prev > 0 ? double.parse((((price - prev) / prev) * 100).toStringAsFixed(2)) : 0.0;
                final name = meta['shortName'] ?? meta['longName'] ?? '$sym ($exch)';
                results[sym] = {
                  'symbol': sym,
                  'name': name,
                  'exchange': exch,
                  'price': price,
                  'change_pct': chgPct,
                  'is_positive': chgPct >= 0,
                  'signal': chgPct >= 1.5 ? 'STRONG BUY' : (chgPct >= 0 ? 'BUY' : (chgPct > -1.5 ? 'HOLD' : 'SELL')),
                  'target': price > 0 ? double.parse((price * 1.12).toStringAsFixed(2)) : 0.0,
                  'stop_loss': price > 0 ? double.parse((price * 0.94).toStringAsFixed(2)) : 0.0,
                };
                break;
              }
            }
          }
        }
      } catch (_) {}
    }));

    return results;
  }

  Future<bool> deleteUserAccount(String userId) async {
    try {
      final res = await http.post(
        Uri.parse('$baseUrl/api/user/delete-account'),
        headers: _getAuthHeaders(),
        body: jsonEncode({'user_id': userId}),
      ).timeout(const Duration(seconds: 30));
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
          .timeout(const Duration(seconds: 30));
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
          .timeout(const Duration(seconds: 30));
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
      ).timeout(const Duration(seconds: 30));
      return res.statusCode == 200;
    } catch (e) {
      debugPrint("API Error registering device token via HTTP: $e");
      return profileUpdates.isNotEmpty;
    }
  }
}
