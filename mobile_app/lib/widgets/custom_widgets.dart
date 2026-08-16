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
// OFFICIAL STOKVIGIL BRAND HEADER
// ─────────────────────────────────────────────
class StokVigilBrandHeader extends StatelessWidget {
  final double logoSize;
  final Widget? trailing;

  const StokVigilBrandHeader({
    super.key,
    this.logoSize = 34,
    this.trailing,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        Expanded(
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              TradingAILogo(size: logoSize),
              const SizedBox(width: 8),
              Flexible(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    FittedBox(
                      fit: BoxFit.scaleDown,
                      alignment: Alignment.centerLeft,
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Text(
                            "StokVigil ",
                            style: TextStyle(
                              color: Colors.white,
                              fontSize: 17,
                              fontWeight: FontWeight.w900,
                              letterSpacing: -0.3,
                            ),
                          ),
                          ShaderMask(
                            shaderCallback: (bounds) => AppTheme.logoGradient.createShader(bounds),
                            child: const Text(
                              "AI",
                              style: TextStyle(
                                color: Colors.white,
                                fontSize: 17,
                                fontWeight: FontWeight.w900,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 2),
                    FittedBox(
                      fit: BoxFit.scaleDown,
                      alignment: Alignment.centerLeft,
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Container(
                            width: 5,
                            height: 5,
                            decoration: const BoxDecoration(
                              color: AppTheme.primaryEmerald,
                              shape: BoxShape.circle,
                            ),
                          ),
                          const SizedBox(width: 4),
                          const Text(
                            "NSE LIVE 09:15–15:30",
                            style: TextStyle(
                              color: AppTheme.primaryEmerald,
                              fontSize: 9.5,
                              fontWeight: FontWeight.w800,
                              letterSpacing: 0.2,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
        if (trailing != null) ...[
          const SizedBox(width: 8),
          trailing!,
        ],
      ],
    );
  }
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
  final String type; // 'strong_buy', 'buy', 'volume', 'breakout', 'hold', 'neutral', 'med', 'sell'
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
    } else if (type == 'volume' || type == 'breakout') {
      bg = AppTheme.cyan.withOpacity(0.15);
      border = AppTheme.cyan;
      text = AppTheme.cyan;
    } else if (type == 'med' || type == 'moderate') {
      bg = AppTheme.secondaryAmber.withOpacity(0.15);
      border = AppTheme.secondaryAmber;
      text = AppTheme.secondaryAmber;
    } else if (type == 'hold' || type == 'neutral') {
      bg = AppTheme.textSecondary.withOpacity(0.15);
      border = AppTheme.textSecondary;
      text = AppTheme.textSecondary;
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
    this.targetPrice = '3250',
    this.stopLoss = '2820',
  });

  static void show(
    BuildContext context, {
    required String symbol,
    required double currentPrice,
    String initialType = 'BUY',
    String targetPrice = '3250',
    String stopLoss = '2820',
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
  late TextEditingController _targetController;
  late TextEditingController _stopLossController;
  late TextEditingController _qtyController;
  bool _isSuccess = false;

  @override
  void initState() {
    super.initState();
    _tradeType = widget.initialType;
    _orderType = 'MARKET';
    _limitPriceController = TextEditingController(text: widget.currentPrice.toStringAsFixed(2));
    _targetController = TextEditingController(text: widget.targetPrice.replaceAll(RegExp(r'[^0-9.]'), ''));
    _stopLossController = TextEditingController(text: widget.stopLoss.replaceAll(RegExp(r'[^0-9.]'), ''));
    _qtyController = TextEditingController(text: '$_qty');
  }

  @override
  void dispose() {
    _limitPriceController.dispose();
    _targetController.dispose();
    _stopLossController.dispose();
    _qtyController.dispose();
    super.dispose();
  }

  double get _effectivePrice {
    if (_orderType == 'LIMIT') {
      return double.tryParse(_limitPriceController.text.trim()) ?? widget.currentPrice;
    }
    return widget.currentPrice;
  }

  void _executeOrder() {
    setState(() => _isSuccess = true);
  }

  String _formatIndian(double val) {
    final intPart = val.truncate().abs();
    final str = intPart.toString();
    if (str.length <= 3) return "${str}.${(val.abs() - intPart).toStringAsFixed(2).split('.').last}";
    final last3 = str.substring(str.length - 3);
    final rest = str.substring(0, str.length - 3);
    final formattedRest = rest.replaceAllMapped(
      RegExp(r'(\d)(?=(\d{2})+(?!\d))'),
      (Match m) => '${m[1]},',
    );
    final dec = ((val.abs() - intPart) * 100).round().toString().padLeft(2, '0');
    return '$formattedRest,$last3.$dec';
  }

  @override
  Widget build(BuildContext context) {
    final isBuy = _tradeType == 'BUY';
    final totalAmount = _qty * _effectivePrice;

    return Padding(
      padding: EdgeInsets.only(
        bottom: MediaQuery.of(context).viewInsets.bottom,
      ),
      child: Container(
        padding: const EdgeInsets.all(22),
        decoration: BoxDecoration(
          color: AppTheme.cardBackground,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
          border: const Border(
            top: BorderSide(color: AppTheme.cardBorder, width: 1),
            left: BorderSide(color: AppTheme.cardBorder, width: 1),
            right: BorderSide(color: AppTheme.cardBorder, width: 1),
          ),
          boxShadow: const [
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

              // Header: Badge + Symbol + Close Button
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                        decoration: BoxDecoration(
                          color: (isBuy ? AppTheme.primaryEmerald : AppTheme.dangerRose).withOpacity(0.18),
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(
                            color: isBuy ? AppTheme.primaryEmerald : AppTheme.dangerRose,
                            width: 1.2,
                          ),
                        ),
                        child: Text(
                          "$_tradeType ORDER",
                          style: TextStyle(
                            color: isBuy ? AppTheme.primaryEmerald : AppTheme.dangerRose,
                            fontWeight: FontWeight.w900,
                            fontSize: 12,
                          ),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Text(
                        widget.symbol,
                        style: const TextStyle(color: Colors.white, fontSize: 17, fontWeight: FontWeight.w900),
                      ),
                    ],
                  ),
                  IconButton(
                    onPressed: () => Navigator.of(context).pop(),
                    icon: const Icon(Icons.close, color: AppTheme.textSecondary, size: 20),
                    padding: EdgeInsets.zero,
                    constraints: const BoxConstraints(),
                  )
                ],
              ),
              const SizedBox(height: 18),

              if (_isSuccess) ...[
                // Order Success Receipt (Matches Web Portal)
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(
                    color: AppTheme.primaryEmerald.withOpacity(0.12),
                    borderRadius: BorderRadius.circular(18),
                    border: Border.all(color: AppTheme.primaryEmerald.withOpacity(0.4), width: 1.2),
                  ),
                  child: Column(
                    children: [
                      const Text("🎉", style: TextStyle(fontSize: 32)),
                      const SizedBox(height: 8),
                      const Text(
                        "Order Executed via ICICI Breeze!",
                        textAlign: TextAlign.center,
                        style: TextStyle(color: AppTheme.primaryEmerald, fontWeight: FontWeight.w900, fontSize: 15),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        "Placed $_tradeType order for $_qty shares of ${widget.symbol} at ₹${_effectivePrice.toStringAsFixed(2)} (Total: ₹${_formatIndian(totalAmount)}).",
                        textAlign: TextAlign.center,
                        style: const TextStyle(color: AppTheme.textSecondary, fontSize: 12, height: 1.5),
                      ),
                      const SizedBox(height: 12),
                      const Text(
                        "📱 Execution Receipt sent to @StokVigilAi_bot on Telegram",
                        textAlign: TextAlign.center,
                        style: TextStyle(color: AppTheme.cyan, fontSize: 11, fontWeight: FontWeight.w800),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 18),
                Container(
                  width: double.infinity,
                  height: 48,
                  decoration: BoxDecoration(
                    gradient: AppTheme.logoGradient,
                    borderRadius: BorderRadius.circular(14),
                    boxShadow: const [
                      BoxShadow(color: Color(0x4D06B6D4), blurRadius: 12, offset: Offset(0, 4)),
                    ],
                  ),
                  child: ElevatedButton(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.transparent,
                      shadowColor: Colors.transparent,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                      padding: EdgeInsets.zero,
                    ),
                    onPressed: () => Navigator.of(context).pop(),
                    child: const Text("Done", style: TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 14)),
                  ),
                ),
              ] else ...[
                // BUY / SELL Segmented Switcher
                Container(
                  decoration: BoxDecoration(
                    color: const Color(0xFF080B16),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: AppTheme.cardBorder),
                  ),
                  padding: const EdgeInsets.all(3),
                  child: Row(
                    children: [
                      Expanded(
                        child: GestureDetector(
                          onTap: () => setState(() => _tradeType = 'BUY'),
                          child: Container(
                            padding: const EdgeInsets.symmetric(vertical: 9),
                            decoration: BoxDecoration(
                              color: isBuy ? AppTheme.primaryEmerald : Colors.transparent,
                              borderRadius: BorderRadius.circular(9),
                            ),
                            alignment: Alignment.center,
                            child: Text(
                              "BUY",
                              style: TextStyle(
                                color: isBuy ? Colors.black : AppTheme.textSecondary,
                                fontWeight: FontWeight.w900,
                                fontSize: 13,
                              ),
                            ),
                          ),
                        ),
                      ),
                      Expanded(
                        child: GestureDetector(
                          onTap: () => setState(() => _tradeType = 'SELL'),
                          child: Container(
                            padding: const EdgeInsets.symmetric(vertical: 9),
                            decoration: BoxDecoration(
                              color: !isBuy ? AppTheme.dangerRose : Colors.transparent,
                              borderRadius: BorderRadius.circular(9),
                            ),
                            alignment: Alignment.center,
                            child: Text(
                              "SELL",
                              style: TextStyle(
                                color: !isBuy ? Colors.white : AppTheme.textSecondary,
                                fontWeight: FontWeight.w900,
                                fontSize: 13,
                              ),
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 14),

                // MARKET / LIMIT Order Type Selector
                Row(
                  children: [
                    Expanded(
                      child: GestureDetector(
                        onTap: () => setState(() => _orderType = 'MARKET'),
                        child: Container(
                          padding: const EdgeInsets.symmetric(vertical: 9),
                          decoration: BoxDecoration(
                            color: _orderType == 'MARKET' ? AppTheme.cyan.withOpacity(0.16) : const Color(0xFF080B16),
                            borderRadius: BorderRadius.circular(10),
                            border: Border.all(color: _orderType == 'MARKET' ? AppTheme.cyan : AppTheme.cardBorder, width: 1.4),
                          ),
                          alignment: Alignment.center,
                          child: Text(
                            "MARKET ORDER",
                            style: TextStyle(
                              color: _orderType == 'MARKET' ? AppTheme.cyan : AppTheme.textSecondary,
                              fontWeight: FontWeight.w800,
                              fontSize: 11.5,
                            ),
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: GestureDetector(
                        onTap: () => setState(() => _orderType = 'LIMIT'),
                        child: Container(
                          padding: const EdgeInsets.symmetric(vertical: 9),
                          decoration: BoxDecoration(
                            color: _orderType == 'LIMIT' ? AppTheme.cyan.withOpacity(0.16) : const Color(0xFF080B16),
                            borderRadius: BorderRadius.circular(10),
                            border: Border.all(color: _orderType == 'LIMIT' ? AppTheme.cyan : AppTheme.cardBorder, width: 1.4),
                          ),
                          alignment: Alignment.center,
                          child: Text(
                            "LIMIT ORDER",
                            style: TextStyle(
                              color: _orderType == 'LIMIT' ? AppTheme.cyan : AppTheme.textSecondary,
                              fontWeight: FontWeight.w800,
                              fontSize: 11.5,
                            ),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),

                // Dynamic Explanation Card & Custom Limit Input
                if (_orderType == 'LIMIT') ...[
                  Container(
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      color: const Color(0xFF080B16),
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(color: AppTheme.borderCyan),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            const Text(
                              "CUSTOM LIMIT PRICE (₹)",
                              style: TextStyle(color: AppTheme.cyan, fontSize: 10, fontWeight: FontWeight.w900),
                            ),
                            Text(
                              "LTP: ₹${widget.currentPrice.toStringAsFixed(2)}",
                              style: const TextStyle(color: AppTheme.textMuted, fontSize: 10, fontWeight: FontWeight.w700),
                            ),
                          ],
                        ),
                        const SizedBox(height: 8),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 12),
                          decoration: BoxDecoration(
                            color: const Color(0xFF04060E),
                            borderRadius: BorderRadius.circular(10),
                            border: Border.all(color: AppTheme.borderCyan),
                          ),
                          child: TextField(
                            controller: _limitPriceController,
                            keyboardType: const TextInputType.numberWithOptions(decimal: true),
                            style: const TextStyle(color: AppTheme.cyan, fontSize: 16, fontWeight: FontWeight.w900),
                            decoration: const InputDecoration(border: InputBorder.none),
                            onChanged: (_) => setState(() {}),
                          ),
                        ),
                        const SizedBox(height: 8),
                        Container(
                          padding: const EdgeInsets.all(8),
                          decoration: BoxDecoration(
                            color: AppTheme.cyan.withOpacity(0.06),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Text(
                            "💡 What is a Limit Order? Sets the maximum price (₹${_limitPriceController.text.isEmpty ? widget.currentPrice.toStringAsFixed(2) : _limitPriceController.text}) you are willing to pay. Triggers only if market price reaches or drops below your limit.",
                            style: const TextStyle(color: AppTheme.textSecondary, fontSize: 10.5, height: 1.4),
                          ),
                        ),
                      ],
                    ),
                  ),
                ] else ...[
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: AppTheme.cyan.withOpacity(0.06),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: AppTheme.borderCyan.withOpacity(0.6), style: BorderStyle.solid),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text("⚡ What is a Market Order?", style: TextStyle(color: AppTheme.cyan, fontSize: 11, fontWeight: FontWeight.w900)),
                        const SizedBox(height: 4),
                        Text(
                          "Executes immediately at the best available current market price (LTP: ₹${widget.currentPrice.toStringAsFixed(2)}). Guarantees instant execution.",
                          style: const TextStyle(color: AppTheme.textSecondary, fontSize: 10.5, height: 1.4),
                        ),
                      ],
                    ),
                  ),
                ],
                const SizedBox(height: 14),

                // Quantity Stepper Control
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
                      const Text(
                        "QUANTITY (SHARES)",
                        style: TextStyle(color: AppTheme.textMuted, fontSize: 10, fontWeight: FontWeight.w800, letterSpacing: 0.5),
                      ),
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          GestureDetector(
                            onTap: _qty > 1 ? () {
                              setState(() {
                                _qty--;
                                _qtyController.text = '$_qty';
                              });
                            } : null,
                            child: Container(
                              width: 40,
                              height: 40,
                              decoration: BoxDecoration(
                                color: AppTheme.cyan.withOpacity(0.1),
                                borderRadius: BorderRadius.circular(10),
                                border: Border.all(color: AppTheme.borderCyan),
                              ),
                              alignment: Alignment.center,
                              child: const Text("-", style: TextStyle(color: AppTheme.cyan, fontSize: 22, fontWeight: FontWeight.w900)),
                            ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Container(
                              height: 40,
                              decoration: BoxDecoration(
                                color: const Color(0xFF04060E),
                                borderRadius: BorderRadius.circular(10),
                                border: Border.all(color: AppTheme.borderCyan),
                              ),
                              child: TextField(
                                controller: _qtyController,
                                textAlign: TextAlign.center,
                                keyboardType: TextInputType.number,
                                style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w900),
                                decoration: const InputDecoration(border: InputBorder.none, contentPadding: EdgeInsets.only(bottom: 8)),
                                onChanged: (val) {
                                  final parsed = int.tryParse(val.trim());
                                  if (parsed != null && parsed > 0) {
                                    setState(() => _qty = parsed);
                                  }
                                },
                              ),
                            ),
                          ),
                          const SizedBox(width: 8),
                          GestureDetector(
                            onTap: () {
                              setState(() {
                                _qty++;
                                _qtyController.text = '$_qty';
                              });
                            },
                            child: Container(
                              width: 40,
                              height: 40,
                              decoration: BoxDecoration(
                                color: AppTheme.cyan.withOpacity(0.1),
                                borderRadius: BorderRadius.circular(10),
                                border: Border.all(color: AppTheme.borderCyan),
                              ),
                              alignment: Alignment.center,
                              child: const Text("+", style: TextStyle(color: AppTheme.cyan, fontSize: 22, fontWeight: FontWeight.w900)),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 14),

                // Financial Breakdown & Auto Risk Bracket Order
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
                        children: [
                          const Text("Execution Price:", style: TextStyle(color: AppTheme.textSecondary, fontSize: 11.5)),
                          Text("₹${_effectivePrice.toStringAsFixed(2)}", style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w900)),
                        ],
                      ),
                      const SizedBox(height: 6),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text("Total Order Value:", style: TextStyle(color: AppTheme.textSecondary, fontSize: 11.5)),
                          Text("₹${_formatIndian(totalAmount)}", style: const TextStyle(color: AppTheme.cyan, fontSize: 13, fontWeight: FontWeight.w900)),
                        ],
                      ),
                      const SizedBox(height: 10),
                      const Divider(color: AppTheme.cardBorder, height: 1),
                      const SizedBox(height: 10),

                      const Text(
                        "🛡️ AUTO RISK MANAGEMENT (BRACKET ORDER)",
                        style: TextStyle(color: AppTheme.textMuted, fontSize: 9.5, fontWeight: FontWeight.w900, letterSpacing: 0.5),
                      ),
                      const SizedBox(height: 8),

                      Row(
                        children: [
                          // Target Input
                          Expanded(
                            child: Container(
                              padding: const EdgeInsets.all(8),
                              decoration: BoxDecoration(
                                color: AppTheme.primaryEmerald.withOpacity(0.06),
                                borderRadius: BorderRadius.circular(10),
                                border: Border.all(color: AppTheme.primaryEmerald.withOpacity(0.3)),
                              ),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  const Text("🎯 TARGET (₹)", style: TextStyle(color: AppTheme.primaryEmerald, fontSize: 9.5, fontWeight: FontWeight.w900)),
                                  const SizedBox(height: 4),
                                  Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 6),
                                    decoration: BoxDecoration(
                                      color: const Color(0xFF04060E),
                                      borderRadius: BorderRadius.circular(6),
                                      border: Border.all(color: AppTheme.primaryEmerald.withOpacity(0.4)),
                                    ),
                                    child: TextField(
                                      controller: _targetController,
                                      keyboardType: const TextInputType.numberWithOptions(decimal: true),
                                      style: const TextStyle(color: AppTheme.primaryEmerald, fontSize: 12, fontWeight: FontWeight.w900),
                                      decoration: const InputDecoration(border: InputBorder.none, isDense: true, contentPadding: EdgeInsets.symmetric(vertical: 4)),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                          const SizedBox(width: 8),

                          // Stop Loss Input
                          Expanded(
                            child: Container(
                              padding: const EdgeInsets.all(8),
                              decoration: BoxDecoration(
                                color: AppTheme.dangerRose.withOpacity(0.06),
                                borderRadius: BorderRadius.circular(10),
                                border: Border.all(color: AppTheme.dangerRose.withOpacity(0.3)),
                              ),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  const Text("🛡️ STOP LOSS (₹)", style: TextStyle(color: AppTheme.dangerRose, fontSize: 9.5, fontWeight: FontWeight.w900)),
                                  const SizedBox(height: 4),
                                  Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 6),
                                    decoration: BoxDecoration(
                                      color: const Color(0xFF04060E),
                                      borderRadius: BorderRadius.circular(6),
                                      border: Border.all(color: AppTheme.dangerRose.withOpacity(0.4)),
                                    ),
                                    child: TextField(
                                      controller: _stopLossController,
                                      keyboardType: const TextInputType.numberWithOptions(decimal: true),
                                      style: const TextStyle(color: AppTheme.dangerRose, fontSize: 12, fontWeight: FontWeight.w900),
                                      decoration: const InputDecoration(border: InputBorder.none, isDense: true, contentPadding: EdgeInsets.symmetric(vertical: 4)),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 18),

                // Confirm & Send CTA Button (Matches User Screenshot)
                Container(
                  width: double.infinity,
                  height: 52,
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [
                        Color(0xFF00B4D8), // Vibrant Cyan
                        Color(0xFF0284C7), // Sky Blue
                        Color(0xFF6366F1), // Indigo
                        Color(0xFF8B5CF6), // Violet Purple
                      ],
                      begin: Alignment.centerLeft,
                      end: Alignment.centerRight,
                    ),
                    borderRadius: BorderRadius.circular(16),
                    boxShadow: const [
                      BoxShadow(
                        color: Color(0x6606B6D4),
                        blurRadius: 16,
                        offset: Offset(0, 4),
                      ),
                    ],
                  ),
                  child: ElevatedButton(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.transparent,
                      shadowColor: Colors.transparent,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                      padding: EdgeInsets.zero,
                    ),
                    onPressed: _executeOrder,
                    child: Text(
                      "⚡ Confirm $_tradeType & Send Order via Breeze →",
                      style: const TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.w900,
                        fontSize: 14.5,
                        letterSpacing: -0.2,
                      ),
                    ),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
