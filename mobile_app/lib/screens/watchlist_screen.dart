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

  @override
  void initState() {
    super.initState();
    _loadWatchlist();
  }

  Future<void> _loadWatchlist() async {
    final user = SupabaseService().currentUser;
    if (user == null) {
      _loadFallbackMockWatchlist();
      return;
    }

    setState(() => _isLoading = true);
    try {
      final data = await SupabaseService().client
          .from('user_watchlists')
          .select()
          .eq('user_id', user.id);
      
      setState(() {
        if ((data as List).isNotEmpty) {
          _watchlist = List<Map<String, dynamic>>.from(data);
        } else {
          _loadFallbackMockWatchlist();
        }
        _isLoading = false;
      });
    } catch (e) {
      debugPrint("Error loading watchlist: $e");
      _loadFallbackMockWatchlist();
    }
  }

  void _loadFallbackMockWatchlist() {
    _watchlist = [
      {'id': '1', 'symbol': 'RELIANCE', 'name': 'Reliance Industries Ltd', 'price': 3120.0, 'chg': '+1.85%', 'is_positive': true, 'is_auto_synced': true},
      {'id': '2', 'symbol': 'TCS', 'name': 'Tata Consultancy Services', 'price': 3950.0, 'chg': '+2.40%', 'is_positive': true, 'is_auto_synced': true},
      {'id': '3', 'symbol': 'HDFCBANK', 'name': 'HDFC Bank Ltd', 'price': 1680.0, 'chg': '+1.15%', 'is_positive': true, 'is_auto_synced': true},
      {'id': '4', 'symbol': 'BAJAJFINSV', 'name': 'Bajaj Finserv Ltd', 'price': 1640.5, 'chg': '-0.65%', 'is_positive': false, 'is_auto_synced': false},
      {'id': '5', 'symbol': 'TATAMOTORS', 'name': 'Tata Motors Ltd', 'price': 1085.0, 'chg': '+3.10%', 'is_positive': true, 'is_auto_synced': false},
    ];
    _isLoading = false;
  }

  Future<void> _addSymbol(String symbol) async {
    if (symbol.trim().isEmpty) {
      ErrorHandler.showErrorSnackBar(context, "Please enter a valid NSE ticker symbol.");
      return;
    }
    final sym = symbol.trim().toUpperCase();

    final user = SupabaseService().currentUser;
    if (user != null) {
      try {
        await SupabaseService().client.from('user_watchlists').upsert({
          'user_id': user.id,
          'symbol': sym,
          'is_auto_synced': false,
        });
        ErrorHandler.showSuccessSnackBar(context, "$sym added to watchlist!");
      } catch (e) {
        ErrorHandler.showErrorSnackBar(context, e);
      }
    } else {
      ErrorHandler.showSuccessSnackBar(context, "$sym added to watchlist!");
    }

    setState(() {
      _watchlist.insert(0, {
        'id': DateTime.now().millisecondsSinceEpoch.toString(),
        'symbol': sym,
        'name': '$sym India Ltd',
        'price': 1250.0,
        'chg': '+1.20%',
        'is_positive': true,
        'is_auto_synced': false,
      });
    });
    _searchController.clear();
  }

  Future<void> _removeSymbol(String id, String symbol) async {
    try {
      final user = SupabaseService().currentUser;
      if (user != null) {
        await SupabaseService().client.from('user_watchlists').delete().eq('id', id);
      }
      setState(() {
        _watchlist.removeWhere((item) => item['id'] == id);
      });
      if (mounted) {
        ErrorHandler.showSuccessSnackBar(context, "$symbol removed from watchlist.");
      }
    } catch (e) {
      if (mounted) {
        ErrorHandler.showErrorSnackBar(context, e);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            const TradingAILogo(size: 30),
            const SizedBox(width: 10),
            const Text("StokVigil Watchlist", style: TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 18)),
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
      ),
      body: Column(
        children: [
          // Enhanced Ticker Search Bar
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: Row(
              children: [
                Expanded(
                  child: Container(
                    decoration: BoxDecoration(
                      color: AppTheme.cardBackground,
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(color: AppTheme.borderCyan, width: 1.5),
                      boxShadow: const [
                        BoxShadow(color: Color(0x1F06B6D4), blurRadius: 10, offset: Offset(0, 4)),
                      ],
                    ),
                    child: TextField(
                      controller: _searchController,
                      style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13),
                      textCapitalization: TextCapitalization.characters,
                      decoration: const InputDecoration(
                        hintText: "Add NSE ticker (e.g. BAJAJFINSV)",
                        hintStyle: TextStyle(color: AppTheme.textMuted, fontSize: 12),
                        border: InputBorder.none,
                        contentPadding: EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                        prefixIcon: Icon(Icons.search, color: AppTheme.cyan, size: 20),
                      ),
                      onSubmitted: _addSymbol,
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                GestureDetector(
                  onTap: () => _addSymbol(_searchController.text),
                  child: Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      gradient: AppTheme.logoGradient,
                      borderRadius: BorderRadius.circular(14),
                      boxShadow: const [
                        BoxShadow(color: Color(0x4D06B6D4), blurRadius: 12, offset: Offset(0, 4)),
                      ],
                    ),
                    child: const Icon(Icons.add, color: Colors.white, size: 22),
                  ),
                )
              ],
            ),
          ),

          // Demat Auto-Sync Toggle
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16.0),
            child: GlassCard(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
              child: SwitchListTile(
                contentPadding: EdgeInsets.zero,
                activeColor: AppTheme.cyan,
                title: const Text(
                  "📊 Demat Auto-Sync Watchlist",
                  style: TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w900),
                ),
                subtitle: const Text(
                  "Automatically import & monitor active demat stocks",
                  style: TextStyle(color: AppTheme.textSecondary, fontSize: 11),
                ),
                value: _autoSync,
                onChanged: (val) => setState(() => _autoSync = val),
              ),
            ),
          ),
          const SizedBox(height: 12),

          // Watchlist Cards List
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator(color: AppTheme.cyan))
                : _watchlist.isEmpty
                    ? const Center(
                        child: Text("Watchlist empty. Search and add NSE tickers above.", style: TextStyle(color: AppTheme.textSecondary)),
                      )
                    : ListView.builder(
                        padding: const EdgeInsets.symmetric(horizontal: 16),
                        itemCount: _watchlist.length,
                        itemBuilder: (context, index) {
                          final item = _watchlist[index];
                          final isAuto = item['is_auto_synced'] ?? false;
                          final isPos = item['is_positive'] ?? true;
                          final priceNum = (item['price'] as num? ?? 1250.0).toDouble();

                          return GlassCard(
                            margin: const EdgeInsets.only(bottom: 10),
                            onTap: () {
                              TradeOrderModal.show(
                                context,
                                symbol: item['symbol'],
                                currentPrice: priceNum,
                                initialType: 'BUY',
                              );
                            },
                            child: Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Row(
                                  children: [
                                    Container(
                                      width: 40,
                                      height: 40,
                                      decoration: BoxDecoration(
                                        color: isPos ? AppTheme.primaryEmerald.withOpacity(0.12) : AppTheme.dangerRose.withOpacity(0.12),
                                        borderRadius: BorderRadius.circular(11),
                                        border: Border.all(
                                          color: isPos ? AppTheme.primaryEmerald.withOpacity(0.35) : AppTheme.dangerRose.withOpacity(0.35),
                                        ),
                                      ),
                                      child: Center(
                                        child: Text(
                                          (item['symbol'] as String).substring(0, 2),
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
                                              item['symbol'],
                                              style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 15),
                                            ),
                                            const SizedBox(width: 6),
                                            Container(
                                              padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                                              decoration: BoxDecoration(
                                                color: isAuto ? AppTheme.cyan.withOpacity(0.1) : Colors.white.withOpacity(0.05),
                                                borderRadius: BorderRadius.circular(4),
                                                border: Border.all(color: isAuto ? AppTheme.cyan.withOpacity(0.25) : AppTheme.cardBorder),
                                              ),
                                              child: Text(
                                                isAuto ? "📊 Demat Auto-Sync" : "📌 Custom",
                                                style: TextStyle(
                                                  color: isAuto ? AppTheme.cyan : AppTheme.textMuted,
                                                  fontSize: 9,
                                                  fontWeight: FontWeight.bold,
                                                ),
                                              ),
                                            ),
                                          ],
                                        ),
                                        const SizedBox(height: 2),
                                        Text(
                                          item['name'] ?? item['symbol'],
                                          style: const TextStyle(color: AppTheme.textSecondary, fontSize: 11),
                                        ),
                                      ],
                                    ),
                                  ],
                                ),

                                Row(
                                  children: [
                                    Column(
                                      crossAxisAlignment: CrossAxisAlignment.end,
                                      children: [
                                        Text(
                                          "₹${priceNum.toStringAsFixed(2)}",
                                          style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 14),
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
                                    const SizedBox(width: 8),
                                    IconButton(
                                      icon: const Icon(Icons.delete_outline, color: AppTheme.dangerRose, size: 20),
                                      onPressed: () => _removeSymbol(item['id'], item['symbol']),
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
