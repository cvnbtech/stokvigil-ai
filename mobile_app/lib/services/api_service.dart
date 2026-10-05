import 'dart:async';
import 'dart:convert';
import 'dart:math' as math;
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import '../models/models.dart';
import 'supabase_service.dart';

class ApiService {
  // Static L1 In-Memory Cache for 0ms SWR (Stale-While-Revalidate) screen rendering
  static final Map<String, Map<String, dynamic>> _quotesCache = {};
  static final Map<String, DateTime> _quotesCacheTimestamps = {};

  static Map<String, dynamic>? getCachedQuote(String symbol) {
    final clean = symbol.trim().toUpperCase().replaceAll(RegExp(r'\.(BO|NS)$'), '');
    return _quotesCache[clean] ?? _quotesCache[symbol.trim().toUpperCase()];
  }

  static Map<String, Map<String, dynamic>> getAllCachedQuotes() {
    return Map.unmodifiable(_quotesCache);
  }

  static void setCachedQuote(String symbol, Map<String, dynamic> quote) {
    final clean = symbol.trim().toUpperCase().replaceAll(RegExp(r'\.(BO|NS)$'), '');
    _quotesCache[clean] = quote;
    _quotesCache[symbol.trim().toUpperCase()] = quote;
    _quotesCacheTimestamps[clean] = DateTime.now();
  }

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
    // Purely environment-driven: Return empty if not configured in environment (no dummy localhost)
    return '';
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
    required String sessionToken,
    String broker = 'icici',
  }) async {
    try {
      final res = await http.post(
        Uri.parse('$baseUrl/api/user/credentials'),
        headers: _getAuthHeaders(),
        body: jsonEncode({
          'user_id': userId,
          'session_token': sessionToken,
          'broker': broker,
        }),
      ).timeout(const Duration(seconds: 30));
      return res.statusCode == 200;
    } catch (e) {
      debugPrint("API Error saving credentials: $e");
      return false;
    }
  }

  Future<String?> fetchBrokerLoginUrl([String broker = 'icici']) async {
    try {
      final res = await http
          .get(
            Uri.parse('$baseUrl/api/broker/$broker/login-url'),
            headers: _getAuthHeaders(),
          )
          .timeout(const Duration(seconds: 15));
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        return data['login_url']?.toString();
      }
    } catch (e) {
      debugPrint("API Error fetching broker login URL: $e");
    }
    return null;
  }

  Future<List<Map<String, dynamic>>> fetchSupportedBrokers() async {
    try {
      final res = await http
          .get(
            Uri.parse('$baseUrl/api/brokers'),
            headers: _getAuthHeaders(),
          )
          .timeout(const Duration(seconds: 15));
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        if (data['brokers'] is List) {
          return List<Map<String, dynamic>>.from(data['brokers']);
        }
      }
    } catch (e) {
      debugPrint("API Error fetching brokers: $e");
    }
    return [];
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

    // Check L1 In-Memory SWR Cache first
    for (final sym in clean) {
      final cached = getCachedQuote(sym);
      if (cached != null && (cached['price'] as num? ?? 0) > 0) {
        quotes[sym] = cached;
      }
    }

    // Tier 1: Fetch from backend ONLY if backend URL is configured in the environment
    if (baseUrl.isNotEmpty) {
      try {
        final q = Uri.encodeComponent(clean.join(','));
        final res = await http
            .get(Uri.parse('$baseUrl/api/stocks/quotes?symbols=$q'))
            .timeout(const Duration(milliseconds: 2500));
        if (res.statusCode == 200) {
          final data = jsonDecode(res.body);
          final bQuotes = Map<String, dynamic>.from(data['quotes'] ?? {});
          for (final sym in clean) {
            if (bQuotes.containsKey(sym) && bQuotes[sym] is Map && (bQuotes[sym]['price'] as num? ?? 0) > 0) {
              final qData = Map<String, dynamic>.from(bQuotes[sym]);
              quotes[sym] = qData;
              setCachedQuote(sym, qData);
            } else if (!quotes.containsKey(sym)) {
              missing.add(sym);
            }
          }
        } else {
          for (final sym in clean) {
            if (!quotes.containsKey(sym)) missing.add(sym);
          }
        }
      } catch (e) {
        debugPrint("API backend quotes fetch skipped/failed ($e), falling back directly");
        for (final sym in clean) {
          if (!quotes.containsKey(sym)) missing.add(sym);
        }
      }
    } else {
      // Pure environment-driven: No backend URL configured, 0ms latency straight to Tier 2
      for (final sym in clean) {
        if (!quotes.containsKey(sym)) missing.add(sym);
      }
    }

    // Tier 2: Direct Yahoo Finance fallback for any still-missing symbols
    if (missing.isNotEmpty) {
      await Future.wait(missing.map((sym) async {
        final directQuote = await _fetchDirectYahooQuote(sym);
        if (directQuote != null) {
          quotes[sym] = directQuote;
          setCachedQuote(sym, directQuote);
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

    final cleanSym = sym.replaceAll(RegExp(r'\.(BO|NS)$'), '').trim();

    for (final suffix in ['.NS', '.BO']) {
      final exch = suffix == '.NS' ? 'NSE' : 'BSE';
      for (final host in ['query1.finance.yahoo.com', 'query2.finance.yahoo.com']) {
        try {
          final url = Uri.parse('https://$host/v8/finance/chart/${Uri.encodeComponent(cleanSym)}$suffix?range=5d&interval=1d');
          final res = await http.get(url, headers: headers).timeout(const Duration(milliseconds: 2500));
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
                final name = (meta?['shortName'] ?? meta?['longName'] ?? '$cleanSym ($exch)').toString();
                final dayHigh = meta?['regularMarketDayHigh'] != null ? (meta!['regularMarketDayHigh'] as num).toDouble() : null;
                final dayLow = meta?['regularMarketDayLow'] != null ? (meta!['regularMarketDayLow'] as num).toDouble() : null;

                // Extract completed prior-day (D-1) bar to guarantee static horizontal Camarilla pivots
                final quoteObj = resList[0]['indicators']?['quote']?[0] as Map<String, dynamic>?;
                final rawHighs = (quoteObj?['high'] as List?)?.whereType<num>().toList() ?? [];
                final rawLows = (quoteObj?['low'] as List?)?.whereType<num>().toList() ?? [];
                final rawCloses = (quoteObj?['close'] as List?)?.whereType<num>().toList() ?? [];

                double? hPrev;
                double? lPrev;
                double cPrev = prev.toDouble();

                if (rawHighs.length >= 2 && rawLows.length >= 2) {
                  hPrev = rawHighs[rawHighs.length - 2].toDouble();
                  lPrev = rawLows[rawLows.length - 2].toDouble();
                  if (rawCloses.length >= 2) {
                    cPrev = rawCloses[rawCloses.length - 2].toDouble();
                  }
                } else if (rawHighs.length == 1 && rawLows.length == 1) {
                  hPrev = rawHighs[0].toDouble();
                  lPrev = rawLows[0].toDouble();
                }

                // Calculate authentic Camarilla Equation Pivots anchored strictly to D-1 completed session
                final double refHigh = hPrev ?? (dayHigh ?? price);
                final double refLow = lPrev ?? (dayLow ?? price);
                final double trueRange = math.max(refHigh - refLow, math.max((refHigh - cPrev).abs(), (refLow - cPrev).abs()));
                final bool hasRealVol = trueRange > 0 && cPrev > 0 && price > 0;

                // Intraday Expansion Ratio (IER) & High-Beta Event Buffering
                final double intradayRange = (dayHigh != null && dayLow != null) ? math.max(0.0, dayHigh - dayLow) : 0.0;
                final double ier = trueRange > 0 ? (intradayRange / trueRange) : 0.0;
                final bool isHighBeta = ier >= 1.25;
                final double bufferMult = isHighBeta ? 0.25 : 0.10;
                final double atrBuffer = trueRange * bufferMult;

                final double h3 = cPrev + (trueRange * 1.1 / 4.0);
                final double h4 = cPrev + (trueRange * 1.1 / 2.0);
                final double l3 = cPrev - (trueRange * 1.1 / 4.0);
                final double l4 = cPrev - (trueRange * 1.1 / 2.0);

                final double bufferedH4 = h4 + atrBuffer;
                final double bufferedL4 = l4 - atrBuffer;

                String? targetStr;
                String? slStr;
                String? signalStr;
                String? signalTypeStr;

                if (hasRealVol && price > 0) {
                  if (price >= bufferedH4) {
                    signalStr = 'STRONG BUY';
                    signalTypeStr = 'strong_buy';
                    targetStr = '₹${(h4 + (trueRange * 0.5)).toStringAsFixed(2)}';
                    slStr = '₹${h3.toStringAsFixed(2)}';
                  } else if (price >= h3) {
                    signalStr = 'BUY';
                    signalTypeStr = 'buy';
                    targetStr = '₹${h4.toStringAsFixed(2)}';
                    slStr = '₹${l3.toStringAsFixed(2)}';
                  } else if (price <= bufferedL4 || price <= l4) {
                    signalStr = 'STOP LOSS EXIT';
                    signalTypeStr = 'danger';
                    targetStr = 'CUT RISK';
                    slStr = '₹${l4.toStringAsFixed(2)} BREACHED';
                  } else if (price <= l3) {
                    signalStr = 'SELL';
                    signalTypeStr = 'sell';
                    targetStr = '₹${l4.toStringAsFixed(2)}';
                    slStr = '₹${h3.toStringAsFixed(2)}';
                  }
                  // Zero-Default Policy: If price trades between L3 and H3 (neutral consolidation),
                  // do NOT invent fake signals ('HOLD', 'MONITORING', 'ACCUMULATE') or dummy targets/stops.
                  // signalStr, signalTypeStr, targetStr, slStr remain null (rendered as '--' on client UI).
                }

                // Dynamic Chandelier Trailing Stop (2.0x ATR for High Beta, 1.5x ATR for Standard)
                // Calculated strictly when real volume exists and an active trade setup is triggered
                final double trailMult = isHighBeta ? 2.0 : 1.5;
                final double peakVal = math.max(price, dayHigh ?? price);
                final double rawTrailSl = math.max(l3, peakVal - (trailMult * trueRange));
                final String? trailingSlStr = (hasRealVol && price > 0 && signalStr != null)
                    ? '₹${rawTrailSl.toStringAsFixed(2)}'
                    : null;

                return {
                  'symbol': cleanSym,
                  'name': name,
                  'exchange': exch,
                  'price': double.parse(price.toStringAsFixed(2)),
                  'change_pct': double.parse(chgPct.toStringAsFixed(2)),
                  'is_positive': chgPct >= 0,
                  'day_high': dayHigh != null ? double.parse(dayHigh.toStringAsFixed(2)) : null,
                  'day_low': dayLow != null ? double.parse(dayLow.toStringAsFixed(2)) : null,
                  'target': targetStr,
                  'stop_loss': slStr,
                  'trailing_sl': trailingSlStr,
                  'is_high_beta': isHighBeta,
                  'volatility_regime': isHighBeta ? 'HIGH_BETA_EVENT' : 'STANDARD_CAMARILLA',
                  'signal': signalStr,
                  'signal_type': signalTypeStr,
                  'disclaimer': 'Authentic mathematical Camarilla Equation pivots (H3/H4/L3/L4) from live market volatility.',
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

  Future<Map<String, dynamic>> placeTradeOrder({
    required String userId,
    required String symbol,
    required String action,
    required String orderType,
    required int quantity,
    required double price,
    String? idempotencyKey,
  }) async {
    final cleanSym = symbol.trim().toUpperCase();
    final key = idempotencyKey ?? '$userId-$cleanSym-${DateTime.now().millisecondsSinceEpoch}';
    try {
      final headers = _getAuthHeaders();
      headers['X-Idempotency-Key'] = key;

      final res = await http.post(
        Uri.parse('$baseUrl/api/v1/orders/place'),
        headers: headers,
        body: jsonEncode({
          'user_id': userId,
          'symbol': cleanSym,
          'action': action.toUpperCase(),
          'order_type': orderType.toUpperCase(),
          'quantity': quantity,
          'price': price,
          'idempotency_key': key,
        }),
      ).timeout(const Duration(seconds: 25));

      if (res.statusCode == 200) {
        return {'success': true, 'data': jsonDecode(res.body)};
      } else {
        String msg = 'Execution error';
        try {
          final errBody = jsonDecode(res.body);
          msg = errBody['detail'] ?? errBody['message'] ?? 'HTTP ${res.statusCode}';
        } catch (_) {
          msg = 'HTTP ${res.statusCode}';
        }
        return {'success': false, 'error': msg};
      }
    } catch (e) {
      debugPrint("API Error placing trade order for $cleanSym: $e");
      return {'success': false, 'error': e.toString()};
    }
  }

  Future<Map<String, dynamic>?> fetchStrategyBacktest({
    required String symbol,
    String period = '1y',
    String interval = '1d',
    String strategy = 'camarilla_breakout',
    double capital = 200000.0,
    double riskBudget = 2000.0,
  }) async {
    final cleanSym = symbol.trim().toUpperCase();
    try {
      final uri = Uri.parse('$baseUrl/api/market/backtest').replace(
        queryParameters: {
          'symbol': cleanSym,
          'period': period,
          'interval': interval,
          'strategy': strategy,
          'capital': capital.toString(),
          'risk_budget': riskBudget.toString(),
        },
      );
      final res = await http.get(uri, headers: _getAuthHeaders()).timeout(const Duration(seconds: 35));
      if (res.statusCode == 200) {
        return jsonDecode(res.body) as Map<String, dynamic>;
      } else {
        debugPrint("API Error fetching backtest for $cleanSym (HTTP ${res.statusCode}): ${res.body}");
        return null;
      }
    } catch (e) {
      debugPrint("API Error executing backtest for $cleanSym: $e");
      return null;
    }
  }
}

