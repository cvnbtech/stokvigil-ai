import 'package:flutter/material.dart';
import '../config/theme.dart';

// ─────────────────────────────────────────────
// OFFICIAL 4-COLOR GOOGLE 'G' LOGO WIDGET
// ─────────────────────────────────────────────
class OfficialGoogleLogo extends StatelessWidget {
  final double size;
  const OfficialGoogleLogo({super.key, this.size = 22});

  @override
  Widget build(BuildContext context) {
    return CustomPaint(
      size: Size(size, size),
      painter: _GoogleLogoPainter(),
    );
  }
}

class _GoogleLogoPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final double s = size.width;
    final double scale = s / 24.0;

    canvas.save();
    canvas.scale(scale, scale);

    // 1. Blue Arm & Right Arc (#4285F4)
    final Path bluePath = Path()
      ..moveTo(22.56, 12.25)
      ..cubicTo(22.56, 11.47, 22.49, 10.72, 22.36, 10.0)
      ..lineTo(12.0, 10.0)
      ..lineTo(12.0, 14.26)
      ..lineTo(17.92, 14.26)
      ..cubicTo(17.66, 15.63, 16.88, 16.79, 15.71, 17.57)
      ..lineTo(15.71, 20.34)
      ..lineTo(19.28, 20.34)
      ..cubicTo(21.36, 18.42, 22.56, 15.6, 22.56, 12.25);
    canvas.drawPath(bluePath, Paint()..color = const Color(0xFF4285F4)..style = PaintingStyle.fill);

    // 2. Green Bottom Arc (#34A853)
    final Path greenPath = Path()
      ..moveTo(12.0, 23.0)
      ..cubicTo(14.97, 23.0, 17.46, 22.02, 19.28, 20.34)
      ..lineTo(15.71, 17.57)
      ..cubicTo(14.73, 18.23, 13.48, 18.63, 12.0, 18.63)
      ..cubicTo(9.14, 18.63, 6.71, 16.7, 5.84, 14.1)
      ..lineTo(2.18, 14.1)
      ..lineTo(2.18, 16.94)
      ..cubicTo(3.99, 20.53, 7.7, 23.0, 12.0, 23.0);
    canvas.drawPath(greenPath, Paint()..color = const Color(0xFF34A853)..style = PaintingStyle.fill);

    // 3. Yellow Left Arc (#FBBC05)
    final Path yellowPath = Path()
      ..moveTo(5.84, 14.1)
      ..cubicTo(5.62, 13.44, 5.49, 12.74, 5.49, 12.0)
      ..cubicTo(5.49, 11.26, 5.62, 10.56, 5.84, 9.9)
      ..lineTo(5.84, 7.06)
      ..lineTo(2.18, 7.06)
      ..cubicTo(1.43, 8.55, 1.0, 10.22, 1.0, 12.0)
      ..cubicTo(1.0, 13.78, 1.43, 15.45, 2.18, 16.94)
      ..lineTo(5.84, 14.1);
    canvas.drawPath(yellowPath, Paint()..color = const Color(0xFFFBBC05)..style = PaintingStyle.fill);

    // 4. Red Top Arc (#EA4335)
    final Path redPath = Path()
      ..moveTo(12.0, 5.38)
      ..cubicTo(13.62, 5.38, 15.06, 5.94, 16.21, 7.02)
      ..lineTo(19.36, 3.87)
      ..cubicTo(17.45, 2.09, 14.97, 1.0, 12.0, 1.0)
      ..cubicTo(7.7, 1.0, 3.99, 3.47, 2.18, 7.06)
      ..lineTo(5.84, 9.9)
      ..cubicTo(6.71, 7.3, 9.14, 5.38, 12.0, 5.38);
    canvas.drawPath(redPath, Paint()..color = const Color(0xFFEA4335)..style = PaintingStyle.fill);

    canvas.restore();
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

// ─────────────────────────────────────────────
// OFFICIAL TRADING AI LOGO EMBLEM (MATCHES WEB PORTAL)
// ─────────────────────────────────────────────
class TradingAILogo extends StatelessWidget {
  final double size;

  const TradingAILogo({super.key, this.size = 36});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(size * 0.28),
        boxShadow: const [
          BoxShadow(color: Color(0x4D06B6D4), blurRadius: 12, offset: Offset(0, 4)),
        ],
      ),
      child: CustomPaint(
        size: Size(size, size),
        painter: CandlestickBreakoutLogoPainter(),
      ),
    );
  }
}

class CandlestickBreakoutLogoPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final s = size.width / 52.0;

    // 1. Background Squircle (#0D111E -> #080B16)
    final bgPaint = Paint()
      ..shader = const LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: [Color(0xFF0D111E), Color(0xFF080B16)],
      ).createShader(Rect.fromLTWH(0, 0, size.width, size.height));

    final rrect = RRect.fromRectAndRadius(
      Rect.fromLTWH(0, 0, size.width, size.height),
      Radius.circular(14.0 * s),
    );
    canvas.drawRRect(rrect, bgPaint);

    // Cyan Border
    final borderPaint = Paint()
      ..color = const Color(0x4006B6D4)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.5 * s;
    canvas.drawRRect(rrect, borderPaint);

    // 2. Candlesticks Underneath
    // Green Candlestick
    final greenLine = Paint()
      ..color = const Color(0x9910B981)
      ..strokeWidth = 1.2 * s;
    canvas.drawLine(Offset(14 * s, 18 * s), Offset(14 * s, 38 * s), greenLine);

    final greenBody = Paint()..color = const Color(0xD910B981);
    canvas.drawRRect(
      RRect.fromRectAndRadius(Rect.fromLTWH(12 * s, 22 * s, 4 * s, 12 * s), Radius.circular(1 * s)),
      greenBody,
    );

    // Red Candlestick
    final redLine = Paint()
      ..color = const Color(0x99EF4444)
      ..strokeWidth = 1.2 * s;
    canvas.drawLine(Offset(24 * s, 24 * s), Offset(24 * s, 40 * s), redLine);

    final redBody = Paint()..color = const Color(0xD9EF4444);
    canvas.drawRRect(
      RRect.fromRectAndRadius(Rect.fromLTWH(22 * s, 27 * s, 4 * s, 8 * s), Radius.circular(1 * s)),
      redBody,
    );

    // Cyan Candlestick
    final cyanLine = Paint()
      ..color = const Color(0x9906B6D4)
      ..strokeWidth = 1.2 * s;
    canvas.drawLine(Offset(34 * s, 10 * s), Offset(34 * s, 36 * s), cyanLine);

    final cyanBody = Paint()..color = const Color(0xE606B6D4);
    canvas.drawRRect(
      RRect.fromRectAndRadius(Rect.fromLTWH(32 * s, 14 * s, 4 * s, 18 * s), Radius.circular(1 * s)),
      cyanBody,
    );

    // 3. Overlaid Up-Down-Up Breakout Arrow Path
    final arrowShader = const LinearGradient(
      begin: Alignment.bottomLeft,
      end: Alignment.topRight,
      colors: [Color(0xFF06B6D4), Color(0xFF38BDF8), Color(0xFF8B5CF6)],
    ).createShader(Rect.fromLTWH(4 * s, 6 * s, 44 * s, 38 * s));

    final arrowPath = Path()
      ..moveTo(6 * s, 38 * s)
      ..lineTo(14 * s, 22 * s)
      ..lineTo(24 * s, 31 * s)
      ..lineTo(38 * s, 11 * s);

    // Glow Layer
    final glowPaint = Paint()
      ..shader = arrowShader
      ..strokeWidth = 5.5 * s
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 2.5);
    canvas.drawPath(arrowPath, glowPaint);

    // Core Arrow Line
    final linePaint = Paint()
      ..shader = arrowShader
      ..strokeWidth = 3.5 * s
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;
    canvas.drawPath(arrowPath, linePaint);

    // Arrowhead Triangle
    final headPath = Path()
      ..moveTo(44 * s, 6 * s)
      ..lineTo(32 * s, 11 * s)
      ..lineTo(38 * s, 19 * s)
      ..close();

    final headPaint = Paint()
      ..shader = arrowShader
      ..style = PaintingStyle.fill;
    canvas.drawPath(headPath, headPaint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

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

    if (type == 'strong_buy' || type == 'buy' || type == 'high' || type == 'bullish') {
      bg = AppTheme.primaryEmerald.withOpacity(0.15);
      border = AppTheme.primaryEmerald;
      text = AppTheme.primaryEmerald;
    } else if (type == 'med' || type == 'moderate') {
      bg = AppTheme.secondaryAmber.withOpacity(0.15);
      border = AppTheme.secondaryAmber;
      text = AppTheme.secondaryAmber;
    } else {
      bg = AppTheme.dangerRose.withOpacity(0.15);
      border = AppTheme.dangerRose;
      text = AppTheme.dangerRose;
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
                      const Text(
                        "Order Placed Successfully!",
                        style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16),
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
