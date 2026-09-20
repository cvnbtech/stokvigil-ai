import 'dart:async';
import 'package:flutter/material.dart';
import '../config/theme.dart';
import '../services/api_service.dart';
import '../services/supabase_service.dart';
import '../utils/error_handler.dart';
import '../widgets/custom_widgets.dart';
import '../widgets/candle_chart_modal.dart';
import 'candle_chart_screen.dart';

class WatchlistScreen extends StatefulWidget {
  const WatchlistScreen({super.key});

  @override
  State<WatchlistScreen> createState() => _WatchlistScreenState();
}

class _WatchlistScreenState extends State<WatchlistScreen> {
  final _searchController = TextEditingController();
  List<Map<String, dynamic>> _watchlist = [];
  List<Map<String, dynamic>> _suggestions = [];
  bool _isLoading = true;
  bool _autoSync = false;
  StreamSubscription<List<Map<String, dynamic>>>? _watchlistSub;
  Timer? _searchDebounce;

  @override
  void initState() {
    super.initState();
    _searchController.addListener(_onSearchChanged);
    _loadWatchlist();
    _subscribeToWatchlist();
  }

  void _onSearchChanged() {
    final query = _searchController.text.trim();
    if (query.isEmpty) {
      _searchDebounce?.cancel();
      if (_suggestions.isNotEmpty) {
        setState(() => _suggestions = []);
      }
      return;
    }

    _searchDebounce?.cancel();
    _searchDebounce = Timer(const Duration(milliseconds: 300), () async {
      final results = await ApiService().searchStocks(query);
      if (mounted && _searchController.text.trim().isNotEmpty) {
        setState(() {
          _suggestions = results.map((r) => {
            'symbol': r['symbol']?.toString() ?? '',
            'name': r['name']?.toString() ?? '',
            'sector': r['sector']?.toString() ?? (r['exchange'] ?? 'NSE'),
            'exchange': r['exchange']?.toString() ?? 'NSE',
          }).toList();
        });
      }
    });
  }

  @override
  void dispose() {
    _searchDebounce?.cancel();
    _searchController.removeListener(_onSearchChanged);
    _watchlistSub?.cancel();
    _searchController.dispose();
    super.dispose();
  }

  void _subscribeToWatchlist() {
    _watchlistSub = SupabaseService().streamWatchlist().listen((liveData) {
      if (mounted) {
        setState(() {
          _watchlist = liveData;
          _isLoading = false;
        });
      }
    });
  }

  List<Map<String, dynamic>> _dematHoldings = [];

  Future<void> _loadWatchlist() async {
    final user = SupabaseService().currentUser;
    if (user == null) {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
      return;
    }

    setState(() => _isLoading = true);
    try {
      final profile = await SupabaseService().fetchUserProfile();
      if (profile != null) {
        _autoSync = profile.dematAutoSync;
      }
    } catch (_) {}

    // Step 1: Instantly load cached/persisted watchlist from Supabase (< 100ms)
    final data = await SupabaseService().fetchWatchlist();
    if (mounted) {
      setState(() {
        _watchlist = data;
        _isLoading = false; // Screen is immediately interactive and visible!
      });
    }

    // Step 2: Fetch real-time live quotes in background and update smoothly
    final symbols = data
        .map((item) => (item['symbol']?.toString() ?? '').toUpperCase())
        .where((s) => s.isNotEmpty)
        .toList();
    if (symbols.isNotEmpty) {
      try {
        final liveQuotes = await ApiService().fetchBatchQuotes(symbols);
        for (var item in data) {
          final sym = (item['symbol']?.toString() ?? '').toUpperCase();
          if (liveQuotes.containsKey(sym)) {
            final q = liveQuotes[sym] as Map<String, dynamic>;
            final price = (q['price'] as num? ?? 0.0).toDouble();
            item['price'] = price;
            final num? chgVal = q['change_pct'] as num?;
            final isPos = chgVal != null ? (chgVal >= 0) : (q['is_positive'] == true);
            final chgPctStr = chgVal != null ? chgVal.toStringAsFixed(2) : '0.00';
            item['is_positive'] = isPos;
            item['chg'] = price > 0 ? "${isPos ? '+' : ''}$chgPctStr%" : "--";
            if (q['name'] != null && q['name'].toString().isNotEmpty) {
              item['name'] = q['name'];
            }
            if (q['exchange'] != null && q['exchange'].toString().isNotEmpty) {
              item['exchange'] = q['exchange'];
            }
            item['signal'] = q['signal'];
            item['target'] = (q['target'] != null && q['target'] != '--' && q['target'] != '₹0') ? (q['target'].toString().startsWith('₹') ? q['target'] : "₹${q['target']}") : null;
            item['stop_loss'] = (q['stop_loss'] != null && q['stop_loss'] != '--' && q['stop_loss'] != '₹0') ? (q['stop_loss'].toString().startsWith('₹') ? q['stop_loss'] : "₹${q['stop_loss']}") : null;
          }
        }
        if (mounted) {
          setState(() {
            _watchlist = List.from(data);
          });
        }
      } catch (e) {
        debugPrint("Error fetching live quotes for watchlist: $e");
      }
    }

    // Step 3: Run Demat portfolio sync in background without blocking UI
    if (_autoSync) {
      _syncDematHoldings(user.id);
    }
  }

