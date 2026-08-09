import 'package:flutter/material.dart';
import '../config/theme.dart';
import '../services/supabase_service.dart';

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
    if (user == null) return;

    setState(() => _isLoading = true);
    try {
      final data = await SupabaseService().client
          .from('user_watchlists')
          .select()
          .eq('user_id', user.id);
      
      setState(() {
        _watchlist = List<Map<String, dynamic>>.from(data);
        _isLoading = false;
      });
    } catch (e) {
      debugPrint("Error loading watchlist: $e");
      setState(() => _isLoading = false);
    }
  }

  Future<void> _addSymbol(String symbol) async {
    final user = SupabaseService().currentUser;
    if (user == null || symbol.trim().isEmpty) return;

    final sym = symbol.trim().toUpperCase();
    try {
      await SupabaseService().client.from('user_watchlists').upsert({
        'user_id': user.id,
        'symbol': sym,
        'is_auto_synced': false,
      });
      _searchController.clear();
      _loadWatchlist();
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Error adding symbol: $e")),
      );
    }
  }

  Future<void> _removeSymbol(String id) async {
    try {
      await SupabaseService().client.from('user_watchlists').delete().eq('id', id);
      _loadWatchlist();
    } catch (e) {
      debugPrint("Error removing symbol: $e");
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Watchlist Manager"),
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _searchController,
                    style: const TextStyle(color: Colors.white),
                    textCapitalization: TextCapitalization.characters,
                    decoration: InputDecoration(
                      hintText: "Add NSE Ticker (e.g. RELIANCE)",
                      hintStyle: const TextStyle(color: AppTheme.textSecondary, fontSize: 13),
                      filled: true,
                      fillColor: AppTheme.cardBackground,
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
                      prefixIcon: const Icon(Icons.search, color: AppTheme.textSecondary),
                    ),
                    onSubmitted: _addSymbol,
                  ),
                ),
                const SizedBox(width: 10),
                IconButton.filled(
                  style: IconButton.styleFrom(backgroundColor: AppTheme.primaryEmerald),
                  onPressed: () => _addSymbol(_searchController.text),
                  icon: const Icon(Icons.add, color: Colors.black),
                )
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16.0),
            child: Card(
              child: SwitchListTile(
                activeColor: AppTheme.primaryEmerald,
                title: const Text("Auto-Sync ICICI Demat Holdings", style: TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.bold)),
                subtitle: const Text("Automatically import & monitor active demat stocks", style: TextStyle(color: AppTheme.textSecondary, fontSize: 11)),
                value: _autoSync,
                onChanged: (val) {
                  setState(() => _autoSync = val);
                },
              ),
            ),
          ),
          const SizedBox(height: 12),
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator(color: AppTheme.primaryEmerald))
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
                          return Card(
                            margin: const EdgeInsets.only(bottom: 8),
                            child: ListTile(
                              leading: Icon(isAuto ? Icons.account_balance : Icons.show_chart, color: AppTheme.primaryEmerald),
                              title: Text(item['symbol'], style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                              subtitle: Text(isAuto ? "Auto-synced Demat Holding" : "Custom Watchlist Ticker", style: const TextStyle(color: AppTheme.textSecondary, fontSize: 11)),
                              trailing: IconButton(
                                icon: const Icon(Icons.delete_outline, color: AppTheme.dangerRose),
                                onPressed: () => _removeSymbol(item['id']),
                              ),
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
