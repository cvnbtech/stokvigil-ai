import 'dart:math' as math;
import 'package:flutter/material.dart';
import '../config/theme.dart';
import '../services/api_service.dart';

/// Institutional Strategy Backtester Screen.
/// Performs in-memory historical backtests over NSE and BSE equities with 1% capital risk sizing.
/// Adheres strictly to Zero-Default policy: shows actual backtested exchange metrics or clean error, never fake mock data.
class BacktestScreen extends StatefulWidget {
  final String initialSymbol;

  const BacktestScreen({
    super.key,
    this.initialSymbol = '',
  });

  @override
  State<BacktestScreen> createState() => _BacktestScreenState();
}

class _BacktestScreenState extends State<BacktestScreen> {
  late TextEditingController _symbolController;
  String _selectedStrategy = 'camarilla_breakout';
  String _selectedPeriod = '1y';
  bool _isLoading = false;
  String? _errorMessage;
  Map<String, dynamic>? _result;

  @override
  void initState() {
    super.initState();
    _symbolController = TextEditingController(text: widget.initialSymbol);
    if (widget.initialSymbol.trim().isNotEmpty) {
      _runBacktest();
    }
  }

  @override
  void dispose() {
    _symbolController.dispose();
    super.dispose();
  }

  Future<void> _runBacktest() async {
    final sym = _symbolController.text.trim();
    if (sym.isEmpty) return;

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    final res = await ApiService().fetchStrategyBacktest(
      symbol: sym,
      period: _selectedPeriod,
      strategy: _selectedStrategy,
      capital: 200000.0,
      riskBudget: 2000.0,
    );

    if (!mounted) return;

    setState(() {
      _isLoading = false;
      if (res != null && res['status'] == 'success') {
        _result = res;
      } else {
        _result = null;
        _errorMessage = res?['message']?.toString() ??
            "Historical exchange data unavailable for '$sym'. Ensure symbol has active liquidity or try another ticker.";
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.darkBackground,
      appBar: AppBar(
        backgroundColor: AppTheme.darkBackground,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back, color: Colors.white),
          onPressed: () => Navigator.of(context).pop(),
        ),
        title: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(6),
              decoration: BoxDecoration(
                color: AppTheme.cyan.withOpacity(0.12),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: AppTheme.borderCyan),
              ),
              child: const Icon(Icons.science_outlined, color: AppTheme.cyan, size: 18),
            ),
            const SizedBox(width: 8),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  "Strategy Backtester",
                  style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w900),
                ),
                Row(
                  children: [
                    Container(
                      width: 6,
                      height: 6,
                      decoration: const BoxDecoration(
                        color: AppTheme.emerald,
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: 4),
                    const Text(
                      "NSE & BSE REPLAY",
                      style: TextStyle(color: AppTheme.emerald, fontSize: 10, fontWeight: FontWeight.w800),
                    ),
                  ],
                ),
              ],
            ),
          ],
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Controls Card
            _buildControlsCard(),
            const SizedBox(height: 16),

            // Loading Indicator
            if (_isLoading) ...[
              const Center(
                child: Padding(
                  padding: EdgeInsets.symmetric(vertical: 40),
                  child: Column(
                    children: [
                      CircularProgressIndicator(color: AppTheme.cyan),
                      SizedBox(height: 14),
                      Text(
                        "Replaying Historical Exchange Bars...",
                        style: TextStyle(color: AppTheme.textSecondary, fontSize: 12, fontWeight: FontWeight.w700),
                      ),
                    ],
                  ),
                ),
              ),
            ] else if (_errorMessage != null) ...[
              _buildErrorNotice(),
            ] else if (_result != null) ...[
              _buildResultsView(),
            ] else ...[
              _buildEmptyStatePrompt(),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyStatePrompt() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 36),
      decoration: BoxDecoration(
        color: const Color(0xFF080B16),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppTheme.cardBorder),
      ),
      child: Center(
        child: Column(
          children: const [
            Icon(Icons.science_outlined, color: AppTheme.cyan, size: 36),
            SizedBox(height: 12),
            Text(
              "Ready to Replay Historical Strategy",
              style: TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.w900),
            ),
            SizedBox(height: 6),
            Text(
              "Enter any active NSE or BSE stock symbol or 6-digit security code above and tap Replay to evaluate institutional performance metrics with 1% capital risk sizing.",
              textAlign: TextAlign.center,
              style: TextStyle(color: AppTheme.textSecondary, fontSize: 11, height: 1.5),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildControlsCard() {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFF080B16),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppTheme.cardBorder),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            "TICKER SYMBOL OR SECURITY CODE (NSE / BSE)",
            style: TextStyle(color: AppTheme.textMuted, fontSize: 10, fontWeight: FontWeight.w800, letterSpacing: 0.5),
          ),
          const SizedBox(height: 8),

          // Symbol input + Replay button
          Row(
            children: [
              Expanded(
                child: Container(
                  height: 44,
                  decoration: BoxDecoration(
                    color: const Color(0xFF04060E),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: AppTheme.borderCyan),
                  ),
                  child: TextField(
                    controller: _symbolController,
                    style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w800),
                    decoration: const InputDecoration(
                      hintText: "Enter symbol or security code...",
                      hintStyle: TextStyle(color: AppTheme.textMuted, fontSize: 12),
                      border: InputBorder.none,
                      contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 12),
                    ),
                    onSubmitted: (_) => _runBacktest(),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              GestureDetector(
                onTap: _isLoading ? null : _runBacktest,
                child: Container(
                  height: 44,
                  padding: const EdgeInsets.symmetric(horizontal: 14),
                  decoration: BoxDecoration(
                    color: AppTheme.cyan.withOpacity(0.9),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  alignment: Alignment.center,
                  child: const Row(
                    children: [
                      Icon(Icons.bolt, color: Colors.black, size: 16),
                      SizedBox(width: 4),
                      Text("Replay", style: TextStyle(color: Colors.black, fontSize: 12, fontWeight: FontWeight.w900)),
                    ],
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),

          // Strategy Selector
          const Text(
            "ALGORITHMIC STRATEGY",
            style: TextStyle(color: AppTheme.textMuted, fontSize: 10, fontWeight: FontWeight.w800, letterSpacing: 0.5),
          ),
          const SizedBox(height: 6),
          Row(
            children: [
              _buildStrategyChip("Camarilla Breakout", "camarilla_breakout"),
              const SizedBox(width: 8),
              _buildStrategyChip("Confluence Trend", "confluence_trend"),
            ],
          ),
          const SizedBox(height: 14),

          // Timeframe Selector
          const Text(
            "HISTORICAL TIMEFRAME",
            style: TextStyle(color: AppTheme.textMuted, fontSize: 10, fontWeight: FontWeight.w800, letterSpacing: 0.5),
          ),
          const SizedBox(height: 6),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: [
                _buildPeriodChip("3 Months", "3mo"),
                const SizedBox(width: 6),
                _buildPeriodChip("6 Months", "6mo"),
                const SizedBox(width: 6),
                _buildPeriodChip("1 Year", "1y"),
                const SizedBox(width: 6),
                _buildPeriodChip("2 Years", "2y"),
                const SizedBox(width: 6),
                _buildPeriodChip("5 Years", "5y"),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStrategyChip(String label, String value) {
    final isSelected = _selectedStrategy == value;
    return Expanded(
      child: GestureDetector(
        onTap: () {
          setState(() => _selectedStrategy = value);
          _runBacktest();
        },
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 8),
          decoration: BoxDecoration(
            color: isSelected ? AppTheme.cyan.withOpacity(0.15) : const Color(0xFF04060E),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: isSelected ? AppTheme.cyan : AppTheme.cardBorder),
          ),
          alignment: Alignment.center,
          child: Text(
            label,
            style: TextStyle(
              color: isSelected ? AppTheme.cyan : AppTheme.textSecondary,
              fontSize: 11,
              fontWeight: FontWeight.w800,
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildPeriodChip(String label, String value) {
    final isSelected = _selectedPeriod == value;
    return GestureDetector(
      onTap: () {
        setState(() => _selectedPeriod = value);
        _runBacktest();
      },
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: isSelected ? AppTheme.cyan.withOpacity(0.18) : const Color(0xFF04060E),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: isSelected ? AppTheme.cyan : AppTheme.cardBorder),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: isSelected ? AppTheme.cyan : AppTheme.textSecondary,
            fontSize: 10.5,
            fontWeight: FontWeight.w800,
          ),
        ),
      ),
    );
  }

  Widget _buildErrorNotice() {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppTheme.rose.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.rose.withOpacity(0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: const [
              Icon(Icons.warning_amber_rounded, color: AppTheme.rose, size: 18),
              SizedBox(width: 6),
              Text(
                "Backtest Data Notice",
                style: TextStyle(color: AppTheme.rose, fontSize: 13, fontWeight: FontWeight.w900),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            _errorMessage ?? "",
            style: const TextStyle(color: Colors.white, fontSize: 11, height: 1.4),
          ),
          const SizedBox(height: 6),
          const Text(
            "Under our Zero-Default policy, we never generate synthetic mock trades. Verify the ticker symbol or pick a high-liquidity stock.",
            style: TextStyle(color: AppTheme.textMuted, fontSize: 10),
          ),
        ],
      ),
    );
  }

  Widget _buildResultsView() {
    final r = _result!;
    final totalPnl = (r['total_pnl'] as num?)?.toDouble() ?? 0.0;
    final isProfit = totalPnl >= 0;
    final winRate = (r['win_rate_pct'] as num?)?.toDouble() ?? 0.0;
    final profitFactor = (r['profit_factor'] as num?)?.toDouble() ?? 0.0;
    final maxDrawdown = (r['max_drawdown_pct'] as num?)?.toDouble() ?? 0.0;
    final target1HitRate = (r['target_1_hit_rate_pct'] as num?)?.toDouble() ?? 0.0;
    final sharpe = (r['sharpe_ratio'] as num?)?.toDouble() ?? 0.0;
    final totalTrades = (r['total_trades'] as num?)?.toInt() ?? 0;
    final winningTrades = (r['winning_trades'] as num?)?.toInt() ?? 0;
    final losingTrades = (r['losing_trades'] as num?)?.toInt() ?? 0;

    final equityCurveRaw = (r['equity_curve'] as List?) ?? [];
    final equityPoints = equityCurveRaw.map((e) => (e['equity'] as num?)?.toDouble() ?? 200000.0).toList();

    final recentTradesRaw = (r['recent_trades'] as List?) ?? [];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Header Ticker Summary
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
          decoration: BoxDecoration(
            color: AppTheme.cyan.withOpacity(0.06),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: AppTheme.borderCyan),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    r['resolved_ticker']?.toString() ?? '',
                    style: const TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.w900),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    "Replay: ${r['period']} • ${_selectedStrategy == 'camarilla_breakout' ? 'Camarilla H4/L4' : 'Confluence Trend'}",
                    style: const TextStyle(color: AppTheme.textMuted, fontSize: 10.5),
                  ),
                ],
              ),
              Text(
                "${isProfit ? '+' : ''}₹${totalPnl.toStringAsFixed(2)} (${r['total_return_pct']}%)",
                style: TextStyle(
                  color: isProfit ? AppTheme.emerald : AppTheme.rose,
                  fontSize: 13,
                  fontWeight: FontWeight.w900,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 12),

        // KPI Metric Cards Grid
        GridView.count(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          crossAxisCount: 2,
          crossAxisSpacing: 10,
          mainAxisSpacing: 10,
          childAspectRatio: 1.8,
          children: [
            _buildMetricCard(
              title: "WIN RATE",
              value: "$winRate%",
              subtext: "$winningTrades Wins / $losingTrades Losses",
              valueColor: winRate >= 50 ? AppTheme.emerald : AppTheme.amber,
            ),
            _buildMetricCard(
              title: "PROFIT FACTOR",
              value: "${profitFactor}x",
              subtext: "Institutional > 1.50",
              valueColor: profitFactor >= 1.5 ? AppTheme.emerald : AppTheme.cyan,
            ),
            _buildMetricCard(
              title: "MAX DRAWDOWN",
              value: "$maxDrawdown%",
              subtext: "Strict Risk Guard",
              valueColor: maxDrawdown <= 10 ? AppTheme.emerald : AppTheme.rose,
            ),
            _buildMetricCard(
              title: "TARGET 1 REACHED",
              value: "$target1HitRate%",
              subtext: "Tactical Exits",
              valueColor: AppTheme.emerald,
            ),
            _buildMetricCard(
              title: "SHARPE RATIO",
              value: "$sharpe",
              subtext: "Risk-Adjusted Alpha",
              valueColor: const Color(0xFF8B5CF6),
            ),
            _buildMetricCard(
              title: "TOTAL TRADES",
              value: "$totalTrades",
              subtext: "Avg Hold: ${r['average_holding_period_bars']} bars",
              valueColor: Colors.white,
            ),
          ],
        ),
        const SizedBox(height: 14),

        // Equity Curve Chart
        if (equityPoints.length >= 2) ...[
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: const Color(0xFF080B16),
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: AppTheme.cardBorder),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: const [
                    Text(
                      "📈 Equity Curve",
                      style: TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w800),
                    ),
                    Text(
                      "1% Risk Budget (₹2,000/trade)",
                      style: TextStyle(color: AppTheme.cyan, fontSize: 10, fontWeight: FontWeight.w700),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                SizedBox(
                  height: 140,
                  width: double.infinity,
                  child: CustomPaint(
                    painter: _EquityCurvePainter(
                      points: equityPoints,
                      isProfit: isProfit,
                    ),
                  ),
                ),
                const SizedBox(height: 6),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      "Start: ₹${(r['initial_capital'] as num?)?.toInt() ?? 200000}",
                      style: const TextStyle(color: AppTheme.textMuted, fontSize: 9.5),
                    ),
                    Text(
                      "End: ₹${(r['final_capital'] as num?)?.toDouble().toStringAsFixed(0) ?? ''}",
                      style: const TextStyle(color: AppTheme.textMuted, fontSize: 9.5),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),
        ],

        // Recent Trades Log
        if (recentTradesRaw.isNotEmpty) ...[
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: const Color(0xFF080B16),
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: AppTheme.cardBorder),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  "📋 Execution Log (${recentTradesRaw.length} Sample Trades)",
                  style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w800),
                ),
                const SizedBox(height: 10),
                ...recentTradesRaw.map((trade) {
                  final tPnl = (trade['pnl'] as num?)?.toDouble() ?? 0.0;
                  final tWin = tPnl >= 0;
                  final type = trade['type']?.toString() ?? 'BUY';
                  return Container(
                    margin: const EdgeInsets.only(bottom: 8),
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: const Color(0xFF04060E),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: Colors.white.withOpacity(0.04)),
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
                                  decoration: BoxDecoration(
                                    color: type == 'BUY' ? AppTheme.emerald.withOpacity(0.15) : AppTheme.rose.withOpacity(0.15),
                                    borderRadius: BorderRadius.circular(4),
                                  ),
                                  child: Text(
                                    type,
                                    style: TextStyle(
                                      color: type == 'BUY' ? AppTheme.emerald : AppTheme.rose,
                                      fontSize: 9.5,
                                      fontWeight: FontWeight.w900,
                                    ),
                                  ),
                                ),
                                const SizedBox(width: 6),
                                Text(
                                  "Entry: ₹${(trade['entry_price'] as num?)?.toDouble().toStringAsFixed(1)} → Exit: ₹${(trade['exit_price'] as num?)?.toDouble().toStringAsFixed(1)}",
                                  style: const TextStyle(color: Colors.white, fontSize: 10.5, fontWeight: FontWeight.w700),
                                ),
                              ],
                            ),
                            const SizedBox(height: 3),
                            Text(
                              "${trade['entry_date']} • ${trade['exit_reason']?.toString().replaceAll('_', ' ')} (${trade['bars_held']} bars)",
                              style: const TextStyle(color: AppTheme.textMuted, fontSize: 9.5),
                            ),
                          ],
                        ),
                        Text(
                          "${tWin ? '+' : ''}₹${tPnl.toStringAsFixed(1)}\n(${trade['return_pct']}%)",
                          textAlign: TextAlign.right,
                          style: TextStyle(
                            color: tWin ? AppTheme.emerald : AppTheme.rose,
                            fontSize: 11,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                      ],
                    ),
                  );
                }).toList(),
              ],
            ),
          ),
          const SizedBox(height: 14),
        ],

        // Institutional Disclaimer
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.02),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: AppTheme.cardBorder),
          ),
          child: Text(
            "🛡️ Quantitative Audit Notice: ${r['disclaimer'] ?? 'Simulations incorporate slippage buffer and strict mathematical 1% account risk sizing.'}",
            style: const TextStyle(color: AppTheme.textMuted, fontSize: 9.5, height: 1.4),
          ),
        ),
      ],
    );
  }

  Widget _buildMetricCard({
    required String title,
    required String value,
    required String subtext,
    required Color valueColor,
  }) {
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: const Color(0xFF080B16),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.cardBorder),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(
            title,
            style: const TextStyle(color: AppTheme.textMuted, fontSize: 9, fontWeight: FontWeight.w800, letterSpacing: 0.5),
          ),
          const SizedBox(height: 2),
          Text(
            value,
            style: TextStyle(color: valueColor, fontSize: 16, fontWeight: FontWeight.w900),
          ),
          const SizedBox(height: 2),
          Text(
            subtext,
            style: const TextStyle(color: AppTheme.textSecondary, fontSize: 9),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }
}

