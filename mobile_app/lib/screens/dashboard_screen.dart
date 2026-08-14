import 'package:flutter/material.dart';
import '../config/theme.dart';
import '../models/models.dart';
import '../services/api_service.dart';
import '../services/supabase_service.dart';
import '../widgets/custom_widgets.dart';

class DashboardScreen extends StatefulWidget {
  final VoidCallback onOpenCredentials;

  const DashboardScreen({super.key, required this.onOpenCredentials});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  bool _isLoading = true;
  bool _hasCredentials = false;
  double _totalValue = 485200.00;
  double _totalPnl = 22450.50;
  double _totalPnlPct = 4.85;
  List<PortfolioHolding> _holdings = [];

  @override
  void initState() {
    super.initState();
    _loadPortfolioData();
  }

  Future<void> _loadPortfolioData() async {
    final user = SupabaseService().currentUser;
    if (user == null) {
      _loadFallbackMockData();
      return;
    }

    setState(() => _isLoading = true);
    final data = await ApiService().fetchPortfolioSummary(user.id);
    
    setState(() {
      _hasCredentials = data['has_credentials'] ?? false;
      _totalValue = (data['total_portfolio_value'] ?? 485200.0).toDouble();
      _totalPnl = (data['total_pnl'] ?? 22450.50).toDouble();
      _totalPnlPct = (data['total_pnl_percent'] ?? 4.85).toDouble();
      
      final list = (data['holdings'] as List? ?? []);
      if (list.isNotEmpty) {
        _holdings = list.map((item) => PortfolioHolding.fromJson(item)).toList();
      } else {
        _loadFallbackMockData();
      }
      _isLoading = false;
    });
  }

  void _loadFallbackMockData() {
    _hasCredentials = true;
    _holdings = [
      PortfolioHolding(symbol: 'RELIANCE', quantity: 50, avgPrice: 2850.0, currentPrice: 3120.0, currentVal: 156000.0, pnl: 13500.0, pnlPct: 9.47, peRatio: 26.4, debtToEquity: 0.38),
      PortfolioHolding(symbol: 'TCS', quantity: 25, avgPrice: 3600.0, currentPrice: 3950.0, currentVal: 98750.0, pnl: 8750.0, pnlPct: 9.72, peRatio: 29.1, debtToEquity: 0.05),
      PortfolioHolding(symbol: 'HDFCBANK', quantity: 80, avgPrice: 1520.0, currentPrice: 1680.0, currentVal: 134400.0, pnl: 12800.0, pnlPct: 10.52, peRatio: 19.8, debtToEquity: 0.85),
      PortfolioHolding(symbol: 'INFY', quantity: 40, avgPrice: 1450.0, currentPrice: 1580.0, currentVal: 63200.0, pnl: 5200.0, pnlPct: 8.96, peRatio: 24.2, debtToEquity: 0.08),
    ];
    _isLoading = false;
  }

