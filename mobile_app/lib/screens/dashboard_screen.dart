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
    if (user == null) {
      setState(() {
        _isLoading = false;
        _hasCredentials = false;
        _holdings = [];
      });
      return;
    }

    setState(() => _isLoading = true);
    final data = await ApiService().fetchPortfolioSummary(user.id);
    
    if (mounted) {
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
  }

  String _getGreeting() {
    final hour = DateTime.now().hour;
    if (hour < 12) {
      return "Good morning 👋";
    } else if (hour < 17) {
      return "Good afternoon 👋";
    } else {
      return "Good evening 👋";
    }
  }

  String _getUserName() {
    final user = SupabaseService().currentUser;
    if (user == null) return "Investor";
    final metaName = user.userMetadata?['full_name'] ?? user.userMetadata?['name'];
    if (metaName != null && metaName.toString().trim().isNotEmpty) {
      return metaName.toString().trim();
    }
    if (user.email != null && user.email!.isNotEmpty) {
      final handle = user.email!.split('@').first;
      if (handle.isNotEmpty) {
        return handle[0].toUpperCase() + handle.substring(1);
      }
    }
    return "Investor";
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
              // Top Brand Header
              const StokVigilBrandHeader(logoSize: 38),
              const SizedBox(height: 18),

              // Dynamic Greeting & User Name
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    _getGreeting(),
                    style: const TextStyle(
                      color: AppTheme.textSecondary,
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 3),
                  Text(
                    _getUserName(),
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 22,
                      fontWeight: FontWeight.w900,
                      letterSpacing: -0.4,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),

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