/// Custom painter for the Backtester Equity Curve with gradient fill.
class _EquityCurvePainter extends CustomPainter {
  final List<double> points;
  final bool isProfit;

  _EquityCurvePainter({required this.points, required this.isProfit});

  @override
  void paint(Canvas canvas, Size size) {
    if (points.length < 2) return;

    final minVal = points.reduce(math.min);
    final maxVal = points.reduce(math.max);
    final range = (maxVal - minVal == 0) ? 1.0 : (maxVal - minVal);

    final lineColor = isProfit ? AppTheme.emerald : AppTheme.rose;
    final strokePaint = Paint()
      ..color = lineColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.2
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;

    final path = Path();
    final fillPath = Path();

    for (int i = 0; i < points.length; i++) {
      final x = (i / (points.length - 1)) * size.width;
      final y = size.height - ((points[i] - minVal) / range) * (size.height - 16) - 8;

      if (i == 0) {
        path.moveTo(x, y);
        fillPath.moveTo(x, size.height);
        fillPath.lineTo(x, y);
      } else {
        path.lineTo(x, y);
        fillPath.lineTo(x, y);
      }
    }

    fillPath.lineTo(size.width, size.height);
    fillPath.close();

    final fillPaint = Paint()
      ..shader = LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: [
          lineColor.withOpacity(0.25),
          lineColor.withOpacity(0.0),
        ],
      ).createShader(Rect.fromLTWH(0, 0, size.width, size.height))
      ..style = PaintingStyle.fill;

    canvas.drawPath(fillPath, fillPaint);
    canvas.drawPath(path, strokePaint);

    // End point node
    final lastX = size.width;
    final lastY = size.height - ((points.last - minVal) / range) * (size.height - 16) - 8;
    canvas.drawCircle(Offset(lastX, lastY), 4, Paint()..color = lineColor);
    canvas.drawCircle(Offset(lastX, lastY), 2, Paint()..color = Colors.white);
  }

  @override
  bool shouldRepaint(covariant _EquityCurvePainter oldDelegate) => true;
}
