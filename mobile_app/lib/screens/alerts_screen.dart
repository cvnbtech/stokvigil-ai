import 'dart:async';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../config/theme.dart';
import '../models/models.dart';
import '../services/api_service.dart';
import '../services/supabase_service.dart';
import '../widgets/custom_widgets.dart';

class AlertsScreen extends StatefulWidget {
  const AlertsScreen({super.key});

  @override
  State<AlertsScreen> createState() => _AlertsScreenState();
}

class _AlertsScreenState extends State<AlertsScreen> {
  bool _isLoading = true;
  String _selectedFilter = 'all';
  List<StokAlert> _alerts = [];
  StreamSubscription<List<StokAlert>>? _alertsSub;

  @override
  void initState() {
    super.initState();
    _loadAlerts();
    _subscribeToAlerts();
  }

  @override
  void dispose() {
    _alertsSub?.cancel();
    super.dispose();
  }

  void _subscribeToAlerts() {
    _alertsSub = SupabaseService().streamAlerts().listen((liveAlerts) {
      if (mounted && liveAlerts.isNotEmpty) {
        setState(() {
          _alerts = liveAlerts;
          _isLoading = false;
        });
      }
    });
  }

  Future<void> _loadAlerts() async {
    final user = SupabaseService().currentUser;
    if (user == null) {
      setState(() {
        _isLoading = false;
        _alerts = [];
      });
      return;
    }

    setState(() => _isLoading = true);
    final list = await ApiService().fetchAlerts(user.id);
    if (mounted) {
      setState(() {
        _alerts = list;
        _isLoading = false;
      });
    }
  }

  String _getSignalLabel(StokAlert alert) {
    final bias = alert.actionBias.toUpperCase();
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
    if (bias.contains('BUY') || bias.contains('ACCUMULATE')) return 'strong_buy';
    if (bias.contains('SELL')) return 'hold';
    if (bias.contains('TRAILING')) return 'med';
    
    final cat = alert.catalystType.toUpperCase();
    if (cat.contains('VOLUME')) return 'volume';
    if (cat.contains('BREAKOUT')) return 'breakout';
    if (alert.impactScore >= 80) return 'strong_buy';
    return 'buy';
  }

  @override
  Widget build(BuildContext context) {
    final filteredList = _alerts.where((a) {
      if (_selectedFilter == 'high') return a.impactScore >= 80;
      if (_selectedFilter == 'earnings') {
        return a.catalystType == 'EARNINGS_BEAT' ||
            a.alertTitle.toUpperCase().contains('EARNING') ||
            a.alertTitle.toUpperCase().contains('REVENUE');
      }
      if (_selectedFilter == 'breakout') {
        return a.catalystType == 'PRICE_BREAKOUT' ||
            a.alertTitle.toUpperCase().contains('BREAKOUT') ||
            a.alertTitle.toUpperCase().contains('HIGH');
      }
      if (_selectedFilter == 'volume') {
        return a.catalystType == 'VOLUME_SURGE' ||
            a.alertTitle.toUpperCase().contains('VOLUME') ||
            a.factualReasons.any((r) => r.toUpperCase().contains('VOLUME'));
      }
      if (_selectedFilter == 'fii') {
        return a.catalystType == 'BLOCK_DEAL' ||
            a.catalystType == 'DEBT_CHANGE' ||
            a.alertTitle.toUpperCase().contains('FII') ||
            a.alertTitle.toUpperCase().contains('DEAL') ||
            a.alertTitle.toUpperCase().contains('BLOCK');
      }
      if (_selectedFilter == 'trailing') {
        return a.actionBias.contains('TRAILING') ||
            a.alertTitle.toUpperCase().contains('TRAILING');
      }
      return true;
    }).toList();

    return Scaffold(
      backgroundColor: AppTheme.darkBackground,
      appBar: AppBar(
        backgroundColor: AppTheme.darkBackground,
        elevation: 0,
        title: const StokVigilBrandHeader(),
        actions: [
          IconButton(onPressed: _loadAlerts, icon: const Icon(Icons.refresh, color: AppTheme.cyan)),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _loadAlerts,
        color: AppTheme.cyan,
        child: Column(
          children: [
            // Filter Chip Bar
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              child: Row(
                children: [
                  _buildFilterChip('all', '⚡ All Alerts'),
                  _buildFilterChip('high', '🔥 High Impact'),
                  _buildFilterChip('trailing', '🟡 Trailing SL'),
                  _buildFilterChip('earnings', '📈 Earnings'),
                  _buildFilterChip('breakout', '🚀 Breakout'),
                  _buildFilterChip('volume', '⚡ Volume Surge'),
                  _buildFilterChip('fii', '📊 FII / Deals'),
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
                            final priceVal = alert.metricsSnapshot['current_price'] ?? alert.metricsSnapshot['price'] ?? 0.0;
                            final signalLabel = _getSignalLabel(alert);
                            final signalType = _getSignalType(alert);
                            final targetStr = alert.target1 ?? ((priceVal as num) > 0 ? "₹${(priceVal * 1.08).toStringAsFixed(0)}" : "₹0");
                            final slStr = alert.stopLoss ?? ((priceVal as num) > 0 ? "₹${(priceVal * 0.96).toStringAsFixed(0)}" : "₹0");
                            final rrStr = alert.riskReward ?? "1:2.0";

                            return GlassCard(
                              margin: const EdgeInsets.only(bottom: 16),
                              borderColor: isHigh ? AppTheme.borderCyan : AppTheme.cardBorder,
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
                                  RichText(
                                    text: TextSpan(
                                      children: [
                                        TextSpan(
                                          text: "[${alert.symbol}] ",
                                          style: const TextStyle(color: AppTheme.cyan, fontWeight: FontWeight.w900, fontSize: 15),
                                        ),
                                        TextSpan(
                                          text: alert.alertTitle,
                                          style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 14, height: 1.3),
                                        ),
                                      ],
                                    ),
                                  ),
                                  const SizedBox(height: 12),

                                  // Demat Position Banner (if user holds stock)
                                  if (alert.dematPosition != null) ...[
                                    Container(
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
                                              "ICICI Demat: ${alert.dematPosition!['quantity']} Qty @ Avg ₹${alert.dematPosition!['average_buy_price']} (P&L: ${alert.dematPosition!['unrealized_pnl_pct']}%)",
                                              style: const TextStyle(color: Colors.white, fontSize: 11.5, fontWeight: FontWeight.bold),
                                            ),
                                          ),
                                        ],
                                      ),
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
                                  const SizedBox(height: 12),

                                  // Fundamental Metrics Grid
                                  MetricChipStrip(metrics: alert.metricsSnapshot),
                                  const SizedBox(height: 12),

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
                                          currentPrice: (priceVal as num).toDouble(),
                                          initialType: alert.actionBias.contains('SELL') ? 'SELL' : 'BUY',
                                          targetPrice: targetStr,
                                          stopLoss: slStr,
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

  Widget _buildFilterChip(String filterKey, String label) {
    final active = _selectedFilter == filterKey;
    return GestureDetector(
      onTap: () => setState(() => _selectedFilter = filterKey),
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