  Future<void> _syncDematHoldings(String userId) async {
    try {
      final portfolioData = await ApiService().fetchPortfolioSummary(userId);
      if (portfolioData != null && portfolioData['holdings'] is List) {
        final list = portfolioData['holdings'] as List;
        final demat = list.map((h) {
          final rawSym = (h['symbol'] ?? '').toString().toUpperCase();
          final cleanSym = (h['clean_symbol'] ?? rawSym.replaceAll('.BO', '').replaceAll('.NS', '')).toString().toUpperCase();
          final companyName = (h['name'] ?? h['stock_name'] ?? cleanSym).toString();
          final exchange = (h['exchange'] ?? (rawSym.endsWith('.BO') ? 'BSE' : 'NSE')).toString();
          final pnlPct = (h['pnl_percent'] as num? ?? 0).toDouble();
          final pnl = (h['pnl'] as num? ?? 0).toDouble();
          final price = (h['current_price'] as num? ?? 0.0).toDouble();
          final hasDematPrice = price > 0;
          return {
            'symbol': cleanSym,
            'full_symbol': rawSym,
            'exchange': exchange,
            'name': companyName,
            'price': price,
            'chg': (hasDematPrice && pnlPct != 0) ? (pnlPct >= 0 ? '+${pnlPct.toStringAsFixed(2)}%' : '${pnlPct.toStringAsFixed(2)}%') : '--',
            'is_positive': pnlPct >= 0,
            'is_auto_synced': true,
            'signal': (hasDematPrice && h['signal'] != null && h['signal'] != '--') ? h['signal'].toString() : '--',
            'target': (hasDematPrice && h['target'] != null) ? h['target'].toString() : '--',
            'stop_loss': (hasDematPrice && h['stop_loss'] != null) ? h['stop_loss'].toString() : '--',
          };
        }).toList();

        final symbolsToSync = demat
            .map((dh) => (dh['symbol'] as String? ?? '').trim())
            .where((s) => s.isNotEmpty)
            .toList();
        if (symbolsToSync.isNotEmpty) {
          SupabaseService().batchAddToWatchlist(symbolsToSync, isAutoSynced: true);
        }

        if (mounted) {
          setState(() {
            _dematHoldings = demat;
          });
        }
      }
    } catch (e) {
      debugPrint("Error in background demat sync: $e");
    }
  }

  Future<void> _toggleAutoSync(bool val) async {
    setState(() => _autoSync = val);
    final user = SupabaseService().currentUser;
    if (user != null) {
      await SupabaseService().updateProfile({'demat_auto_sync': val});
      ApiService().registerDeviceToken(
        userId: user.id,
        fcmToken: null,
        alertSensitivity: null,
        executionMode: null,
      );
    }
    if (val) {
      _loadWatchlist();
    }
  }

