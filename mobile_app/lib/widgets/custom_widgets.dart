import 'package:flutter/material.dart';
import '../config/theme.dart';

// ─────────────────────────────────────────────
// REUSABLE GLASS CARD WIDGET
// ─────────────────────────────────────────────
class GlassCard extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry? padding;
  final EdgeInsetsGeometry? margin;
  final Color? borderColor;
  final Color? backgroundColor;
  final VoidCallback? onTap;

  const GlassCard({
    super.key,
    required this.child,
    this.padding,
    this.margin,
    this.borderColor,
    this.backgroundColor,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    Widget cardContent = Container(
      margin: margin,
      padding: padding ?? const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: backgroundColor ?? AppTheme.cardBackground,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: borderColor ?? AppTheme.cardBorder,
          width: 1,
        ),
        boxShadow: const [
          BoxShadow(
            color: Color(0x66000000),
            blurRadius: 24,
            offset: Offset(0, 8),
          ),
        ],
      ),
      child: child,
    );

    if (onTap != null) {
      return GestureDetector(
        onTap: onTap,
        child: cardContent,
      );
    }
    return cardContent;
  }
}

// ─────────────────────────────────────────────
// SIGNAL BADGE WIDGET
// ─────────────────────────────────────────────
class SignalBadge extends StatelessWidget {
  final String label;
  final String type; // 'strong_buy', 'buy', 'sell', 'high', 'med'
  final Color? colorOverride;

  const SignalBadge({
    super.key,
    required this.label,
    required this.type,
    this.colorOverride,
  });

  @override
  Widget build(BuildContext context) {
    Color bg;
    Color border;
    Color text;

    if (type == 'strong_buy' || type == 'buy') {
      bg = AppTheme.primaryEmerald.withOpacity(0.12);
      border = AppTheme.primaryEmerald.withOpacity(0.4);
      text = AppTheme.primaryEmerald;
    } else if (type == 'sell') {
      bg = AppTheme.secondaryAmber.withOpacity(0.12);
      border = AppTheme.secondaryAmber.withOpacity(0.4);
      text = AppTheme.secondaryAmber;
    } else if (type == 'high') {
      bg = AppTheme.primaryEmerald.withOpacity(0.15);
      border = AppTheme.primaryEmerald;
      text = AppTheme.primaryEmerald;
    } else if (type == 'med') {
      bg = AppTheme.secondaryAmber.withOpacity(0.15);
      border = AppTheme.secondaryAmber;
      text = AppTheme.secondaryAmber;
    } else {
      bg = AppTheme.cyan.withOpacity(0.12);
      border = AppTheme.borderCyan;
      text = AppTheme.cyan;
    }

    if (colorOverride != null) {
      bg = colorOverride!.withOpacity(0.15);
      border = colorOverride!;
      text = colorOverride!;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: border, width: 1.2),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: text,
          fontSize: 10,
          fontWeight: FontWeight.w900,
          letterSpacing: 0.5,
        ),
      ),
    );
  }
}

// ─────────────────────────────────────────────
// METRIC CHIP STRIP WIDGET
// ─────────────────────────────────────────────
class MetricChipStrip extends StatelessWidget {
  final Map<String, dynamic> metrics;

  const MetricChipStrip({super.key, required this.metrics});

  @override
  Widget build(BuildContext context) {
    if (metrics.isEmpty) return const SizedBox.shrink();

    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: const Color(0xFF080B16),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.cardBorder),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceAround,
        children: metrics.entries.map((e) {
          final valStr = e.value?.toString() ?? '-';
          return Column(
            children: [
              Text(
                e.key.toUpperCase(),
                style: const TextStyle(
                  color: AppTheme.textMuted,
                  fontSize: 9,
                  fontWeight: FontWeight.w800,
                ),
              ),
              const SizedBox(height: 3),
              Text(
                valStr,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 12,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          );
        }).toList(),
      ),
    );
  }
}

// ─────────────────────────────────────────────
// INTERACTIVE TRADE ORDER PLACEMENT MODAL
// ─────────────────────────────────────────────
class TradeOrderModal extends StatefulWidget {
  final String symbol;
  final double currentPrice;
  final String initialType; // 'BUY' or 'SELL'
  final String targetPrice;
  final String stopLoss;

