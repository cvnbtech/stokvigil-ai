import 'package:flutter/material.dart';
import '../config/theme.dart';
import '../models/models.dart';
import '../services/api_service.dart';
import '../services/supabase_service.dart';

class DashboardScreen extends StatefulWidget {
  final VoidCallback onOpenCredentials;

  const DashboardScreen({super.key, required this.onOpenCredentials});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  bool _isLoading = true;
  bool _hasCredentials = false;
  double _totalValue = 0.0;
  double _totalPnl = 0.0;
  double _totalPnlPct = 0.0;
  List<PortfolioHolding> _holdings = [];

  @override
  void initState() {
    super.initState();
    _loadPortfolioData();
  }

  Future<void> _loadPortfolioData() async {
    final user = SupabaseService().currentUser;
    if (user == null) return;

    setState(() => _isLoading = true);
    final data = await ApiService().fetchPortfolioSummary(user.id);
    
    setState(() {
      _hasCredentials = data['has_credentials'] ?? false;
      _totalValue = (data['total_portfolio_value'] ?? 0.0).toDouble();
      _totalPnl = (data['total_pnl'] ?? 0.0).toDouble();
      _totalPnlPct = (data['total_pnl_percent'] ?? 0.0).toDouble();
      
      final list = (data['holdings'] as List? ?? []);
      _holdings = list.map((item) => PortfolioHolding.fromJson(item)).toList();
      _isLoading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    final isPositive = _totalPnl >= 0;

    return RefreshIndicator(
      onRefresh: _loadPortfolioData,
      color: AppTheme.primaryEmerald,
      child: ListView(
        padding: const EdgeInsets.all(20.0),
        children: [
          // Header Bar
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: const [
                  Text("Portfolio Intelligence", style: TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.bold)),
                  Text("Live Demat Holdings Radar", style: TextStyle(color: AppTheme.textSecondary, fontSize: 13)),
                ],
              ),
              GestureDetector(
                onTap: widget.onOpenCredentials,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: (_hasCredentials ? AppTheme.primaryEmerald : AppTheme.dangerRose).withOpacity(0.15),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: _hasCredentials ? AppTheme.primaryEmerald : AppTheme.dangerRose),
                  ),
                  child: Row(
                    children: [
                      Icon(Icons.circle, size: 8, color: _hasCredentials ? AppTheme.primaryEmerald : AppTheme.dangerRose),
                      const SizedBox(width: 6),
                      Text(
                        _hasCredentials ? "Key Active" : "Needs Key",
                        style: TextStyle(
                          color: _hasCredentials ? AppTheme.primaryEmerald : AppTheme.dangerRose,
                          fontWeight: FontWeight.bold,
                          fontSize: 12,
                        ),
                      ),
                    ],
                  ),
                ),
              )
            ],
          ),
          const SizedBox(height: 20),

          // Summary Card
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [AppTheme.cardBackground, AppTheme.cardBackground.withRed(25)],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: AppTheme.cardBorder),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text("TOTAL PORTFOLIO VALUE", style: TextStyle(color: AppTheme.textSecondary, fontSize: 11, fontWeight: FontWeight.bold)),
                const SizedBox(height: 6),
                Text(
                  "₹${_totalValue.toStringAsFixed(2)}",
                  style: const TextStyle(color: Colors.white, fontSize: 32, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 16),
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                      decoration: BoxDecoration(
                        color: (isPositive ? AppTheme.primaryEmerald : AppTheme.dangerRose).withOpacity(0.2),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Row(
                        children: [
                          Icon(isPositive ? Icons.trending_up : Icons.trending_down, color: isPositive ? AppTheme.primaryEmerald : AppTheme.dangerRose, size: 16),
                          const SizedBox(width: 4),
                          Text(
                            "${isPositive ? '+' : ''}${_totalPnl.toStringAsFixed(2)} (${_totalPnlPct.toStringAsFixed(2)}%)",
                            style: TextStyle(
                              color: isPositive ? AppTheme.primaryEmerald : AppTheme.dangerRose,
                              fontWeight: FontWeight.bold,
                              fontSize: 13,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 10),
                    const Text("Overall P/L", style: TextStyle(color: AppTheme.textSecondary, fontSize: 12)),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),

          const Text("Holdings Monitored by AI", style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold)),
          const SizedBox(height: 12),

          if (_isLoading)
            const Center(child: Padding(padding: EdgeInsets.all(30), child: CircularProgressIndicator(color: AppTheme.primaryEmerald)))
          else if (_holdings.isEmpty)
            Container(
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(color: AppTheme.cardBackground, borderRadius: BorderRadius.circular(16)),
              child: Column(
                children: [
                  const Icon(Icons.account_balance_wallet_outlined, color: AppTheme.textSecondary, size: 40),
                  const SizedBox(height: 12),
                  const Text("No Holdings Found or Token Expired", style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 6),
                  const Text("Tap 'Needs Key' above to setup your morning ICICI Breeze Session token.", textAlign: TextAlign.center, style: TextStyle(color: AppTheme.textSecondary, fontSize: 12)),
                  const SizedBox(height: 16),
                  ElevatedButton(
                    style: ElevatedButton.styleFrom(backgroundColor: AppTheme.primaryEmerald),
                    onPressed: widget.onOpenCredentials,
                    child: const Text("Setup Session Key", style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold)),
                  )
                ],
              ),
            )
          else
            ListView.builder(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: _holdings.length,
              itemBuilder: (context, index) {
                final item = _holdings[index];
                final pnlPos = item.pnl >= 0;
                return Card(
                  margin: const EdgeInsets.only(bottom: 10),
                  child: ListTile(
                    contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                    title: Text(item.symbol, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                    subtitle: Text("Qty: ${item.quantity.toInt()} • Avg: ₹${item.avgPrice}", style: const TextStyle(color: AppTheme.textSecondary, fontSize: 12)),
                    trailing: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        Text("₹${item.currentPrice}", style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14)),
                        const SizedBox(height: 4),
                        Text(
                          "${pnlPos ? '+' : ''}₹${item.pnl.toStringAsFixed(1)}",
                          style: TextStyle(color: pnlPos ? AppTheme.primaryEmerald : AppTheme.dangerRose, fontSize: 12, fontWeight: FontWeight.w600),
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
        ],
      ),
    );
  }
}