  Future<void> _addSymbol(String symbol, [String? displayName]) async {
    final sym = symbol.trim().toUpperCase();
    if (sym.isEmpty) {
      ErrorHandler.showErrorSnackBar(context, "Please enter an NSE/BSE stock symbol.");
      return;
    }

    // Real-time dynamic validation against exchange quote
    final validation = await ApiService().validateStock(sym);
    if (validation['is_valid'] != true) {
      if (mounted) {
        if (validation['is_timeout'] == true) {
          ErrorHandler.showErrorSnackBar(
            context,
            "⏳ Connection to exchange timed out for '$sym'. Please try again.",
          );
        } else {
          ErrorHandler.showErrorSnackBar(
            context,
            "⚠️ '$sym' is not a recognized or traded stock on NSE or BSE.",
          );
        }
      }
      return;
    }

    final exchange = validation['exchange'] ?? 'NSE';
    final name = displayName ?? validation['name'] ?? "$sym ($exchange)";
    final livePrice = validation['price'] != null ? (validation['price'] as num).toDouble() : 0.0;

    // Clear suggestions immediately
    setState(() => _suggestions = []);
    _searchController.clear();

    final user = SupabaseService().currentUser;
    if (user != null) {
      final ok = await SupabaseService().addToWatchlist(sym);
      if (ok) {
        if (mounted) {
          ErrorHandler.showSuccessSnackBar(context, "✅ $sym ($name) added to watchlist!");
        }
      } else {
        if (mounted) {
          ErrorHandler.showErrorSnackBar(context, "Failed to add $sym to watchlist.");
        }
      }
    } else {
      setState(() {
        if (!_watchlist.any((item) => item['symbol']?.toString().toUpperCase() == sym)) {
          _watchlist.insert(0, {
            'symbol': sym,
            'is_auto_synced': false,
            'name': name,
            'price': livePrice,
            'is_positive': true,
            'chg': livePrice > 0 ? "+0.00%" : "--",
            'signal': '--',
            'target': '--',
            'stop_loss': '--'
          });
        }
      });
      if (mounted) {
        ErrorHandler.showSuccessSnackBar(context, "✅ $sym added to watchlist!");
      }
    }
    _loadWatchlist();
  }

