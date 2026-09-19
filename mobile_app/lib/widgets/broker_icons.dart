import 'package:flutter/material.dart';

/// Pixel-perfect, high-fidelity brand icon for ICICI Direct
class IciciDirectLogo extends StatelessWidget {
  final double size;

  const IciciDirectLogo({super.key, this.size = 20});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFFA32338), Color(0xFFF37021)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(size * 0.28),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFFF37021).withOpacity(0.3),
            blurRadius: 4,
            offset: const Offset(0, 1),
          ),
        ],
      ),
      child: Center(
        child: Text(
          "i",
          style: TextStyle(
            color: Colors.white,
            fontSize: size * 0.72,
            fontWeight: FontWeight.w900,
            fontFamily: 'serif',
            height: 1.0,
          ),
        ),
      ),
    );
  }
}

/// Pixel-perfect, high-fidelity brand icon for Zerodha Kite (Origami Kite Facets)
class ZerodhaLogo extends StatelessWidget {
  final double size;

  const ZerodhaLogo({super.key, this.size = 20});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: const Color(0xFF181F30),
        borderRadius: BorderRadius.circular(size * 0.28),
        border: Border.all(color: Colors.white.withOpacity(0.08), width: 0.8),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(size * 0.28),
        child: CustomPaint(
          size: Size(size, size),
          painter: _ZerodhaKitePainter(),
        ),
      ),
    );
  }
}

class _ZerodhaKitePainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final w = size.width;
    final h = size.height;

    final topPt = Offset(w * 0.50, h * 0.16);
    final bottomPt = Offset(w * 0.50, h * 0.84);
    final leftPt = Offset(w * 0.20, h * 0.44);
    final rightPt = Offset(w * 0.80, h * 0.44);
    final centerPt = Offset(w * 0.50, h * 0.52);

    // Top-right facet (Kite Blue)
    final pTR = Paint()..color = const Color(0xFF387ED1);
    final pathTR = Path()..moveTo(topPt.dx, topPt.dy)..lineTo(rightPt.dx, rightPt.dy)..lineTo(centerPt.dx, centerPt.dy)..close();
    canvas.drawPath(pathTR, pTR);

    // Bottom-right facet (Deep Blue)
    final pBR = Paint()..color = const Color(0xFF1C5393);
    final pathBR = Path()..moveTo(centerPt.dx, centerPt.dy)..lineTo(rightPt.dx, rightPt.dy)..lineTo(bottomPt.dx, bottomPt.dy)..close();
    canvas.drawPath(pathBR, pBR);

    // Top-left facet (Vibrant Orange)
    final pTL = Paint()..color = const Color(0xFFEA532A);
    final pathTL = Path()..moveTo(topPt.dx, topPt.dy)..lineTo(leftPt.dx, leftPt.dy)..lineTo(centerPt.dx, centerPt.dy)..close();
    canvas.drawPath(pathTL, pTL);

    // Bottom-left facet (Deep Orange)
    final pBL = Paint()..color = const Color(0xFFC4340F);
    final pathBL = Path()..moveTo(centerPt.dx, centerPt.dy)..lineTo(leftPt.dx, leftPt.dy)..lineTo(bottomPt.dx, bottomPt.dy)..close();
    canvas.drawPath(pathBL, pBL);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

/// Pixel-perfect, high-fidelity brand icon for Angel One (Flame Wing Chevron)
class AngelOneLogo extends StatelessWidget {
  final double size;

  const AngelOneLogo({super.key, this.size = 20});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: const Color(0xFF111728),
        borderRadius: BorderRadius.circular(size * 0.28),
        border: Border.all(color: Colors.white.withOpacity(0.08), width: 0.8),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(size * 0.28),
        child: CustomPaint(
          size: Size(size, size),
          painter: _AngelOnePainter(),
        ),
      ),
    );
  }
}

class _AngelOnePainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final w = size.width;
    final h = size.height;

    // Wing chevron A
    final paint = Paint()
      ..shader = const LinearGradient(
        colors: [Color(0xFFFF3E30), Color(0xFFFF851B)],
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
      ).createShader(Rect.fromLTWH(0, 0, w, h));

    final path = Path()
      ..moveTo(w * 0.24, h * 0.72)
      ..lineTo(w * 0.50, h * 0.22)
      ..lineTo(w * 0.76, h * 0.72)
      ..lineTo(w * 0.62, h * 0.72)
      ..lineTo(w * 0.50, h * 0.48)
      ..lineTo(w * 0.38, h * 0.72)
      ..close();

    canvas.drawPath(path, paint);

    // Inner spark dot
    final dotPaint = Paint()..color = const Color(0xFFFF851B);
    canvas.drawCircle(Offset(w * 0.50, h * 0.64), w * 0.085, dotPaint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
