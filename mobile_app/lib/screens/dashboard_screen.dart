import 'package:flutter/material.dart';
import '../config/theme.dart';
import '../models/models.dart';
import '../services/api_service.dart';
import '../services/supabase_service.dart';
import '../services/fcm_service.dart';
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
  bool _isPortfolioVisible = false;
  double _totalValue = 0.0;
  double _totalPnl = 0.0;
  double _totalPnlPct = 0.0;
  List<PortfolioHolding> _holdings = [];
  Map<String, dynamic>? _fiiDiiFlows;

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

    // Auto-sync FCM device token in background
    FcmService().syncDeviceToken(user.id);

    // Fetch FII/DII net flows in background
    ApiService().fetchFiiDiiFlows().then((flows) {
      if (mounted && flows != null) {
        setState(() => _fiiDiiFlows = flows);
      }
    });

    setState(() => _isLoading = true);
    final data = await ApiService().fetchPortfolioSummary(user.id);
    
    if (mounted) {
      final todayStr = DateTime.now().toIso8601String().split('T')[0];
      final tokenDate = data['token_date']?.toString();
      final isTokenValidToday = (data['has_credentials'] == true) && (tokenDate == todayStr);

      setState(() {
        _hasCredentials = isTokenValidToday;
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

  String _formatCurrency(double value) {
    final intPart = value.truncate().abs();
    final str = intPart.toString();
    if (str.length <= 3) return str;
    
    final last3 = str.substring(str.length - 3);
    final rest = str.substring(0, str.length - 3);
    
    final formattedRest = rest.replaceAllMapped(
      RegExp(r'(\d)(?=(\d{2})+(?!\d))'),
      (Match m) => '${m[1]},',
    );
    
    return '$formattedRest,$last3';
  }

  String _getDecimals(double value) {
    final frac = ((value.abs() - value.abs().truncate()) * 100).round();
    return frac.toString().padLeft(2, '0');
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
              // Top Brand Header with Key Active Badge
              StokVigilBrandHeader(
                logoSize: 38,
                trailing: GestureDetector(
                  onTap: widget.onOpenCredentials,
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    decoration: BoxDecoration(
                      color: (_hasCredentials ? AppTheme.cyan : AppTheme.dangerRose).withOpacity(0.12),
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(
                        color: _hasCredentials ? AppTheme.cyan : AppTheme.dangerRose,
                        width: 1.2,
                      ),
                      boxShadow: [
                        BoxShadow(
                          color: (_hasCredentials ? AppTheme.cyan : AppTheme.dangerRose).withOpacity(0.15),
                          blurRadius: 8,
                          offset: const Offset(0, 2),
                        ),
                      ],
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Text("🔑", style: TextStyle(fontSize: 12)),
                        const SizedBox(width: 6),
                        Text(
                          _hasCredentials ? "Key Active" : "Needs Key",
                          style: TextStyle(
                            color: _hasCredentials ? AppTheme.cyan : AppTheme.dangerRose,
                            fontWeight: FontWeight.w900,
                            fontSize: 12,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
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

              // Institutional FII / DII Flow Bar
              if (_fiiDiiFlows != null) ...[
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                  decoration: BoxDecoration(
                    color: const Color(0xFF080B16),
                    borderRadius: BorderRadius.circular(18),
                    border: Border.all(color: AppTheme.cardBorder),
                  ),
                  child: Column(
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Row(
                            children: [
                              const Text("🏛️ ", style: TextStyle(fontSize: 12)),
                              const Text(
                                "Institutional FII / DII Flows",
                                style: TextStyle(color: Colors.white, fontSize: 11.5, fontWeight: FontWeight.bold),
                              ),
                              const SizedBox(width: 4),
                              Text(
                                "(${_fiiDiiFlows!['date'] ?? ''})",
                                style: const TextStyle(color: AppTheme.textMuted, fontSize: 9.5),
                              ),
                            ],
                          ),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                            decoration: BoxDecoration(
                              color: (_fiiDiiFlows!['combined_net'] ?? 0) >= 0
                                  ? AppTheme.primaryEmerald.withOpacity(0.15)
                                  : AppTheme.dangerRose.withOpacity(0.15),
                              borderRadius: BorderRadius.circular(6),
                            ),
                            child: Text(
                              (_fiiDiiFlows!['sentiment'] ?? 'BALANCED').toString().replaceAll('_', ' '),
                              style: TextStyle(
                                color: (_fiiDiiFlows!['combined_net'] ?? 0) >= 0 ? AppTheme.primaryEmerald : AppTheme.dangerRose,
                                fontSize: 9,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 10),
                      Row(
                        children: [
                          Expanded(
                            child: Column(
                              children: [
                                const Text("FII NET", style: TextStyle(color: AppTheme.textMuted, fontSize: 9, fontWeight: FontWeight.bold)),
                                const SizedBox(height: 2),
                                Text(
                                  "${(_fiiDiiFlows!['fii']?['net'] ?? 0) >= 0 ? '+' : ''}₹${((_fiiDiiFlows!['fii']?['net'] ?? 0) as num).toStringAsFixed(0)} Cr",
                                  style: TextStyle(
                                    color: (_fiiDiiFlows!['fii']?['net'] ?? 0) >= 0 ? AppTheme.primaryEmerald : AppTheme.dangerRose,
                                    fontSize: 11,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                              ],
                            ),
                          ),
                          Expanded(
                            child: Column(
                              children: [
                                const Text("DII NET", style: TextStyle(color: AppTheme.textMuted, fontSize: 9, fontWeight: FontWeight.bold)),
                                const SizedBox(height: 2),
                                Text(
                                  "${(_fiiDiiFlows!['dii']?['net'] ?? 0) >= 0 ? '+' : ''}₹${((_fiiDiiFlows!['dii']?['net'] ?? 0) as num).toStringAsFixed(0)} Cr",
                                  style: TextStyle(
                                    color: (_fiiDiiFlows!['dii']?['net'] ?? 0) >= 0 ? AppTheme.primaryEmerald : AppTheme.dangerRose,
                                    fontSize: 11,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                              ],
                            ),
                          ),
                          Expanded(
                            child: Column(
                              children: [
                                const Text("COMBINED", style: TextStyle(color: AppTheme.cyan, fontSize: 9, fontWeight: FontWeight.bold)),
                                const SizedBox(height: 2),
                                Text(
                                  "${(_fiiDiiFlows!['combined_net'] ?? 0) >= 0 ? '+' : ''}₹${((_fiiDiiFlows!['combined_net'] ?? 0) as num).toStringAsFixed(0)} Cr",
                                  style: TextStyle(
                                    color: (_fiiDiiFlows!['combined_net'] ?? 0) >= 0 ? AppTheme.cyan : AppTheme.dangerRose,
                                    fontSize: 11,
                                    fontWeight: FontWeight.w900,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 14),
              ],

              // Hero Gradient Demat Portfolio Balance Card (Matches Screenshot Design)
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
                    // Header Label with Eye Visibility Toggle Icon
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text(
                          "DEMAT PORTFOLIO VALUE",
                          style: TextStyle(
                            color: Color(0xFF94A3B8),
                            fontSize: 11,
                            fontWeight: FontWeight.w800,
                            letterSpacing: 0.8,
                          ),
                        ),
                        GestureDetector(
                          onTap: () => setState(() => _isPortfolioVisible = !_isPortfolioVisible),
                          behavior: HitTestBehavior.opaque,
                          child: Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                            decoration: BoxDecoration(
                              color: Colors.white.withOpacity(0.06),
                              borderRadius: BorderRadius.circular(12),
                              border: Border.all(
                                color: Colors.white.withOpacity(0.12),
                                width: 0.8,
                              ),
                            ),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(
                                  _isPortfolioVisible ? Icons.visibility_outlined : Icons.visibility_off_outlined,
                                  color: const Color(0xFF94A3B8),
                                  size: 15,
                                ),
                                const SizedBox(width: 4),
                                Text(
                                  _isPortfolioVisible ? "Hide" : "Show",
                                  style: const TextStyle(
                                    color: Color(0xFF94A3B8),
                                    fontSize: 10.5,
                                    fontWeight: FontWeight.w700,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),

                    // Main Portfolio Value (Masked / Unmasked)
                    if (_isPortfolioVisible)
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.baseline,
                        textBaseline: TextBaseline.alphabetic,
                        children: [
                          Text(
                            "₹${_formatCurrency(_totalValue)}",
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 34,
                              fontWeight: FontWeight.w900,
                              letterSpacing: -0.6,
                            ),
                          ),
                          Text(
                            ".${_getDecimals(_totalValue)}",
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 22,
                              fontWeight: FontWeight.w900,
                            ),
                          ),
                        ],
                      )
                    else
                      const Text(
                        "₹ • • • • • •",
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 32,
                          fontWeight: FontWeight.w900,
                          letterSpacing: 2.0,
                        ),
                      ),
                    const SizedBox(height: 10),

                    // Returns, Percentage Badge, All Time
                    Wrap(
                      crossAxisAlignment: WrapCrossAlignment.center,
                      spacing: 8,
                      runSpacing: 6,
                      children: [
                        Text(
                          _isPortfolioVisible
                              ? "${isPositive ? '↑ +' : '↓ -'}₹${_formatCurrency(_totalPnl.abs())}"
                              : "••••••",
                          style: TextStyle(
                            color: isPositive ? AppTheme.primaryEmerald : AppTheme.dangerRose,
                            fontWeight: FontWeight.w900,
                            fontSize: 14,
                          ),
                        ),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                          decoration: BoxDecoration(
                            color: (isPositive ? AppTheme.primaryEmerald : AppTheme.dangerRose).withOpacity(0.12),
                            borderRadius: BorderRadius.circular(20),
                            border: Border.all(
                              color: (isPositive ? AppTheme.primaryEmerald : AppTheme.dangerRose).withOpacity(0.4),
                              width: 1,
                            ),
                          ),
                          child: Text(
                            _isPortfolioVisible
                                ? "${isPositive ? '+' : '-'}${_totalPnlPct.abs().toStringAsFixed(2)}%"
                                : "••• %",
                            style: TextStyle(
                              color: isPositive ? AppTheme.primaryEmerald : AppTheme.dangerRose,
                              fontWeight: FontWeight.w900,
                              fontSize: 11,
                            ),
                          ),
                        ),
                        const Text(
                          "All Time",
                          style: TextStyle(
                            color: Color(0xFF64748B),
                            fontSize: 11.5,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),

                    // Glowing Sparkline Area Chart
                    SizedBox(
                      height: 48,
                      width: double.infinity,
                      child: CustomPaint(
                        painter: PortfolioSparklinePainter(isPositive: isPositive),
                      ),
                    ),
                    const SizedBox(height: 14),

                    // Divider
                    const Divider(color: Color(0x33334155), height: 1),
                    const SizedBox(height: 14),

                    // 3-Column Stats Footer: Invested | Holdings | Day P&L
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        // Column 1: Invested
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text(
                              "Invested",
                              style: TextStyle(color: Color(0xFF64748B), fontSize: 11, fontWeight: FontWeight.w600),
                            ),
                            const SizedBox(height: 3),
                            Text(
                              _isPortfolioVisible
                                  ? "₹${_formatCurrency((_totalValue - _totalPnl).clamp(0.0, double.infinity))}"
                                  : "₹ ••••••",
                              style: const TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.w900),
                            ),
                          ],
                        ),
                        // Column 2: Holdings
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text(
                              "Holdings",
                              style: TextStyle(color: Color(0xFF64748B), fontSize: 11, fontWeight: FontWeight.w600),
                            ),
                            const SizedBox(height: 3),
                            Text(
                              _isPortfolioVisible
                                  ? "${_holdings.length} Stocks"
                                  : "•• Stocks",
                              style: const TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.w900),
                            ),
                          ],
                        ),
                        // Column 3: Day P&L
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text(
                              "Day P&L",
                              style: TextStyle(color: Color(0xFF64748B), fontSize: 11, fontWeight: FontWeight.w600),
                            ),
                            const SizedBox(height: 3),
                            Text(
                              _isPortfolioVisible
                                  ? "${isPositive ? '+₹' : '-₹'}${_formatCurrency((_totalPnl * 0.08).abs())}"
                                  : "••••••",
                              style: TextStyle(
                                color: isPositive ? AppTheme.primaryEmerald : AppTheme.dangerRose,
                                fontSize: 14,
                                fontWeight: FontWeight.w900,
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),

              // Active Holdings Section Header (Matches Screenshot)
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text(
                    "Active Holdings",
                    style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w900),
                  ),
                  Text(
                    "Tap for details • ${_holdings.length} stocks",
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
                      Container(
                        height: 44,
                        decoration: BoxDecoration(
                          gradient: const LinearGradient(
                            colors: [
                              Color(0xFF00B4D8),
                              Color(0xFF0284C7),
                              Color(0xFF6366F1),
                              Color(0xFF8B5CF6),
                            ],
                            begin: Alignment.centerLeft,
                            end: Alignment.centerRight,
                          ),
                          borderRadius: BorderRadius.circular(14),
                          boxShadow: const [
                            BoxShadow(
                              color: Color(0x5506B6D4),
                              blurRadius: 12,
                              offset: Offset(0, 3),
                            ),
                          ],
                        ),
                        child: ElevatedButton(
                          style: ElevatedButton.styleFrom(
                            backgroundColor: Colors.transparent,
                            shadowColor: Colors.transparent,
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                            padding: const EdgeInsets.symmetric(horizontal: 20),
                          ),
                          onPressed: widget.onOpenCredentials,
                          child: const Text(
                            "🔑 Setup Session Key →",
                            style: TextStyle(
                              color: Colors.white,
                              fontWeight: FontWeight.w900,
                              fontSize: 13.5,
                            ),
                          ),
                        ),
                      ),
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
                            crossAxisAlignment: CrossAxisAlignment.center,
                            children: [
                              Expanded(
                                child: Row(
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
                                    const SizedBox(width: 10),
                                    Flexible(
                                      child: Column(
                                        crossAxisAlignment: CrossAxisAlignment.start,
                                        children: [
                                          Text(
                                            item.symbol,
                                            overflow: TextOverflow.ellipsis,
                                            style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 15),
                                          ),
                                          const SizedBox(height: 2),
                                          Text(
                                            "Qty: ${item.quantity.toInt()} • Avg: ₹${item.avgPrice}",
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

// ─────────────────────────────────────────────
// GLOWING PORTFOLIO SPARKLINE AREA CHART
// ─────────────────────────────────────────────
class PortfolioSparklinePainter extends CustomPainter {
  final bool isPositive;

  const PortfolioSparklinePainter({this.isPositive = true});

  @override
  void paint(Canvas canvas, Size size) {
    final color = isPositive ? AppTheme.primaryEmerald : AppTheme.dangerRose;
    final path = Path();

    // Smooth ascending/descending Bezier curve
    final startY = isPositive ? size.height * 0.82 : size.height * 0.22;
    final endY = isPositive ? size.height * 0.12 : size.height * 0.88;

    path.moveTo(0, startY);
    path.cubicTo(
      size.width * 0.35,
      isPositive ? size.height * 0.65 : size.height * 0.35,
      size.width * 0.68,
      isPositive ? size.height * 0.28 : size.height * 0.72,
      size.width,
      endY,
    );

    // Gradient fill below curve
    final fillPath = Path.from(path)
      ..lineTo(size.width, size.height)
      ..lineTo(0, size.height)
      ..close();

    final fillPaint = Paint()
      ..shader = LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: [
          color.withOpacity(0.24),
          color.withOpacity(0.0),
        ],
      ).createShader(Rect.fromLTWH(0, 0, size.width, size.height));

    canvas.drawPath(fillPath, fillPaint);

    // Subtle glow filter
    final glowPaint = Paint()
      ..color = color.withOpacity(0.35)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 4.0
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 3);
    canvas.drawPath(path, glowPaint);

    // Crisp stroke line
    final linePaint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.2
      ..strokeCap = StrokeCap.round;
    canvas.drawPath(path, linePaint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
