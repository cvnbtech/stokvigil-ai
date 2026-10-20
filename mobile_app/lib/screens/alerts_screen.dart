import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import '../config/theme.dart';
import '../models/models.dart';
import '../providers/alerts_provider.dart';
import '../services/api_service.dart';
import '../services/supabase_service.dart';
import '../widgets/custom_widgets.dart';
import '../widgets/candle_chart_modal.dart';
import 'candle_chart_screen.dart';
import 'audit_ledger_screen.dart';
import 'backtest_screen.dart';

class AlertsScreen extends StatefulWidget {
  const AlertsScreen({super.key});

  @override
  State<AlertsScreen> createState() => _AlertsScreenState();
}

class _AlertsScreenState extends State<AlertsScreen> {
  final Set<String> _expandedRadarIds = {};

  String get _selectedFilter => context.read<AlertsProvider>().selectedFilter;

  void _shareAlphaCard(StokAlert alert, String targetStr, String slStr, String rrStr) {
    final shareText = '''⚡ STOKVIGIL AI ALPHA SIGNAL ⚡

🎯 Symbol: #${alert.cleanSymbol} (${alert.exchange})
📈 Confluence Score: ${alert.impactScore}/100
🔥 Catalyst: ${alert.catalystType}

🎯 Target: $targetStr
🛡️ Stop Loss: $slStr
⚖️ R:R Ratio: $rrStr

Key Insights:
${alert.factualReasons.take(2).map((r) => '• $r').join('\n')}

Automated surveillance via StokVigil AI 🛡️''';

    showModalBottomSheet(
      context: context,
      backgroundColor: const Color(0xFF080B16),
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
      builder: (ctx) => Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text("1-TAP SHAREABLE ALPHA", style: TextStyle(fontSize: 10, fontWeight: FontWeight.w900, color: AppTheme.cyan)),
                    Row(
                      children: [
                        Text(alert.cleanSymbol, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w900, color: Colors.white)),
                        const SizedBox(width: 8),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                          decoration: BoxDecoration(
                            color: alert.exchange == 'BSE' ? const Color(0xFFF59E0B).withOpacity(0.15) : AppTheme.cyan.withOpacity(0.15),
                            borderRadius: BorderRadius.circular(4),
                            border: Border.all(color: alert.exchange == 'BSE' ? const Color(0xFFF59E0B) : AppTheme.cyan, width: 0.8),
                          ),
                          child: Text(
                            alert.exchange,
                            style: TextStyle(
                              color: alert.exchange == 'BSE' ? const Color(0xFFF59E0B) : AppTheme.cyan,
                              fontWeight: FontWeight.bold,
                              fontSize: 10,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: const Color(0xFF10B981).withOpacity(0.15),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: const Color(0xFF10B981)),
                  ),
                  child: Text(alert.impactScore > 0 ? "${alert.impactScore}/100 SCORE" : "-- SCORE", style: const TextStyle(color: Color(0xFF10B981), fontWeight: FontWeight.bold, fontSize: 11)),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(alert.alertTitle, style: const TextStyle(color: AppTheme.textPrimary, fontSize: 12.5, fontWeight: FontWeight.w600)),
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF10B981),
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                  padding: const EdgeInsets.symmetric(vertical: 12),
                ),
                onPressed: () {
                  Clipboard.setData(ClipboardData(text: shareText));
                  Navigator.pop(ctx);
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                      content: Text("✅ Alpha Card copied! Ready to paste on WhatsApp or Twitter/X."),
                      backgroundColor: Color(0xFF10B981),
                    ),
                  );
                },
                icon: const Icon(Icons.copy, size: 16),
                label: const Text("Copy Signal for WhatsApp / Twitter", style: TextStyle(fontWeight: FontWeight.bold)),
              ),
            ),
            const SizedBox(height: 10),
          ],
        ),
      ),
    );
  }

  Future<void> _refreshAlerts() async {
    final user = SupabaseService().currentUser;
    if (user != null) {
      await context.read<AlertsProvider>().fetchAlertsFallback(user.id);
    }
  }

  String _getSignalLabel(StokAlert alert) {
    final bias = alert.actionBias.toUpperCase();
    if (bias.contains('CAPITAL_PRESERVATION') || bias.contains('CAPITAL PRESERVATION')) {
      return 'CAPITAL PRESERVATION EXIT';
    }
    if (bias.contains('MIS_SHORT') || bias.contains('INTRADAY_MIS') || bias.contains('MIS SHORT')) {
      return 'INTRADAY MIS SHORT';
    }
    if (bias.contains('BUY') || bias.contains('ACCUMULATE')) return 'ACCUMULATE / BUY';
    if (bias.contains('SELL')) return 'PROFIT BOOK / SELL';
    if (bias.contains('TRAILING')) return 'TRAILING SL TRIGGER';
    
    final cat = alert.catalystType.toUpperCase();
    final title = alert.alertTitle.toUpperCase();
    if (cat.contains('VOLUME') || title.contains('VOLUME')) return 'VOLUME SURGE';
    if (cat.contains('BREAKOUT') || title.contains('BREAKOUT')) return 'BREAKOUT SIGNAL';
    if (cat.contains('EARNING') || title.contains('EARNING')) return 'EARNINGS BEAT';
    if (alert.impactScore >= 80) return 'STRONG BUY';
    return 'WATCH SIGNAL';
  }

  String _getSignalType(StokAlert alert) {
    final bias = alert.actionBias.toUpperCase();
    if (bias.contains('CAPITAL_PRESERVATION') || bias.contains('CAPITAL PRESERVATION')) {
      return 'capital_preservation_exit';
    }
    if (bias.contains('MIS_SHORT') || bias.contains('INTRADAY_MIS') || bias.contains('MIS SHORT')) {
      return 'intraday_mis_short';
    }
    if (bias.contains('BUY') || bias.contains('ACCUMULATE')) return 'strong_buy';
    if (bias.contains('SELL')) return 'sell';
    if (bias.contains('TRAILING')) return 'med';
    
    final cat = alert.catalystType.toUpperCase();
    if (cat.contains('VOLUME')) return 'volume';
    if (cat.contains('BREAKOUT')) return 'breakout';
    if (alert.impactScore >= 80) return 'strong_buy';
    return 'buy';
  }

  @override
  Widget build(BuildContext context) {
    final alertsProvider = context.watch<AlertsProvider>();
    final _isLoading = alertsProvider.isLoading;
    final _selectedFilter = alertsProvider.selectedFilter;
    final filteredList = alertsProvider.filteredAlerts;

    return Scaffold(
      backgroundColor: AppTheme.darkBackground,
      appBar: AppBar(
        backgroundColor: AppTheme.darkBackground,
        elevation: 0,
        title: const StokVigilBrandHeader(),
        actions: [
          IconButton(
            onPressed: () {
              Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const BacktestScreen()),
              );
            },
            icon: const Icon(Icons.science_outlined, color: AppTheme.cyan),
            tooltip: "Strategy Backtester",
          ),
          IconButton(
            onPressed: () {
              Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const AuditLedgerScreen()),
              );
            },
            icon: const Icon(Icons.verified_outlined, color: AppTheme.primaryEmerald),
            tooltip: "Public Audit Ledger",
          ),
          IconButton(onPressed: _refreshAlerts, icon: const Icon(Icons.refresh, color: AppTheme.cyan)),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _refreshAlerts,
        color: AppTheme.cyan,
        child: Column(
          children: [
            // Filter Chip Bar
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              child: Row(
                children: [
                  _buildFilterChip('all', '⚡ All Alerts', _selectedFilter),
                  _buildFilterChip('defense', '🛡️ Capital Defense', _selectedFilter),
                  _buildFilterChip('high', '🔥 High Impact', _selectedFilter),
                  _buildFilterChip('trailing', '🟡 Trailing SL', _selectedFilter),
                  _buildFilterChip('earnings', '📈 Earnings', _selectedFilter),
                  _buildFilterChip('breakout', '🚀 Breakout', _selectedFilter),
                  _buildFilterChip('volume', '⚡ Volume Surge', _selectedFilter),
                  _buildFilterChip('fii', '📊 FII / Deals', _selectedFilter),
                ],
              ),
            ),

            Expanded(
              child: _isLoading
                  ? const Center(child: CircularProgressIndicator(color: AppTheme.cyan))
                  : filteredList.isEmpty
                      ? Center(
                          child: Padding(
                            padding: const EdgeInsets.all(32.0),
                            child: Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: const [
                                Icon(Icons.radar_outlined, color: AppTheme.textSecondary, size: 64),
                                SizedBox(height: 16),
                                Text("No High-Impact Catalysts Yet", style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold)),
                                SizedBox(height: 8),
                                Text(
                                  "StokVigil scans your ICICI portfolio every 5 mins during Indian market hours. Noise is filtered out automatically.",
                                  textAlign: TextAlign.center,
                                  style: TextStyle(color: AppTheme.textSecondary, fontSize: 13),
                                ),
                              ],
                            ),
                          ),
                        )
                      : ListView.builder(
                          padding: const EdgeInsets.all(16),
                          itemCount: filteredList.length,
                          itemBuilder: (context, index) {
                            final alert = filteredList[index];
                            final isHigh = alert.impactScore >= 80;
                            final dateStr = DateFormat('dd MMM, hh:mm a').format(alert.createdAt);
                            
                            // Resolve effective stock price from metricsSnapshot or Demat position
                            num effectivePrice = 0.0;
                            if (alert.metricsSnapshot['current_price'] != null && (alert.metricsSnapshot['current_price'] as num) > 0) {
                              effectivePrice = alert.metricsSnapshot['current_price'] as num;
                            } else if (alert.metricsSnapshot['price'] != null && (alert.metricsSnapshot['price'] as num) > 0) {
                              effectivePrice = alert.metricsSnapshot['price'] as num;
                            } else if (alert.metricsSnapshot['financials'] is Map && alert.metricsSnapshot['financials']['price'] != null && (alert.metricsSnapshot['financials']['price'] as num) > 0) {
                              effectivePrice = alert.metricsSnapshot['financials']['price'] as num;
                            } else if (alert.dematPosition != null && alert.dematPosition!['average_buy_price'] != null && (alert.dematPosition!['average_buy_price'] as num) > 0) {
                              effectivePrice = alert.dematPosition!['average_buy_price'] as num;
                            }

                            final signalLabel = _getSignalLabel(alert);
                            final signalType = _getSignalType(alert);
                            final isCapExit = signalType == 'capital_preservation_exit' || alert.actionBias.toUpperCase().contains('CAPITAL_PRESERVATION');
                            final isMisShort = signalType == 'intraday_mis_short' || alert.actionBias.toUpperCase().contains('MIS_SHORT');
                            
                            // Sanitize dummy ₹100.00 fallback from historical database alerts
                            final isDummy100 = (alert.target1 == "₹100.00" || alert.target1 == "100.0" || alert.target1 == "100" || alert.target1 == "-") && 
                                               (alert.stopLoss == "₹100.00" || alert.stopLoss == "100.0" || alert.stopLoss == "100" || alert.stopLoss == "-");

                            final String targetStr;
                            final String slStr;
                            if (isDummy100 || alert.target1 == null || alert.target1 == "-" || alert.target1 == "₹0" || alert.target1 == "0") {
                              targetStr = "--";
                            } else {
                              targetStr = alert.target1!;
                            }

                            if (isDummy100 || alert.stopLoss == null || alert.stopLoss == "-" || alert.stopLoss == "₹0" || alert.stopLoss == "0") {
                              slStr = "--";
                            } else {
                              slStr = alert.stopLoss!;
                            }

                            final rrStr = (isDummy100 || alert.riskReward == null || alert.riskReward == "-" || alert.riskReward == "0") ? "--" : alert.riskReward!;

                            return GlassCard(
                              margin: const EdgeInsets.only(bottom: 16),
                              borderColor: isCapExit
                                  ? AppTheme.dangerRose
                                  : isMisShort
                                      ? AppTheme.secondaryAmber
                                      : (isHigh ? AppTheme.borderCyan : AppTheme.cardBorder),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  // Top Badge Row
                                  Row(
                                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                    crossAxisAlignment: CrossAxisAlignment.center,
                                    children: [
                                      Flexible(
                                        child: Wrap(
                                          spacing: 6,
                                          runSpacing: 4,
                                          children: [
                                            SignalBadge(
                                              label: signalLabel,
                                              type: signalType,
                                            ),
                                            if (alert.impactScore > 0)
                                              SignalBadge(
                                                label: "${alert.impactScore}/100 SCORE",
                                                type: isHigh ? 'high' : 'med',
                                              ),
                                          ],
                                        ),
                                      ),
                                      const SizedBox(width: 8),
                                      Text(
                                        dateStr,
                                        style: const TextStyle(color: AppTheme.textMuted, fontSize: 10, fontWeight: FontWeight.bold),
                                      ),
                                    ],
                                  ),
                                  const SizedBox(height: 12),

                                  // Symbol & Title
                                  Row(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
                                        margin: const EdgeInsets.only(right: 6, top: 1),
                                        decoration: BoxDecoration(
                                          color: alert.exchange == 'BSE' ? const Color(0xFFF59E0B).withOpacity(0.15) : AppTheme.cyan.withOpacity(0.12),
                                          borderRadius: BorderRadius.circular(4),
                                          border: Border.all(color: alert.exchange == 'BSE' ? const Color(0xFFF59E0B) : AppTheme.cyan, width: 0.8),
                                        ),
                                        child: Text(
                                          alert.exchange,
                                          style: TextStyle(
                                            color: alert.exchange == 'BSE' ? const Color(0xFFF59E0B) : AppTheme.cyan,
                                            fontWeight: FontWeight.w900,
                                            fontSize: 9,
                                          ),
                                        ),
                                      ),
                                      Expanded(
                                        child: RichText(
                                          text: TextSpan(
                                            children: [
                                              TextSpan(
                                                text: "[${alert.cleanSymbol}] ",
                                                style: TextStyle(
                                                  color: alert.exchange == 'BSE' ? const Color(0xFFF59E0B) : AppTheme.cyan,
                                                  fontWeight: FontWeight.w900,
                                                  fontSize: 14.5,
                                                ),
                                              ),
                                              TextSpan(
                                                text: alert.alertTitle,
                                                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 14, height: 1.3),
                                              ),
                                            ],
                                          ),
                                        ),
                                      ),
                                    ],
                                  ),
                                  const SizedBox(height: 12),

                                  // Capital Preservation Exit High-Urgency Defense Box
                                  if (isCapExit) ...[
                                    Container(
                                      padding: const EdgeInsets.all(10),
                                      margin: const EdgeInsets.only(bottom: 12),
                                      decoration: BoxDecoration(
                                        color: AppTheme.dangerRose.withOpacity(0.12),
                                        borderRadius: BorderRadius.circular(10),
                                        border: Border.all(color: AppTheme.dangerRose.withOpacity(0.5), width: 1.2),
                                      ),
                                      child: Row(
                                        crossAxisAlignment: CrossAxisAlignment.start,
                                        children: [
                                          const Icon(Icons.shield, color: AppTheme.dangerRose, size: 20),
                                          const SizedBox(width: 10),
                                          Expanded(
                                            child: Column(
                                              crossAxisAlignment: CrossAxisAlignment.start,
                                              children: const [
                                                Text(
                                                  "CRITICAL: CAPITAL PRESERVATION DEFENSE",
                                                  style: TextStyle(
                                                    color: AppTheme.dangerRose,
                                                    fontSize: 11.5,
                                                    fontWeight: FontWeight.w900,
                                                    letterSpacing: 0.3,
                                                  ),
                                                ),
                                                SizedBox(height: 3),
                                                Text(
                                                  "Severe breakdown detected below tactical support / 200 EMA with supply shock. Standard hold rules overridden to protect invested principal.",
                                                  style: TextStyle(
                                                    color: Colors.white,
                                                    fontSize: 11,
                                                    height: 1.35,
                                                  ),
                                                ),
                                              ],
                                            ),
                                          ),
                                        ],
                                      ),
                                    ),
                                  ],

                                  // SEBI Regulatory Auto-Square-off Warning Box
                                  if (isMisShort) ...[
                                    Container(
                                      padding: const EdgeInsets.all(10),
                                      margin: const EdgeInsets.only(bottom: 12),
                                      decoration: BoxDecoration(
                                        color: AppTheme.secondaryAmber.withOpacity(0.12),
                                        borderRadius: BorderRadius.circular(10),
                                        border: Border.all(color: AppTheme.secondaryAmber.withOpacity(0.5), width: 1.2),
                                      ),
                                      child: Row(
                                        crossAxisAlignment: CrossAxisAlignment.start,
                                        children: [
                                          const Icon(Icons.warning_amber_rounded, color: AppTheme.secondaryAmber, size: 20),
                                          const SizedBox(width: 10),
                                          Expanded(
                                            child: Column(
                                              crossAxisAlignment: CrossAxisAlignment.start,
                                              children: const [
                                                Text(
                                                  "STATUTORY NOTICE: INTRADAY MIS SHORT (SEBI RMS)",
                                                  style: TextStyle(
                                                    color: AppTheme.secondaryAmber,
                                                    fontSize: 11.5,
                                                    fontWeight: FontWeight.w900,
                                                    letterSpacing: 0.3,
                                                  ),
                                                ),
                                                SizedBox(height: 3),
                                                Text(
                                                  "Intraday Margin Intraday Square-off (MIS) setup. SEBI & Broker RMS mandate compulsory auto-square-off at 03:15 PM IST today. Positions not closed will be liquidated at market rate.",
                                                  style: TextStyle(
                                                    color: Colors.white,
                                                    fontSize: 11,
                                                    height: 1.35,
                                                  ),
                                                ),
                                              ],
                                            ),
                                          ),
                                        ],
                                      ),
                                    ),
                                  ],

                                  // Demat Position Banner (if user holds stock)
                                  if (alert.dematPosition != null) ...[
                                    Builder(
                                      builder: (context) {
                                        final demat = alert.dematPosition!;
                                        final qty = demat['quantity'] ?? 0;
                                        final avgPrice = (demat['average_buy_price'] as num?)?.toDouble() ?? 0.0;
                                        num rawPnl = (demat['unrealized_pnl_pct'] as num?) ?? 0.0;
                                        // Sanitize false -100% loss caused by missing live price during off-market alerts
                                        if (rawPnl <= -99.0) {
                                          if (effectivePrice > 0 && avgPrice > 0) {
                                            rawPnl = ((effectivePrice - avgPrice) / avgPrice) * 100;
                                          } else {
                                            rawPnl = 0.0;
                                          }
                                        }
                                        final pnlFormatted = "${rawPnl >= 0 ? '+' : ''}${rawPnl.toStringAsFixed(1)}%";

                                        return Container(
                                          padding: const EdgeInsets.all(10),
                                          margin: const EdgeInsets.only(bottom: 12),
                                          decoration: BoxDecoration(
                                            color: AppTheme.primaryEmerald.withOpacity(0.08),
                                            borderRadius: BorderRadius.circular(10),
                                            border: Border.all(color: AppTheme.primaryEmerald.withOpacity(0.3)),
                                          ),
                                          child: Row(
                                            children: [
                                              const Icon(Icons.account_balance_wallet, color: AppTheme.primaryEmerald, size: 16),
                                              const SizedBox(width: 8),
                                              Expanded(
                                                child: Text(
                                                  "ICICI Demat: $qty Qty @ Avg ₹${avgPrice.toStringAsFixed(1)} (P&L: $pnlFormatted)",
                                                  style: const TextStyle(color: Colors.white, fontSize: 11.5, fontWeight: FontWeight.bold),
                                                ),
                                              ),
                                            ],
                                          ),
                                        );
                                      },
                                    ),
                                  ],

                                  // Factual Catalyst Bullet Points
                                  ...alert.factualReasons.map((reason) => Padding(
                                        padding: const EdgeInsets.only(bottom: 6.0),
                                        child: Row(
                                          crossAxisAlignment: CrossAxisAlignment.start,
                                          children: [
                                            const Text("• ", style: TextStyle(color: AppTheme.cyan, fontWeight: FontWeight.w900, fontSize: 14)),
                                            Expanded(
                                              child: Text(
                                                reason,
                                                style: const TextStyle(color: AppTheme.textSecondary, fontSize: 12, height: 1.4),
                                              ),
                                            ),
                                          ],
                                        ),
                                      )),
                                  const SizedBox(height: 12),

                                  // Tactical Target & Stop Loss Box
                                  Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                                    decoration: BoxDecoration(
                                      color: AppTheme.cyan.withOpacity(0.06),
                                      borderRadius: BorderRadius.circular(10),
                                      border: Border.all(color: AppTheme.cyan.withOpacity(0.2)),
                                    ),
                                    child: Wrap(
                                      alignment: WrapAlignment.spaceBetween,
                                      runSpacing: 4,
                                      spacing: 12,
                                      children: [
                                        Text("🎯 Target 1: $targetStr", style: const TextStyle(color: AppTheme.primaryEmerald, fontSize: 11, fontWeight: FontWeight.w900)),
                                        Text("🛡️ Stop Loss: $slStr", style: const TextStyle(color: AppTheme.dangerRose, fontSize: 11, fontWeight: FontWeight.w900)),
                                        Text("⚖️ R:R: $rrStr", style: const TextStyle(color: AppTheme.cyan, fontSize: 11, fontWeight: FontWeight.bold)),
                                      ],
                                    ),
                                  ),
                                  const SizedBox(height: 10),

                                  // Fundamental Metrics Grid
                                  MetricChipStrip(metrics: alert.metricsSnapshot),
                                  const SizedBox(height: 10),

                                  // Visual 4-Pillar Confluence Spider / Radar Section (Only shown if real factors exist)
                                  if (alert.factorBreakdown != null) ...[
                                    SizedBox(
                                      width: double.infinity,
                                      child: OutlinedButton.icon(
                                        style: OutlinedButton.styleFrom(
                                          side: BorderSide(
                                            color: _expandedRadarIds.contains(alert.id) ? AppTheme.cyan : AppTheme.cardBorder,
                                          ),
                                          backgroundColor: _expandedRadarIds.contains(alert.id)
                                              ? AppTheme.cyan.withOpacity(0.08)
                                              : Colors.transparent,
                                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                                        ),
                                        onPressed: () {
                                          setState(() {
                                            if (_expandedRadarIds.contains(alert.id)) {
                                              _expandedRadarIds.remove(alert.id);
                                            } else {
                                              _expandedRadarIds.add(alert.id);
                                            }
                                          });
                                        },
                                        icon: const Icon(Icons.hub_outlined, size: 14, color: AppTheme.cyan),
                                        label: Text(
                                          _expandedRadarIds.contains(alert.id)
                                              ? "Hide 4-Pillar Confluence Radar ▲"
                                              : "View 4-Pillar Confluence Radar ▼",
                                          style: const TextStyle(color: AppTheme.cyan, fontSize: 11, fontWeight: FontWeight.bold),
                                        ),
                                      ),
                                    ),
                                    if (_expandedRadarIds.contains(alert.id)) ...[
                                      const SizedBox(height: 8),
                                      Container(
                                        width: double.infinity,
                                        padding: const EdgeInsets.all(12),
                                        decoration: BoxDecoration(
                                          color: const Color(0xFF080B16),
                                          borderRadius: BorderRadius.circular(14),
                                          border: Border.all(color: AppTheme.cardBorder),
                                        ),
                                        child: ConfluenceRadarChart(factors: alert.factorBreakdown!, size: 150),
                                      ),
                                    ],
                                    const SizedBox(height: 12),
                                  ],

                                  // Action Buttons Grid: Candles & Camarilla + Share Alpha Card
                                  Row(
                                    children: [
                                      Expanded(
                                        child: OutlinedButton.icon(
                                          style: OutlinedButton.styleFrom(
                                            side: const BorderSide(color: AppTheme.borderCyan),
                                            backgroundColor: AppTheme.cyan.withOpacity(0.08),
                                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                                            padding: const EdgeInsets.symmetric(vertical: 10),
                                          ),
                                          onPressed: () {
                                            CandleChartModal.show(context, symbol: alert.symbol);
                                          },
                                          onLongPress: () {
                                            Navigator.of(context).push(
                                              MaterialPageRoute(
                                                builder: (_) => CandleChartScreen(symbol: alert.symbol),
                                              ),
                                            );
                                          },
                                          icon: const Text("📊", style: TextStyle(fontSize: 13)),
                                          label: const Text(
                                            "Candles & Camarilla",
                                            style: TextStyle(color: AppTheme.cyan, fontWeight: FontWeight.w900, fontSize: 11),
                                          ),
                                        ),
                                      ),
                                      const SizedBox(width: 8),
                                      Expanded(
                                        child: OutlinedButton.icon(
                                          style: OutlinedButton.styleFrom(
                                            side: const BorderSide(color: Color(0xFF10B981)),
                                            backgroundColor: const Color(0xFF10B981).withOpacity(0.08),
                                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                                            padding: const EdgeInsets.symmetric(vertical: 10),
                                          ),
                                          onPressed: () => _shareAlphaCard(alert, targetStr, slStr, rrStr),
                                          icon: const Icon(Icons.share, size: 14, color: Color(0xFF10B981)),
                                          label: const Text(
                                            "Share Alpha Card",
                                            style: TextStyle(color: Color(0xFF10B981), fontWeight: FontWeight.w900, fontSize: 11),
                                          ),
                                        ),
                                      ),
                                    ],
                                  ),
                                  const SizedBox(height: 8),

                                  // 1-Tap Trade Trigger CTA Button
                                  SizedBox(
                                    width: double.infinity,
                                    child: OutlinedButton(
                                      style: OutlinedButton.styleFrom(
                                        side: const BorderSide(color: AppTheme.borderCyan),
                                        backgroundColor: AppTheme.cyan.withOpacity(0.08),
                                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                                        padding: const EdgeInsets.symmetric(vertical: 10),
                                      ),
                                      onPressed: () {
                                        TradeOrderModal.show(
                                          context,
                                          symbol: alert.symbol,
                                          currentPrice: effectivePrice.toDouble(),
                                          initialType: alert.actionBias.contains('SELL') ? 'SELL' : 'BUY',
                                          targetPrice: (targetStr == '--' || targetStr == '-' || targetStr == '₹0') ? '' : targetStr.replaceAll('₹', '').trim(),
                                          stopLoss: (slStr == '--' || slStr == '-' || slStr == '₹0') ? '' : slStr.replaceAll('₹', '').trim(),
                                        );
                                      },
                                      child: Row(
                                        mainAxisAlignment: MainAxisAlignment.center,
                                        children: [
                                          Text(
                                            alert.actionBias.contains('SELL') ? "⚡ 1-Tap Profit Booking Order" : "⚡ 1-Tap ICICI Trade Execution",
                                            style: const TextStyle(color: AppTheme.cyan, fontWeight: FontWeight.w900, fontSize: 12),
                                          ),
                                        ],
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            );
                          },
                        ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildFilterChip(String filterKey, String label, [String? currentFilter]) {
    final active = (currentFilter ?? _selectedFilter) == filterKey;
    return GestureDetector(
      onTap: () => context.read<AlertsProvider>().setFilter(filterKey),
      child: Container(
        margin: const EdgeInsets.only(right: 8),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
        decoration: BoxDecoration(
          color: active ? AppTheme.cyan.withOpacity(0.15) : AppTheme.cardBackground,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: active ? AppTheme.cyan : AppTheme.cardBorder,
            width: active ? 1.5 : 1,
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: active ? AppTheme.cyan : AppTheme.textSecondary,
            fontWeight: active ? FontWeight.w900 : FontWeight.w600,
            fontSize: 11.5,
          ),
        ),
      ),
    );
  }
}