  const TradeOrderModal({
    super.key,
    required this.symbol,
    required this.currentPrice,
    this.initialType = 'BUY',
    this.targetPrice = '₹3,250',
    this.stopLoss = '₹2,820',
  });

  static void show(
    BuildContext context, {
    required String symbol,
    required double currentPrice,
    String initialType = 'BUY',
    String targetPrice = '₹3,250',
    String stopLoss = '₹2,820',
  }) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => TradeOrderModal(
        symbol: symbol,
        currentPrice: currentPrice,
        initialType: initialType,
        targetPrice: targetPrice,
        stopLoss: stopLoss,
      ),
    );
  }

  @override
  State<TradeOrderModal> createState() => _TradeOrderModalState();
}

class _TradeOrderModalState extends State<TradeOrderModal> {
  late String _tradeType;
  late String _orderType;
  int _qty = 10;
  late TextEditingController _limitPriceController;
  bool _isSuccess = false;

  @override
  void initState() {
    super.initState();
    _tradeType = widget.initialType;
    _orderType = 'MARKET';
    _limitPriceController = TextEditingController(text: widget.currentPrice.toStringAsFixed(2));
  }

  @override
  void dispose() {
    _limitPriceController.dispose();
    super.dispose();
  }

  void _executeOrder() {
    setState(() => _isSuccess = true);
    Future.delayed(const Duration(milliseconds: 1600), () {
      if (mounted) {
        Navigator.of(context).pop();
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final totalAmount = _qty * widget.currentPrice;

    return Padding(
      padding: EdgeInsets.only(
        bottom: MediaQuery.of(context).viewInsets.bottom,
      ),
      child: Container(
        padding: const EdgeInsets.all(22),
        decoration: const BoxDecoration(
          color: AppTheme.cardBackground,
          borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
          border: Border(
            top: BorderSide(color: AppTheme.borderCyan, width: 1.5),
            left: BorderSide(color: AppTheme.cardBorder, width: 1),
            right: BorderSide(color: AppTheme.cardBorder, width: 1),
          ),
          boxShadow: [
            BoxShadow(color: Colors.black87, blurRadius: 30, spreadRadius: 5),
          ],
        ),
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Handlebar
              Center(
                child: Container(
                  width: 40,
                  height: 4,
                  decoration: BoxDecoration(
                    color: AppTheme.textMuted,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              const SizedBox(height: 16),

              // Title Row
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      Container(
                        width: 36,
                        height: 36,
                        decoration: BoxDecoration(
                          color: _tradeType == 'BUY'
                              ? AppTheme.primaryEmerald.withOpacity(0.15)
                              : AppTheme.dangerRose.withOpacity(0.15),
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(
                            color: _tradeType == 'BUY' ? AppTheme.primaryEmerald : AppTheme.dangerRose,
                          ),
                        ),
                        child: Icon(
                          _tradeType == 'BUY' ? Icons.arrow_upward : Icons.arrow_downward,
                          color: _tradeType == 'BUY' ? AppTheme.primaryEmerald : AppTheme.dangerRose,
                          size: 20,
                        ),
                      ),
                      const SizedBox(width: 12),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            "${_tradeType == 'BUY' ? 'BUY' : 'SELL'} ${widget.symbol}",
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 18,
                              fontWeight: FontWeight.w900,
                            ),
                          ),
                          const Text(
                            "ICICI Demat 1-Tap Execution",
                            style: TextStyle(color: AppTheme.textSecondary, fontSize: 11),
                          ),
                        ],
                      ),
                    ],
                  ),
                  IconButton(
                    onPressed: () => Navigator.of(context).pop(),
                    icon: const Icon(Icons.close, color: AppTheme.textSecondary),
                  )
                ],
              ),
              const SizedBox(height: 20),

              if (_isSuccess) ...[
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(
                    color: AppTheme.primaryEmerald.withOpacity(0.12),
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: AppTheme.primaryEmerald),
                  ),
                  child: Column(
                    children: [
                      const Icon(Icons.check_circle, color: AppTheme.primaryEmerald, size: 48),
                      const SizedBox(height: 10),
                      Text(
                        "Order Placed Successfully!",
                        style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        "$_tradeType $_qty shares of ${widget.symbol} @ ₹${widget.currentPrice}",
                        style: const TextStyle(color: AppTheme.primaryEmerald, fontSize: 12, fontWeight: FontWeight.w600),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 20),
              ] else ...[
                // Order Type Selector
                Row(
                  children: ['BUY', 'SELL'].map((type) {
                    final selected = _tradeType == type;
                    return Expanded(
                      child: GestureDetector(
                        onTap: () => setState(() => _tradeType = type),
                        child: Container(
                          margin: const EdgeInsets.symmetric(horizontal: 4),
                          padding: const EdgeInsets.symmetric(vertical: 10),
                          decoration: BoxDecoration(
                            color: selected
                                ? (type == 'BUY' ? AppTheme.primaryEmerald : AppTheme.dangerRose)
                                : AppTheme.cardBackground2,
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: Center(
                            child: Text(
                              type,
                              style: TextStyle(
                                color: selected ? Colors.black : AppTheme.textSecondary,
                                fontWeight: FontWeight.w900,
                                fontSize: 13,
                              ),
                            ),
                          ),
                        ),
                      ),
                    );
                  }).toList(),
                ),
                const SizedBox(height: 16),

                // Order Mode Toggle (MARKET / LIMIT)
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text("Execution Type", style: TextStyle(color: AppTheme.textSecondary, fontSize: 12, fontWeight: FontWeight.bold)),
                    Row(
                      children: ['MARKET', 'LIMIT'].map((mode) {
                        final active = _orderType == mode;
                        return GestureDetector(
                          onTap: () => setState(() => _orderType = mode),
                          child: Container(
                            margin: const EdgeInsets.only(left: 6),
                            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                            decoration: BoxDecoration(
                              color: active ? AppTheme.cyan.withOpacity(0.15) : AppTheme.cardBackground2,
                              borderRadius: BorderRadius.circular(8),
                              border: Border.all(color: active ? AppTheme.cyan : AppTheme.cardBorder),
                            ),
                            child: Text(
                              mode,
                              style: TextStyle(
                                color: active ? AppTheme.cyan : AppTheme.textSecondary,
                                fontSize: 11,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ),
                        );
                      }).toList(),
                    ),
                  ],
                ),
                const SizedBox(height: 16),

                // Quantity Counter
                Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: const Color(0xFF080B16),
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(color: AppTheme.cardBorder),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text("Quantity (Shares)", style: TextStyle(color: AppTheme.textSecondary, fontSize: 12, fontWeight: FontWeight.bold)),
                      Row(
                        children: [
                          IconButton(
                            onPressed: _qty > 1 ? () => setState(() => _qty--) : null,
                            icon: const Icon(Icons.remove_circle_outline, color: AppTheme.cyan),
                          ),
                          Text("$_qty", style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w900)),
                          IconButton(
                            onPressed: () => setState(() => _qty++),
                            icon: const Icon(Icons.add_circle_outline, color: AppTheme.cyan),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),

                // Target & Stop Loss Info Strip
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AppTheme.cyan.withOpacity(0.06),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: AppTheme.cyan.withOpacity(0.2)),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceAround,
                    children: [
                      Text("🎯 Target: ${widget.targetPrice}", style: const TextStyle(color: AppTheme.primaryEmerald, fontSize: 12, fontWeight: FontWeight.bold)),
                      Text("🛡️ Stop Loss: ${widget.stopLoss}", style: const TextStyle(color: AppTheme.dangerRose, fontSize: 12, fontWeight: FontWeight.bold)),
                    ],
                  ),
                ),
                const SizedBox(height: 20),

                // Estimated Total & Submit CTA
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text("TOTAL VALUE", style: TextStyle(color: AppTheme.textMuted, fontSize: 10, fontWeight: FontWeight.bold)),
                        Text("₹${totalAmount.toStringAsFixed(2)}", style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w900)),
                      ],
                    ),
                    Expanded(
                      child: Container(
                        margin: const EdgeInsets.only(left: 16),
                        height: 48,
                        child: ElevatedButton(
                          style: ElevatedButton.styleFrom(
                            backgroundColor: _tradeType == 'BUY' ? AppTheme.primaryEmerald : AppTheme.dangerRose,
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                          ),
                          onPressed: _executeOrder,
                          child: Text(
                            "Confirm $_tradeType Order",
                            style: const TextStyle(color: Colors.black, fontWeight: FontWeight.w900, fontSize: 14),
                          ),
                        ),
                      ),
                    )
                  ],
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
