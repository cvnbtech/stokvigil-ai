import 'dart:async';
import 'package:flutter/foundation.dart';
import '../services/api_service.dart';
import '../services/supabase_service.dart';

class WatchlistProvider extends ChangeNotifier {
  List<Map<String, dynamic>> _watchlist = [];
  bool _isLoading = true;
  bool _autoSync = false;
  String? _currentUserId;

  StreamSubscription<List<Map<String, dynamic>>>? _watchlistSub;
  Timer? _refreshTimer;

  List<Map<String, dynamic>> get watchlist => _watchlist;
  bool get isLoading => _isLoading;
  bool get autoSync => _autoSync;

  void initialize(String? userId) {
    if (_currentUserId == userId && _watchlistSub != null) {
      return;
    }
    _currentUserId = userId;
    _watchlistSub?.cancel();
    _refreshTimer?.cancel();

    if (userId == null || userId.isEmpty) {
      _watchlist = [];
      _isLoading = false;
      notifyListeners();
      return;
    }

    _loadInitialData(userId);
    _subscribeToWatchlist();

    // Periodic quote refresh every 30 seconds
    _refreshTimer = Timer.periodic(const Duration(seconds: 30), (_) {
      refreshQuotesOnly();
    });
  }

  void clear() {
    _watchlistSub?.cancel();
    _refreshTimer?.cancel();
    _watchlistSub = null;
    _refreshTimer = null;
    _currentUserId = null;
    _watchlist = [];
    _isLoading = false;
    notifyListeners();
  }

  Future<void> _loadInitialData(String userId) async {
    _isLoading = true;
    notifyListeners();

    try {
      final profile = await SupabaseService().fetchUserProfile();
      if (profile != null) {
        _autoSync = profile.dematAutoSync;
      }

      final items = await SupabaseService().fetchWatchlist();
      final updated = <Map<String, dynamic>>[];
      for (final item in items) {
        final sym = (item['symbol']?.toString() ?? '').toUpperCase();
        final cleanSym = sym.replaceAll(RegExp(r'\.(BO|NS)$'), '');
        final cached = ApiService.getCachedQuote(cleanSym) ?? ApiService.getCachedQuote(sym);
        final map = Map<String, dynamic>.from(item);
        if (cached != null && (cached['price'] as num? ?? 0) > 0) {
          _applyQuoteToItem(map, cached);
        }
        updated.add(map);
      }
      _watchlist = updated;
      _isLoading = false;
      notifyListeners();

      // Trigger background quotes refresh
      await refreshQuotesOnly();
    } catch (e) {
      debugPrint("Error loading initial watchlist in provider: $e");
      _isLoading = false;
      notifyListeners();
    }
  }

  void _subscribeToWatchlist() {
    _watchlistSub = SupabaseService().streamWatchlist().listen((liveData) {
      final updated = <Map<String, dynamic>>[];
      for (final item in liveData) {
        final sym = (item['symbol']?.toString() ?? '').toUpperCase();
        final cleanSym = sym.replaceAll(RegExp(r'\.(BO|NS)$'), '');

        final existing = _watchlist.firstWhere(
          (w) => (w['symbol']?.toString() ?? '').toUpperCase() == sym ||
                 (w['symbol']?.toString() ?? '').toUpperCase() == cleanSym,
          orElse: () => <String, dynamic>{},
        );
        final cached = ApiService.getCachedQuote(cleanSym) ?? ApiService.getCachedQuote(sym);

        final merged = Map<String, dynamic>.from(item);
        if (existing.isNotEmpty && (existing['price'] as num? ?? 0) > 0) {
          merged['price'] = existing['price'];
          merged['chg'] = existing['chg'];
          merged['is_positive'] = existing['is_positive'];
          merged['signal'] = existing['signal'];
          merged['target'] = existing['target'];
          merged['stop_loss'] = existing['stop_loss'];
          merged['trailing_sl'] = existing['trailing_sl'];
          merged['is_high_beta'] = existing['is_high_beta'];
          merged['volatility_regime'] = existing['volatility_regime'];
          merged['name'] = existing['name'] ?? merged['name'];
          merged['exchange'] = existing['exchange'] ?? merged['exchange'];
        } else if (cached != null && (cached['price'] as num? ?? 0) > 0) {
          _applyQuoteToItem(merged, cached);
        }
        updated.add(merged);
      }
      _watchlist = updated;
      _isLoading = false;
      notifyListeners();
    });
  }