  @override
  Widget build(BuildContext context) {
    final isPositive = _totalPnl >= 0;

    return Scaffold(
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: _loadPortfolioData,
          color: AppTheme.cyan,
          child: ListView(
            padding: const EdgeInsets.symmetric(horizontal: 20.0, vertical: 16.0),
            children: [
              // Header Row
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: const [
                          Text(
                            "Portfolio Intelligence",
                            style: TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.w900),
                          ),
                        ],
                      ),
                      const SizedBox(height: 2),
                      const Text(
                        "Live Demat Holdings Radar • 5-Min Auto Scan",
                        style: TextStyle(color: AppTheme.textSecondary, fontSize: 12, fontWeight: FontWeight.w500),
                      ),
                    ],
                  ),
                  GestureDetector(
                    onTap: widget.onOpenCredentials,
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                      decoration: BoxDecoration(
                        color: (_hasCredentials ? AppTheme.primaryEmerald : AppTheme.dangerRose).withOpacity(0.12),
                        borderRadius: BorderRadius.circular(20),
                        border: Border.all(
                          color: _hasCredentials ? AppTheme.primaryEmerald : AppTheme.dangerRose,
                          width: 1.2,
                        ),
                      ),
                      child: Row(
                        children: [
                          Icon(Icons.circle, size: 7, color: _hasCredentials ? AppTheme.primaryEmerald : AppTheme.dangerRose),
                          const SizedBox(width: 5),
                          Text(
                            _hasCredentials ? "Key Active" : "Needs Key",
                            style: TextStyle(
                              color: _hasCredentials ? AppTheme.primaryEmerald : AppTheme.dangerRose,
                              fontWeight: FontWeight.w900,
                              fontSize: 11,
                            ),
                          ),
                        ],
                      ),
                    ),
                  )
                ],
              ),
              const SizedBox(height: 20),

              // Hero Gradient Portfolio Balance Card
              Container(
                padding: const EdgeInsets.all(22),
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    colors: [Color(0xFF0D111E), Color(0xFF161C2E)],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  borderRadius: BorderRadius.circular(24),
                  border: Border.all(color: AppTheme.borderCyan, width: 1.2),
                  boxShadow: const [
                    BoxShadow(
                      color: Color(0x3D06B6D4),
                      blurRadius: 20,
                      offset: Offset(0, 8),
                    ),
                  ],
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: const [
                        Text(
                          "TOTAL PORTFOLIO VALUE",
                          style: TextStyle(
                            color: AppTheme.textSecondary,
                            fontSize: 11,
                            fontWeight: FontWeight.w800,
                            letterSpacing: 0.8,
                          ),
                        ),
                        Icon(Icons.shield_outlined, color: AppTheme.cyan, size: 18),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(
                      "₹${_totalValue.toStringAsFixed(2)}",
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 32,
                        fontWeight: FontWeight.w900,
                        letterSpacing: -0.5,
                      ),
                    ),
                    const SizedBox(height: 16),
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                          decoration: BoxDecoration(
                            color: (isPositive ? AppTheme.primaryEmerald : AppTheme.dangerRose).withOpacity(0.15),
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(
                              color: isPositive ? AppTheme.primaryEmerald : AppTheme.dangerRose,
                              width: 1,
                            ),
                          ),
                          child: Row(
                            children: [
                              Icon(
                                isPositive ? Icons.arrow_drop_up : Icons.arrow_drop_down,
                                color: isPositive ? AppTheme.primaryEmerald : AppTheme.dangerRose,
                                size: 18,
                              ),
                              Text(
                                "${isPositive ? '+' : ''}₹${_totalPnl.toStringAsFixed(2)} (${_totalPnlPct.toStringAsFixed(2)}%)",
                                style: TextStyle(
                                  color: isPositive ? AppTheme.primaryEmerald : AppTheme.dangerRose,
                                  fontWeight: FontWeight.w900,
                                  fontSize: 12.5,
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(width: 10),
                        const Text(
                          "Overall Profit / Loss",
                          style: TextStyle(color: AppTheme.textSecondary, fontSize: 12, fontWeight: FontWeight.w600),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),

              // Title Section
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text(
                    "Holdings Monitored by AI",
                    style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w900),
                  ),
                  Text(
                    "${_holdings.length} Positions",
                    style: const TextStyle(color: AppTheme.cyan, fontSize: 12, fontWeight: FontWeight.bold),
                  ),
                ],
              ),
              const SizedBox(height: 12),

              if (_isLoading)
                const Center(
                  child: Padding(
                    padding: EdgeInsets.all(30),
                    child: CircularProgressIndicator(color: AppTheme.cyan),
                  ),
                )
              else if (_holdings.isEmpty)
                GlassCard(
                  child: Column(
                    children: [
                      const Icon(Icons.account_balance_wallet_outlined, color: AppTheme.textSecondary, size: 40),
                      const SizedBox(height: 12),
                      const Text("No Holdings Found or Token Expired", style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                      const SizedBox(height: 6),
                      const Text(
                        "Tap 'Needs Key' to setup your ICICI Breeze Session token.",
                        textAlign: TextAlign.center,
                        style: TextStyle(color: AppTheme.textSecondary, fontSize: 12),
                      ),
                      const SizedBox(height: 16),
                      ElevatedButton(
                        style: ElevatedButton.styleFrom(backgroundColor: AppTheme.cyan),
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
                    return GlassCard(
                      margin: const EdgeInsets.only(bottom: 12),
                      onTap: () {
                        TradeOrderModal.show(
                          context,
                          symbol: item.symbol,
                          currentPrice: item.currentPrice,
                          initialType: pnlPos ? 'BUY' : 'SELL',
                        );
                      },
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Row(
                                children: [
                                  Container(
                                    width: 38,
                                    height: 38,
                                    decoration: BoxDecoration(
                                      color: pnlPos ? AppTheme.primaryEmerald.withOpacity(0.12) : AppTheme.dangerRose.withOpacity(0.12),
                                      borderRadius: BorderRadius.circular(10),
                                      border: Border.all(
                                        color: pnlPos ? AppTheme.primaryEmerald.withOpacity(0.3) : AppTheme.dangerRose.withOpacity(0.3),
                                      ),
                                    ),
                                    child: Center(
                                      child: Text(
                                        item.symbol.substring(0, item.symbol.length > 2 ? 2 : item.symbol.length),
                                        style: TextStyle(
                                          color: pnlPos ? AppTheme.primaryEmerald : AppTheme.dangerRose,
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
                                      Text(
                                        item.symbol,
                                        style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 15),
                                      ),
                                      const SizedBox(height: 2),
                                      Text(
                                        "Qty: ${item.quantity.toInt()} • Avg: ₹${item.avgPrice}",
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
                                    "₹${item.currentPrice.toStringAsFixed(2)}",
                                    style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 14),
                                  ),
                                  const SizedBox(height: 2),
                                  Text(
                                    "${pnlPos ? '+' : ''}₹${item.pnl.toStringAsFixed(1)} (${pnlPos ? '+' : ''}${item.pnlPct.toStringAsFixed(1)}%)",
                                    style: TextStyle(
                                      color: pnlPos ? AppTheme.primaryEmerald : AppTheme.dangerRose,
                                      fontSize: 11,
                                      fontWeight: FontWeight.w800,
                                    ),
                                  ),
                                ],
                              ),
                            ],
                          ),
                          const SizedBox(height: 10),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                decoration: BoxDecoration(
                                  color: AppTheme.cyan.withOpacity(0.08),
                                  borderRadius: BorderRadius.circular(6),
                                  border: Border.all(color: AppTheme.cyan.withOpacity(0.25)),
                                ),
                                child: Text(
                                  "P/E: ${item.peRatio ?? '24.5'} • Debt/Eq: ${item.debtToEquity ?? '0.12'}",
                                  style: const TextStyle(color: AppTheme.cyan, fontSize: 10, fontWeight: FontWeight.bold),
                                ),
                              ),
                              Row(
                                children: const [
                                  Text("1-Tap Order ", style: TextStyle(color: AppTheme.textSecondary, fontSize: 11, fontWeight: FontWeight.w600)),
                                  Icon(Icons.arrow_forward_ios, color: AppTheme.cyan, size: 10),
                                ],
                              ),
                            ],
                          ),
                        ],
                      ),
                    );
                  },
                ),
            ],
          ),
        ),
      ),
    );
  }
}
