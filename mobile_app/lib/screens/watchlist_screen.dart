import 'dart:async';
import 'package:flutter/material.dart';
import '../config/theme.dart';
import '../services/supabase_service.dart';
import '../utils/error_handler.dart';
import '../widgets/custom_widgets.dart';

class WatchlistScreen extends StatefulWidget {
  const WatchlistScreen({super.key});

  @override
  State<WatchlistScreen> createState() => _WatchlistScreenState();
}

class _WatchlistScreenState extends State<WatchlistScreen> {
  final _searchController = TextEditingController();
  List<Map<String, dynamic>> _watchlist = [];
  bool _isLoading = true;
  bool _autoSync = true;
  StreamSubscription<List<Map<String, dynamic>>>? _watchlistSub;

  @override
  void initState() {
    super.initState();
    _loadWatchlist();
    _subscribeToWatchlist();
  }

  @override
  void dispose() {
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

  Future<void> _loadWatchlist() async {
    final user = SupabaseService().currentUser;
    if (user == null) {
      setState(() {
        _isLoading = false;
        _watchlist = [];
      });
      return;
    }

    setState(() => _isLoading = true);
    final data = await SupabaseService().fetchWatchlist();
    if (mounted) {
      setState(() {
        _watchlist = data;
        _isLoading = false;
      });
    }
  }

  Future<void> _addSymbol(String symbol) async {
    if (symbol.trim().isEmpty) {
      ErrorHandler.showErrorSnackBar(context, "Please enter a valid NSE ticker symbol.");
      return;
    }
    final sym = symbol.trim().toUpperCase();

    final user = SupabaseService().currentUser;
    if (user != null) {
      final ok = await SupabaseService().addToWatchlist(sym);
      if (ok) {
        if (mounted) {
          ErrorHandler.showSuccessSnackBar(context, "$sym added to watchlist!");
        }
      } else {
        if (mounted) {
          ErrorHandler.showErrorSnackBar(context, "Failed to add $sym to watchlist.");
        }
      }
    }
    _loadWatchlist();
    _searchController.clear();
  }

  Future<void> _removeSymbol(String id, String symbol) async {
    final ok = await SupabaseService().removeFromWatchlist(id);
    if (ok) {
      setState(() {
        _watchlist.removeWhere((item) => item['id'] == id);
      });
      if (mounted) {
        ErrorHandler.showSuccessSnackBar(context, "$symbol removed from watchlist.");
      }
    } else {
      if (mounted) {
        ErrorHandler.showErrorSnackBar(context, "Failed to remove $symbol from watchlist.");
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.darkBackground,
      appBar: AppBar(
        backgroundColor: AppTheme.darkBackground,
        elevation: 0,
        title: Column(
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
                    "${_watchlist.length} Tickers",
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
      body: Column(
        children: [
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
                        hintText: "ADD NSE TICKER (E.G. BAJAJFINSV)",
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
                    onChanged: (val) => setState(() => _autoSync = val),
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
                : _watchlist.isEmpty
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
                                "Add NSE stock symbols above (e.g., RELIANCE, TCS, INFY) to monitor breakouts, earnings, and block deals.",
                                textAlign: TextAlign.center,
                                style: TextStyle(color: AppTheme.textSecondary, fontSize: 12),
                              ),
                            ],
                          ),
                        ),
                      )
                    : ListView.builder(
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                        itemCount: _watchlist.length,
                        itemBuilder: (context, index) {
                          final item = _watchlist[index];
                          final isAuto = item['is_auto_synced'] ?? false;
                          final isPos = item['is_positive'] ?? true;
                          final priceNum = (item['price'] as num? ?? 1250.0).toDouble();
                          final signal = item['signal'] ?? 'BUY';
                          final target = item['target'] ?? '1,500';
                          final symbol = item['symbol'] as String;
                          final initial = symbol.length >= 2 ? symbol.substring(0, 2) : symbol;

                          Color signalColor = AppTheme.cyan;
                          if (signal == 'STRONG BUY') signalColor = AppTheme.primaryEmerald;
                          if (signal == 'TAKE PROFIT') signalColor = AppTheme.warningAmber;

                          return GlassCard(
                            margin: const EdgeInsets.only(bottom: 12),
                            child: Column(
                              children: [
                                // TOP ROW: Stock symbol, badge, price, change
                                Row(
                                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                  children: [
                                    Row(
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
                                        const SizedBox(width: 12),
                                        Column(
                                          crossAxisAlignment: CrossAxisAlignment.start,
                                          children: [
                                            Row(
                                              children: [
                                                Text(
                                                  symbol,
                                                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 15),
                                                ),
                                                const SizedBox(width: 6),
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
                                              item['name'] ?? symbol,
                                              style: const TextStyle(color: AppTheme.textSecondary, fontSize: 11),
                                            ),
                                          ],
                                        ),
                                      ],
                                    ),

                                    Column(
                                      crossAxisAlignment: CrossAxisAlignment.end,
                                      children: [
                                        Text(
                                          "₹${priceNum.toStringAsFixed(2)}",
                                          style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 15),
                                        ),
                                        const SizedBox(height: 2),
                                        Text(
                                          "${isPos ? '▲' : '▼'} ${item['chg'] ?? '+1.2%'}",
                                          style: TextStyle(
                                            color: isPos ? AppTheme.primaryEmerald : AppTheme.dangerRose,
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
                                  children: [
                                    Row(
                                      children: [
                                        Container(
                                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                          decoration: BoxDecoration(
                                            color: signalColor.withOpacity(0.12),
                                            borderRadius: BorderRadius.circular(20),
                                            border: Border.all(color: signalColor.withOpacity(0.4)),
                                          ),
                                          child: Row(
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
                                        const SizedBox(width: 8),
                                        Text(
                                          "Target: ₹$target",
                                          style: const TextStyle(color: AppTheme.textSecondary, fontSize: 11, fontWeight: FontWeight.w600),
                                        ),
                                      ],
                                    ),

                                    Row(
                                      children: [
                                        // Trade Order Button
                                        GestureDetector(
                                          onTap: () {
                                            TradeOrderModal.show(
                                              context,
                                              symbol: symbol,
                                              currentPrice: priceNum,
                                              initialType: 'BUY',
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
                                        GestureDetector(
                                          onTap: () => _removeSymbol(item['id'], symbol),
                                          child: Container(
                                            padding: const EdgeInsets.all(6),
                                            decoration: BoxDecoration(
                                              color: AppTheme.dangerRose.withOpacity(0.12),
                                              borderRadius: BorderRadius.circular(8),
                                              border: Border.all(color: AppTheme.dangerRose.withOpacity(0.4)),
                                            ),
                                            child: const Icon(Icons.delete_outline, color: AppTheme.dangerRose, size: 16),
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