  Future<void> refreshQuotesOnly() async {
    if (_watchlist.isEmpty) return;
    final symbols = _watchlist
        .map((item) => (item['symbol']?.toString() ?? '').toUpperCase())
        .where((s) => s.isNotEmpty)
        .toList();
    if (symbols.isEmpty) return;

    try {
      final liveQuotes = await ApiService().fetchBatchQuotes(symbols);
      for (var item in _watchlist) {
        final sym = (item['symbol']?.toString() ?? '').toUpperCase();
        final cleanSym = sym.replaceAll(RegExp(r'\.(BO|NS)$'), '');
        final q = liveQuotes[sym] ?? liveQuotes[cleanSym];
        if (q != null && q is Map<String, dynamic>) {
          _applyQuoteToItem(item, q);
        }
      }
      notifyListeners();
    } catch (e) {
      debugPrint("Error in WatchlistProvider.refreshQuotesOnly: $e");
    }
  }

  void _applyQuoteToItem(Map<String, dynamic> item, Map<String, dynamic> q) {
    final price = (q['price'] as num? ?? 0.0).toDouble();
    if (price <= 0) {
      item['price'] = 0.0;
      item['chg'] = '--';
      item['signal'] = null;
      item['target'] = null;
      item['stop_loss'] = null;
      item['trailing_sl'] = null;
      item['is_high_beta'] = false;
      return;
    }

    item['price'] = price;
    final num? chgVal = q['change_pct'] as num?;
    final isPos = chgVal != null ? (chgVal >= 0) : (q['is_positive'] == true);
    final chgPctStr = chgVal != null ? chgVal.toStringAsFixed(2) : '0.00';
    item['is_positive'] = isPos;
    item['chg'] = "${isPos ? '+' : ''}$chgPctStr%";
    if (q['name'] != null && q['name'].toString().isNotEmpty) {
      item['name'] = q['name'];
    }
    if (q['exchange'] != null && q['exchange'].toString().isNotEmpty) {
      item['exchange'] = q['exchange'];
    }

    // Zero-Default Policy: Filter out placeholder 'HOLD', 'MONITORING', etc.
    final rawSignal = q['signal']?.toString().trim();
    if (rawSignal != null && rawSignal.isNotEmpty && rawSignal != '--' && rawSignal != 'HOLD' && rawSignal != 'MONITORING') {
      item['signal'] = rawSignal;
    } else {
      item['signal'] = null;
    }

    final rawTarget = q['target']?.toString();
    if (rawTarget != null && rawTarget != '--' && rawTarget != '₹0' && rawTarget != '0' && rawTarget.isNotEmpty && item['signal'] != null) {
      if (rawTarget.contains('CUT') || rawTarget.contains('EXIT') || rawTarget.startsWith('₹')) {
        item['target'] = rawTarget;
      } else {
        item['target'] = "₹$rawTarget";
      }
    } else {
      item['target'] = null;
    }

    final rawSl = q['stop_loss']?.toString();
    if (rawSl != null && rawSl != '--' && rawSl != '₹0' && rawSl != '0' && rawSl.isNotEmpty && item['signal'] != null) {
      if (rawSl.contains('BREACHED') || rawSl.startsWith('₹')) {
        item['stop_loss'] = rawSl;
      } else {
        item['stop_loss'] = "₹$rawSl";
      }
    } else {
      item['stop_loss'] = null;
    }
    item['trailing_sl'] = item['signal'] != null ? q['trailing_sl'] : null;
    item['is_high_beta'] = q['is_high_beta'] == true;
    item['volatility_regime'] = q['volatility_regime'];
  }

  Future<bool> addStock(String symbol, {String? exchange, bool isAutoSynced = false}) async {
    final success = await SupabaseService().addToWatchlist(
      symbol,
      exchange: exchange,
      isAutoSynced: isAutoSynced,
    );
    if (success) {
      // Optimistic refresh
      await refreshQuotesOnly();
    }
    return success;
  }

  Future<bool> removeStock(dynamic id, [String? symbol]) async {
    final success = await SupabaseService().removeFromWatchlist(id, symbol);
    if (success) {
      _watchlist.removeWhere((item) => item['id'] == id || item['symbol'] == symbol);
      notifyListeners();
    }
    return success;
  }

  Future<void> toggleAutoSync(bool enabled) async {
    _autoSync = enabled;
    notifyListeners();
    await SupabaseService().updateProfile({'demat_auto_sync': enabled});
  }

  @override
  void dispose() {
    _watchlistSub?.cancel();
    _refreshTimer?.cancel();
    super.dispose();
  }
}
