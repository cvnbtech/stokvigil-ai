import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import '../models/models.dart';
import 'supabase_service.dart';

class ApiService {
  static String get baseUrl {
    const configured = String.fromEnvironment(
      'BACKEND_URL',
      defaultValue: String.fromEnvironment(
        'STOKVIGIL_BACKEND_URL',
        defaultValue: '',
      ),
    );
    if (configured.isNotEmpty && !configured.contains('xxxx.a.run.app')) {
      return configured.replaceAll(RegExp(r'/+$'), '');
    }
    if (kDebugMode) {
      if (defaultTargetPlatform == TargetPlatform.android) {
        return 'http://10.0.2.2:8000';
      }
      return 'http://localhost:8000';
    }
    return configured.isNotEmpty ? configured.replaceAll(RegExp(r'/+$'), '') : 'http://localhost:8000';
  }

  Map<String, String> _getAuthHeaders() {
    String? token;
    try {
      if (SupabaseService.isConfigured) {
        token = SupabaseService().client.auth.currentSession?.accessToken;
      }
    } catch (_) {
      token = null;
    }
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
    if (query.trim().isEmpty) return [];
    try {
      final q = Uri.encodeComponent(query.trim());
      final res = await http
          .get(Uri.parse('$baseUrl/api/stocks/search?q=$q'))
          .timeout(const Duration(seconds: 4));
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        final list = (data['stocks'] as List?)?.map((e) => Map<String, dynamic>.from(e)).toList() ?? [];
        if (list.isNotEmpty) return list;
      }
    } catch (e) {
      debugPrint("API backend search fallback: $e");
    }
    return _searchDirectYahoo(query.trim());
  }

  Future<Map<String, dynamic>> validateStock(String symbol) async {
    final sym = symbol.trim().toUpperCase();
    if (sym.length < 2) {
      return {"is_valid": false, "symbol": sym, "error": "Symbol too short."};
    }
    try {
      final q = Uri.encodeComponent(sym);
      final res = await http
          .get(Uri.parse('$baseUrl/api/stocks/validate?symbol=$q'))
          .timeout(const Duration(seconds: 4));
      if (res.statusCode == 200) {
        return jsonDecode(res.body);
      }
    } on TimeoutException {
      debugPrint("API Timeout validating stock '$sym'");
    } catch (e) {
      debugPrint("API Error validating stock: $e");
    }
    return _validateDirectYahoo(sym);
  }

  Future<Map<String, dynamic>> fetchBatchQuotes(List<String> symbols) async {
    if (symbols.isEmpty) return {};
    final clean = symbols.map((s) => s.trim().toUpperCase()).where((s) => s.isNotEmpty).toSet().toList();
    if (clean.isEmpty) return {};

    final quotes = <String, dynamic>{};
    final missing = <String>[];

    // Tier 1: Fetch from backend (incorporates AI signals, targets & stop loss if available)
    try {
      final q = Uri.encodeComponent(clean.join(','));
      final res = await http
          .get(Uri.parse('$baseUrl/api/stocks/quotes?symbols=$q'))
          .timeout(const Duration(seconds: 5));
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        final bQuotes = Map<String, dynamic>.from(data['quotes'] ?? {});
        for (final sym in clean) {
          if (bQuotes.containsKey(sym) && bQuotes[sym] is Map && (bQuotes[sym]['price'] as num? ?? 0) > 0) {
            quotes[sym] = bQuotes[sym];
          } else {
            missing.add(sym);
          }
        }
      } else {
        missing.addAll(clean);
      }
    } catch (e) {
      debugPrint("API backend quotes fetch failed or offline: $e");
      missing.addAll(clean);
    }

    // Tier 2: Direct Yahoo Finance fallback for any still-missing symbols
    if (missing.isNotEmpty) {
      await Future.wait(missing.map((sym) async {
        final directQuote = await _fetchDirectYahooQuote(sym);
        if (directQuote != null) {
          quotes[sym] = directQuote;
        }
      }));
    }

    return quotes;
  }

  Future<Map<String, dynamic>?> _fetchDirectYahooQuote(String sym) async {
    final headers = {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
      'Referer': 'https://finance.yahoo.com/',
      'Accept': 'application/json, text/plain, */*',
    };

    for (final suffix in ['.NS', '.BO']) {
      final exch = suffix == '.NS' ? 'NSE' : 'BSE';
      for (final host in ['query1.finance.yahoo.com', 'query2.finance.yahoo.com']) {
        try {
          final url = Uri.parse('https://$host/v8/finance/chart/${Uri.encodeComponent(sym)}$suffix?range=1d&interval=1d');
          final res = await http.get(url, headers: headers).timeout(const Duration(seconds: 5));
          if (res.statusCode == 200) {
            final data = jsonDecode(res.body);
            final resList = data['chart']?['result'] as List?;
            if (resList != null && resList.isNotEmpty) {
              final meta = resList[0]['meta'] as Map<String, dynamic>?;
              final p = meta?['regularMarketPrice'];
              if (p != null && (p as num) > 0) {
                final price = (p as num).toDouble();
                final prev = (meta?['chartPreviousClose'] ?? meta?['previousClose'] ?? price) as num;
                final chgPct = prev > 0 ? (((price - prev.toDouble()) / prev.toDouble()) * 100) : 0.0;
                final name = (meta?['shortName'] ?? meta?['longName'] ?? '$sym ($exch)').toString();
                final dayHigh = meta?['regularMarketDayHigh'] != null ? (meta!['regularMarketDayHigh'] as num).toDouble() : null;
                final dayLow = meta?['regularMarketDayLow'] != null ? (meta!['regularMarketDayLow'] as num).toDouble() : null;

                return {
                  'symbol': sym,
                  'name': name,
                  'exchange': exch,
                  'price': double.parse(price.toStringAsFixed(2)),
                  'change_pct': double.parse(chgPct.toStringAsFixed(2)),
                  'is_positive': chgPct >= 0,
                  'day_high': dayHigh != null ? double.parse(dayHigh.toStringAsFixed(2)) : null,
                  'day_low': dayLow != null ? double.parse(dayLow.toStringAsFixed(2)) : null,
                  'target': null,
                  'stop_loss': null,
                  'signal': 'MONITORING',
                  'signal_type': 'monitoring',
                };
              }
            }
          }
        } catch (_) {
          // Try next host/suffix
        }
      }
    }
    return null;
  }

  Future<List<Map<String, dynamic>>> _searchDirectYahoo(String query) async {
    final searchHeaders = {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
      'Accept': 'application/json, text/plain, */*',
    };

    for (final host in ['query1.finance.yahoo.com', 'query2.finance.yahoo.com']) {
      try {
        final url = Uri.parse('https://$host/v1/finance/search?q=${Uri.encodeComponent(query)}&quotesCount=10&newsCount=0');
        final res = await http.get(url, headers: searchHeaders).timeout(const Duration(seconds: 5));
        if (res.statusCode == 200) {
          final data = jsonDecode(res.body);
          final rawQuotes = (data['quotes'] as List?) ?? [];
          final results = <Map<String, dynamic>>[];
          final seen = <String>{};

          for (final item in rawQuotes) {
            final sym = (item['symbol'] ?? '').toString();
            final quoteType = (item['quoteType'] ?? '').toString();
            if (quoteType != 'EQUITY') continue;

            String cleanSym = sym;
            String exchange = 'NSE';
            if (sym.endsWith('.NS')) {
              cleanSym = sym.substring(0, sym.length - 3);
              exchange = 'NSE';
            } else if (sym.endsWith('.BO')) {
              cleanSym = sym.substring(0, sym.length - 3);
              exchange = 'BSE';
            } else if (['NSI', 'NSE'].contains(item['exchange'])) {
              exchange = 'NSE';
            } else if (['BOM', 'BSE'].contains(item['exchange'])) {
              exchange = 'BSE';
            } else {
              continue;
            }

            if (seen.contains(cleanSym) || cleanSym.startsWith('0P')) continue;
            seen.add(cleanSym);

            final name = (item['longname'] ?? item['shortname'] ?? cleanSym).toString();
            final sector = (item['sector'] ?? item['industry'] ?? '$exchange Listed').toString();

            results.add({
              'symbol': cleanSym,
              'name': name,
              'exchange': exchange,
              'full_symbol': sym,
              'sector': sector,
            });

            if (results.length >= 8) break;
          }

          if (results.isNotEmpty) return results;
        }
      } catch (_) {}
    }
    return [];
  }

  Future<Map<String, dynamic>> _validateDirectYahoo(String sym) async {
    final quote = await _fetchDirectYahooQuote(sym);
    if (quote != null && quote['price'] != null && (quote['price'] as num) > 0) {
      return {
        'is_valid': true,
        'symbol': sym,
        'name': quote['name'],
        'exchange': quote['exchange'],
        'price': quote['price'],
        'full_symbol': '${quote['symbol']}.${quote['exchange'] == 'NSE' ? 'NS' : 'BO'}',
      };
    }
    return {
      'is_valid': false,
      'symbol': sym,
      'error': "Could not verify '$sym' on NSE/BSE. Please select from search suggestions.",
    };
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

  Future<Map<String, dynamic>?> fetchFiiDiiFlows() async {
    try {
      final res = await http
          .get(Uri.parse('$baseUrl/api/market/fii-dii-flows'))
          .timeout(const Duration(seconds: 15));
      if (res.statusCode == 200) {
        return jsonDecode(res.body);
      }
    } catch (e) {
      debugPrint("API Error fetching FII/DII flows: $e");
    }
    return null;
  }

  Future<Map<String, dynamic>?> fetchStockCandles({
    required String symbol,
    String interval = "5m",
    String period = "5d",
  }) async {
    final cleanSym = symbol.trim().toUpperCase();
    if (cleanSym.isEmpty) return null;
    try {
      final q = Uri.encodeComponent(cleanSym);
      final res = await http
          .get(
            Uri.parse('$baseUrl/api/stocks/candles?symbol=$q&interval=$interval&period=$period'),
            headers: _getAuthHeaders(),
          )
          .timeout(const Duration(seconds: 25));
      if (res.statusCode == 200) {
        return jsonDecode(res.body);
      } else {
        debugPrint("API Error fetching candles for $cleanSym (HTTP ${res.statusCode}): ${res.body}");
      }
    } catch (e) {
      debugPrint("API Error fetching stock candles for $cleanSym: $e");
    }
    return null;
  }

  Future<Map<String, dynamic>?> fetchAccuracyLedger() async {
    try {
      final res = await http
          .get(
            Uri.parse('$baseUrl/api/market/accuracy-ledger'),
            headers: _getAuthHeaders(),
          )
          .timeout(const Duration(seconds: 20));
      if (res.statusCode == 200) {
        return jsonDecode(res.body);
      } else {
        debugPrint("API Error fetching accuracy ledger (HTTP ${res.statusCode}): ${res.body}");
      }
    } catch (e) {
      debugPrint("API Error fetching accuracy ledger: $e");
    }
    return null;
  }
}