  Future<void> _removeSymbol(String symbol, [dynamic id]) async {
    final user = SupabaseService().currentUser;
    if (user == null) {
      setState(() {
        _watchlist.removeWhere((item) => item['symbol']?.toString().toUpperCase() == symbol.toUpperCase());
      });
      ErrorHandler.showSuccessSnackBar(context, "Removed $symbol from local watchlist.");
      return;
    }

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF0F172A),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: Text("Remove $symbol?", style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
        content: Text("Are you sure you want to stop tracking $symbol?", style: const TextStyle(color: AppTheme.textSecondary)),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text("Cancel", style: TextStyle(color: AppTheme.textMuted)),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppTheme.dangerRose,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
            ),
            child: const Text("Remove", style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      final ok = await SupabaseService().removeFromWatchlist(id, symbol);
      if (ok) {
        setState(() {
          _watchlist.removeWhere((item) => item['symbol']?.toString().toUpperCase() == symbol.toUpperCase());
        });
        if (mounted) {
          ErrorHandler.showSuccessSnackBar(context, "🗑️ Removed $symbol from watchlist.");
        }
      } else {
        ErrorHandler.showErrorSnackBar(context, "Failed to remove $symbol from database.");
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final combinedList = List<Map<String, dynamic>>.from(_watchlist);
    if (_autoSync) {
      for (final dh in _dematHoldings) {
        final sym = (dh['symbol'] ?? '').toString().toUpperCase();
        if (!combinedList.any((item) => (item['symbol'] ?? '').toString().toUpperCase() == sym)) {
          combinedList.add(dh);
        }
      }
    }

    final displayedList = _autoSync
        ? combinedList
        : combinedList.where((item) {
            final symbol = (item['symbol'] as String? ?? '').toUpperCase();
            final isAuto = item['is_auto_synced'] == true;
            return !isAuto;
          }).toList();

    return Scaffold(
      backgroundColor: AppTheme.darkBackground,
      appBar: AppBar(
        backgroundColor: AppTheme.darkBackground,
        elevation: 0,
        title: const StokVigilBrandHeader(),
      ),
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // ─────────────────────────────────────────────
          // WATCHLIST SECTION HEADER
          // ─────────────────────────────────────────────
          Padding(
            padding: const EdgeInsets.fromLTRB(16.0, 12.0, 16.0, 4.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Text(
                      "Watchlist",
                      style: TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 20),
                    ),
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: AppTheme.cyan.withOpacity(0.12),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: AppTheme.borderCyan),
                      ),
                      child: Text(
                        "${_watchlist.length} Stocks",
                        style: const TextStyle(color: AppTheme.cyan, fontSize: 11, fontWeight: FontWeight.w900),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 2),
                const Text(
                  "Real-time market feed • Auto-synced with ICICI Demat",
                  style: TextStyle(color: AppTheme.textSecondary, fontSize: 11, fontWeight: FontWeight.w500),
                ),
              ],
            ),
          ),

          // ─────────────────────────────────────────────
          // ADD STOCK SEARCH BAR
          // ─────────────────────────────────────────────
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 10.0),
            child: Row(
              children: [
                Expanded(
                  child: Container(
                    decoration: BoxDecoration(
                      color: AppTheme.cardBackground,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: AppTheme.borderCyan),
                    ),
                    child: TextField(
                      controller: _searchController,
                      style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 12),
                      textCapitalization: TextCapitalization.characters,
                      decoration: const InputDecoration(
                        hintText: "SEARCH NSE/BSE SYMBOL OR SECURITY CODE",
                        hintStyle: TextStyle(color: AppTheme.textMuted, fontSize: 11, fontWeight: FontWeight.bold),
                        border: InputBorder.none,
                        contentPadding: EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                        prefixIcon: Icon(Icons.search, color: AppTheme.cyan, size: 18),
                      ),
                      onSubmitted: _addSymbol,
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                GestureDetector(
                  onTap: () => _addSymbol(_searchController.text),
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                    decoration: BoxDecoration(
                      gradient: AppTheme.logoGradient,
                      borderRadius: BorderRadius.circular(12),
                      boxShadow: const [
                        BoxShadow(color: Color(0x4D06B6D4), blurRadius: 10, offset: Offset(0, 4)),
                      ],
                    ),
                    child: Row(
                      children: const [
                        Icon(Icons.add, color: Colors.white, size: 16),
                        SizedBox(width: 4),
                        Text(
                          "Add Stock",
                          style: TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 12),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),

          // ─────────────────────────────────────────────
          // SEARCH SUGGESTIONS DROPDOWN (UP TO 3 OPTIONS)
          // ─────────────────────────────────────────────
          if (_suggestions.isNotEmpty)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16.0),
              child: Container(
                margin: const EdgeInsets.only(bottom: 12),
                decoration: BoxDecoration(
                  color: const Color(0xFF0D111E),
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: AppTheme.borderCyan.withOpacity(0.6)),
                  boxShadow: [
                    BoxShadow(
                      color: AppTheme.cyan.withOpacity(0.15),
                      blurRadius: 16,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Padding(
                      padding: const EdgeInsets.fromLTRB(14, 10, 14, 6),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text(
                            "SUGGESTED NSE/BSE STOCKS (TAP TO ADD)",
                            style: TextStyle(
                              color: AppTheme.cyan,
                              fontSize: 10,
                              fontWeight: FontWeight.w900,
                              letterSpacing: 0.8,
                            ),
                          ),
                          GestureDetector(
                            onTap: () => setState(() => _suggestions = []),
                            child: const Icon(Icons.close, size: 14, color: AppTheme.textMuted),
                          ),
                        ],
                      ),
                    ),
                    const Divider(color: Color(0x33334155), height: 1),
                    ..._suggestions.map((item) {
                      final sym = item['symbol'] ?? '';
                      final name = item['name'] ?? '';
                      final sector = item['sector'] ?? 'NSE';
                      return InkWell(
                        onTap: () => _addSymbol(sym),
                        borderRadius: BorderRadius.circular(10),
                        child: Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
                          child: Row(
                            children: [
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
                                decoration: BoxDecoration(
                                  color: AppTheme.cyan.withOpacity(0.12),
                                  borderRadius: BorderRadius.circular(6),
                                  border: Border.all(color: AppTheme.borderCyan),
                                ),
                                child: Text(
                                  sym,
                                  style: const TextStyle(
                                    color: Colors.white,
                                    fontWeight: FontWeight.w900,
                                    fontSize: 12,
                                  ),
                                ),
                              ),
                              const SizedBox(width: 10),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      name,
                                      style: const TextStyle(
                                        color: Colors.white,
                                        fontWeight: FontWeight.w700,
                                        fontSize: 12,
                                      ),
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                    Text(
                                      sector,
                                      style: const TextStyle(
                                        color: AppTheme.textSecondary,
                                        fontSize: 10.5,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                decoration: BoxDecoration(
                                  gradient: AppTheme.logoGradient,
                                  borderRadius: BorderRadius.circular(8),
                                ),
                                child: const Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Icon(Icons.add, color: Colors.white, size: 12),
                                    SizedBox(width: 2),
                                    Text(
                                      "Add",
                                      style: TextStyle(
                                        color: Colors.white,
                                        fontWeight: FontWeight.w800,
                                        fontSize: 11,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                        ),
                      );
                    }).toList(),
                  ],
                ),
              ),
            ),

          // ─────────────────────────────────────────────
          // DEMAT AUTO-SYNC WATCHLIST CARD
          // ─────────────────────────────────────────────
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 2.0),
            child: GlassCard(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      const Text("📊", style: TextStyle(fontSize: 20)),
                      const SizedBox(width: 12),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: const [
                          Text(
                            "Demat Auto-Sync Watchlist",
                            style: TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 13),
                          ),
                          SizedBox(height: 2),
                          Text(
                            "Automatically import & monitor active demat stocks",
                            style: TextStyle(color: AppTheme.textSecondary, fontSize: 11),
                          ),
                        ],
                      ),
                    ],
                  ),
                  Switch(
                    value: _autoSync,
                    activeColor: AppTheme.cyan,
                    onChanged: _toggleAutoSync,
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 10),

          // ─────────────────────────────────────────────
          // WATCHLIST CARDS LIST
          // ─────────────────────────────────────────────
          Expanded(
            child: _isLoading
                    ? const Center(child: CircularProgressIndicator(color: AppTheme.cyan))
                    : displayedList.isEmpty
                        ? Center(
                            child: Padding(
                              padding: const EdgeInsets.all(32.0),
                              child: Column(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: const [
                                  Icon(Icons.format_list_bulleted_rounded, color: AppTheme.textSecondary, size: 56),
                                  SizedBox(height: 16),
                                  Text(
                                    "No Stocks in Watchlist",
                                    style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
                                  ),
                                  SizedBox(height: 8),
                                  Text(
                                    "Add NSE/BSE stock symbols or security codes above to monitor breakouts, earnings, and block deals.",
                                    textAlign: TextAlign.center,
                                    style: TextStyle(color: AppTheme.textSecondary, fontSize: 12),
                                  ),
                                ],
                              ),
                            ),
                          )
                        : ListView.builder(
                            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                            itemCount: displayedList.length + 1,
                            itemBuilder: (context, index) {
                              if (index == displayedList.length) {
                                return Padding(
                                  padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 16),
                                  child: Row(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Icon(Icons.info_outline, size: 13, color: AppTheme.textSecondary.withOpacity(0.6)),
                                      const SizedBox(width: 6),
                                      Expanded(
                                        child: Text(
                                          "All targets & stop-losses are algorithmic volatility benchmarks (1.5x ATR / Camarilla Pivots) for surveillance. Not an investment advisory or price guarantee.",
                                          style: TextStyle(
                                            fontSize: 10,
                                            color: AppTheme.textSecondary.withOpacity(0.6),
                                            height: 1.3,
                                          ),
                                        ),
                                      ),
                                    ],
                                  ),
                                );
                              }
                              final item = displayedList[index];
                          final rawSymbol = (item['symbol'] as String? ?? '').toUpperCase();
                          final symbol = rawSymbol.replaceAll('.BO', '').replaceAll('.NS', '').trim();
                          final exchange = (item['exchange'] as String?) ?? (rawSymbol.endsWith('.BO') ? 'BSE' : 'NSE');
                          final isAuto = item['is_auto_synced'] == true;
                          final priceNum = (item['price'] as num? ?? 0.0).toDouble();
                          final hasRealPrice = priceNum > 0;
                          final chg = hasRealPrice ? (item['chg']?.toString() ?? "+0.00%") : "--";
                          final isNegative = chg.startsWith('-') || item['is_positive'] == false;
                          final isPos = !isNegative && (item['is_positive'] == true);
                          final rawSignal = item['signal']?.toString();
                          final signal = (hasRealPrice && rawSignal != null && rawSignal != '--' && rawSignal != 'MONITORING') ? rawSignal : (hasRealPrice ? (rawSignal ?? '--') : '--');
                          final rawTarget = item['target']?.toString();
                          final target = (hasRealPrice && rawTarget != null && rawTarget != '--' && rawTarget != '₹0' && rawTarget != '0') ? rawTarget : '--';
                          final rawSl = item['stop_loss']?.toString();
                          final stopLoss = (hasRealPrice && rawSl != null && rawSl != '--' && rawSl != '₹0' && rawSl != '0') ? rawSl : '--';
                          final rawName = (item['name'] as String? ?? '').trim();
                          final name = (rawName.isNotEmpty && !rawName.contains('(Demat Holding)')) ? rawName : symbol;
                          final initial = symbol.length >= 2 ? symbol.substring(0, 2) : (symbol.isNotEmpty ? symbol : 'ST');

                          Color signalColor = const Color(0xFF94A3B8);
                          if (signal == 'STRONG BUY') {
                            signalColor = AppTheme.primaryEmerald;
                          } else if (signal == 'BUY') {
                            signalColor = const Color(0xFF06B6D4);
                          } else if (signal == 'ACCUMULATE') {
                            signalColor = const Color(0xFF0EA5E9);
                          } else if (signal == 'TAKE PROFIT') {
                            signalColor = const Color(0xFFF59E0B);
                          } else if (signal == 'SELL' || signal == 'EXIT') {
                            signalColor = AppTheme.dangerRose;
                          } else if (signal == 'HOLD' || signal == 'NEUTRAL') {
                            signalColor = const Color(0xFFEAB308);
                          } else {
                            signalColor = const Color(0xFF94A3B8);
                          }

                          return GlassCard(
                            margin: const EdgeInsets.only(bottom: 12),
                            child: Column(
                              children: [
                                // TOP ROW: Stock symbol, badge, price, change
                                Row(
                                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                  crossAxisAlignment: CrossAxisAlignment.center,
                                  children: [
                                    Expanded(
                                      child: Row(
                                        children: [
                                          // Avatar Symbol Initial Box
                                          Container(
                                            width: 38,
                                            height: 38,
                                            decoration: BoxDecoration(
                                              color: isPos ? AppTheme.primaryEmerald.withOpacity(0.12) : AppTheme.dangerRose.withOpacity(0.12),
                                              borderRadius: BorderRadius.circular(10),
                                              border: Border.all(
                                                color: isPos ? AppTheme.primaryEmerald.withOpacity(0.35) : AppTheme.dangerRose.withOpacity(0.35),
                                              ),
                                            ),
                                            child: Center(
                                              child: Text(
                                                initial,
                                                style: TextStyle(
                                                  color: isPos ? AppTheme.primaryEmerald : AppTheme.dangerRose,
                                                  fontWeight: FontWeight.w900,
                                                  fontSize: 12,
                                                ),
                                              ),
                                            ),
                                          ),
                                          const SizedBox(width: 10),
                                          Flexible(
                                            child: Column(
                                              crossAxisAlignment: CrossAxisAlignment.start,
                                              children: [
                                                Row(
                                                  mainAxisSize: MainAxisSize.min,
                                                  children: [
                                                    Flexible(
                                                      child: Text(
                                                        symbol,
                                                        overflow: TextOverflow.ellipsis,
                                                        style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 15),
                                                      ),
                                                    ),
                                                    const SizedBox(width: 6),
                                                    Container(
                                                      padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1.5),
                                                      decoration: BoxDecoration(
                                                        color: exchange == 'BSE' ? const Color(0xFFF59E0B).withOpacity(0.15) : AppTheme.cyan.withOpacity(0.12),
                                                        borderRadius: BorderRadius.circular(4),
                                                        border: Border.all(color: exchange == 'BSE' ? const Color(0xFFF59E0B) : AppTheme.cyan, width: 0.8),
                                                      ),
                                                      child: Text(
                                                        exchange,
                                                        style: TextStyle(
                                                          color: exchange == 'BSE' ? const Color(0xFFF59E0B) : AppTheme.cyan,
                                                          fontSize: 8.5,
                                                          fontWeight: FontWeight.w900,
                                                        ),
                                                      ),
                                                    ),
                                                    const SizedBox(width: 4),
                                                    Container(
                                                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                                      decoration: BoxDecoration(
                                                        color: isAuto ? AppTheme.cyan.withOpacity(0.1) : Colors.white.withOpacity(0.05),
                                                        borderRadius: BorderRadius.circular(4),
                                                        border: Border.all(color: isAuto ? AppTheme.cyan.withOpacity(0.3) : AppTheme.cardBorder),
                                                      ),
                                                      child: Text(
                                                        isAuto ? "📊 Demat Auto-Sync" : "📌 Custom",
                                                        style: TextStyle(
                                                          color: isAuto ? AppTheme.cyan : AppTheme.textMuted,
                                                          fontSize: 9,
                                                          fontWeight: FontWeight.w800,
                                                        ),
                                                      ),
                                                    ),
                                                  ],
                                                ),
                                                const SizedBox(height: 2),
                                                Text(
                                                  name,
                                                  overflow: TextOverflow.ellipsis,
                                                  style: const TextStyle(color: AppTheme.textSecondary, fontSize: 11),
                                                ),
                                              ],
                                            ),
                                          ),
                                        ],
                                      ),
                                    ),
                                    const SizedBox(width: 8),
                                    Column(
                                      crossAxisAlignment: CrossAxisAlignment.end,
                                      children: [
                                        Text(
                                          priceNum > 0 ? "₹${priceNum.toStringAsFixed(2)}" : "--",
                                          style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 15),
                                        ),
                                        const SizedBox(height: 2),
                                        Text(
                                          priceNum > 0 ? "${isPos ? '▲' : '▼'} $chg" : "--",
                                          style: TextStyle(
                                            color: priceNum > 0 ? (isPos ? AppTheme.primaryEmerald : AppTheme.dangerRose) : AppTheme.textSecondary,
                                            fontSize: 11,
                                            fontWeight: FontWeight.w800,
                                          ),
                                        ),
                                      ],
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 10),
                                const Divider(color: AppTheme.cardBorder, height: 1),
                                const SizedBox(height: 10),

                                // BOTTOM ACTION ROW: AI Signal Badge, Target, Trade Order Button, Delete Button
                                Row(
                                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                  crossAxisAlignment: CrossAxisAlignment.center,
                                  children: [
                                    Flexible(
                                      child: Wrap(
                                        crossAxisAlignment: WrapCrossAlignment.center,
                                        spacing: 6,
                                        runSpacing: 4,
                                        children: [
                                          if (!hasRealPrice || signal == '--')
                                            Container(
                                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                              decoration: BoxDecoration(
                                                color: Colors.white.withOpacity(0.04),
                                                borderRadius: BorderRadius.circular(6),
                                                border: Border.all(color: AppTheme.cardBorder),
                                              ),
                                              child: const Text(
                                                "--",
                                                style: TextStyle(color: AppTheme.textMuted, fontSize: 10, fontWeight: FontWeight.w700),
                                              ),
                                            )
                                          else
                                            Container(
                                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                              decoration: BoxDecoration(
                                                color: signalColor.withOpacity(0.12),
                                                borderRadius: BorderRadius.circular(20),
                                                border: Border.all(color: signalColor.withOpacity(0.4)),
                                              ),
                                              child: Row(
                                                mainAxisSize: MainAxisSize.min,
                                                children: [
                                                  Container(
                                                    width: 6,
                                                    height: 6,
                                                    decoration: BoxDecoration(color: signalColor, shape: BoxShape.circle),
                                                  ),
                                                  const SizedBox(width: 5),
                                                  Text(
                                                    signal,
                                                    style: TextStyle(color: signalColor, fontSize: 10, fontWeight: FontWeight.w900),
                                                  ),
                                                ],
                                              ),
                                            ),
                                          Builder(
                                            builder: (context) {
                                              final isTargetUnset = !hasRealPrice || target == '--' || target == '-' || target == '₹0' || target == '0';
                                              final isSlUnset = !hasRealPrice || stopLoss == '--' || stopLoss == '-' || stopLoss == '₹0' || stopLoss == '0';
                                              final targetText = isTargetUnset ? '--' : (target.startsWith('₹') ? target : '₹$target');
                                              final slText = isSlUnset ? '--' : (stopLoss.startsWith('₹') ? stopLoss : '₹$stopLoss');
                                              return RichText(
                                                text: TextSpan(
                                                  style: const TextStyle(color: AppTheme.textSecondary, fontSize: 11, fontWeight: FontWeight.w600),
                                                  children: [
                                                    const TextSpan(text: "Target: "),
                                                    TextSpan(
                                                      text: targetText,
                                                      style: TextStyle(
                                                        color: isTargetUnset ? AppTheme.textSecondary : AppTheme.primaryEmerald,
                                                        fontWeight: FontWeight.w900,
                                                      ),
                                                    ),
                                                    const TextSpan(text: "  •  SL: "),
                                                    TextSpan(
                                                      text: slText,
                                                      style: TextStyle(
                                                        color: isSlUnset ? AppTheme.textSecondary : AppTheme.dangerRose,
                                                        fontWeight: FontWeight.w900,
                                                      ),
                                                    ),
                                                  ],
                                                ),
                                              );
                                            },
                                          ),
                                        ],
                                      ),
                                    ),
                                    const SizedBox(width: 8),

                                     Row(
                                       children: [
                                         // Candles & Camarilla Chart Button
                                         GestureDetector(
                                           onTap: () {
                                             CandleChartModal.show(context, symbol: symbol);
                                           },
                                           onLongPress: () {
                                             Navigator.of(context).push(
                                               MaterialPageRoute(
                                                 builder: (_) => CandleChartScreen(symbol: symbol),
                                               ),
                                             );
                                           },
                                           child: Container(
                                             padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
                                             decoration: BoxDecoration(
                                               color: Colors.white.withOpacity(0.06),
                                               borderRadius: BorderRadius.circular(8),
                                               border: Border.all(color: Colors.white.withOpacity(0.12)),
                                             ),
                                             child: const Row(
                                               children: [
                                                 Text("📊", style: TextStyle(fontSize: 12)),
                                               ],
                                             ),
                                           ),
                                         ),
                                         const SizedBox(width: 6),

                                         // Trade Order Button
                                        GestureDetector(
                                          onTap: () {
                                            TradeOrderModal.show(
                                              context,
                                              symbol: symbol,
                                              currentPrice: priceNum,
                                              initialType: 'BUY',
                                              targetPrice: (target == '--' || target == '-' || target == '₹0' || target == '0')
                                                  ? ''
                                                  : target.toString().replaceAll('₹', '').trim(),
                                              stopLoss: (stopLoss == '--' || stopLoss == '-' || stopLoss == '₹0' || stopLoss == '0')
                                                  ? ''
                                                  : stopLoss.toString().replaceAll('₹', '').trim(),
                                            );
                                          },
                                          child: Container(
                                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                                            decoration: BoxDecoration(
                                              color: AppTheme.cyan.withOpacity(0.12),
                                              borderRadius: BorderRadius.circular(8),
                                              border: Border.all(color: AppTheme.borderCyan),
                                            ),
                                            child: Row(
                                              children: const [
                                                Icon(Icons.bolt, color: AppTheme.cyan, size: 14),
                                                SizedBox(width: 3),
                                                Text(
                                                  "Trade Order",
                                                  style: TextStyle(color: AppTheme.cyan, fontWeight: FontWeight.w900, fontSize: 11),
                                                ),
                                              ],
                                            ),
                                          ),
                                        ),
                                        const SizedBox(width: 6),

                                        // Delete Ticker Button
                                        Material(
                                          color: Colors.transparent,
                                          child: InkWell(
                                            onTap: () => _removeSymbol(symbol, item['id']),
                                            borderRadius: BorderRadius.circular(8),
                                            child: Ink(
                                              padding: const EdgeInsets.all(7),
                                              decoration: BoxDecoration(
                                                color: AppTheme.dangerRose.withOpacity(0.14),
                                                borderRadius: BorderRadius.circular(8),
                                                border: Border.all(color: AppTheme.dangerRose.withOpacity(0.4)),
                                              ),
                                              child: const Icon(Icons.delete_outline, color: AppTheme.dangerRose, size: 16),
                                            ),
                                          ),
                                        ),
                                      ],
                                    ),
                                  ],
                                ),
                              ],
                            ),
                          );
                        },
                      ),
          ),
        ],
      ),
    );
  }
}
