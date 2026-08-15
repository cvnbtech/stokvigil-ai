import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AppTheme {
  // Web Portal Design Tokens (Vibrant Cyan-Violet Theme)
  static const Color darkBackground = Color(0xFF070913);
  static const Color cardBackground = Color(0xFF0D111E);
  static const Color cardBackground2 = Color(0xFF12172A);
  static const Color cardBorder = Color(0x15FFFFFF); // rgba(255,255,255,0.08)
  
  static const Color borderCyan = Color(0x5906B6D4);   // rgba(6,182,212,0.35)
  static const Color borderViolet = Color(0x598B5CF6); // rgba(139,92,246,0.35)
  
  static const Color cyan = Color(0xFF06B6D4);
  static const Color violet = Color(0xFF8B5CF6);
  static const Color primaryEmerald = Color(0xFF10B981);
  static const Color dangerRose = Color(0xFFEF4444);
  static const Color secondaryAmber = Color(0xFFF59E0B);
  
  static const Color textPrimary = Color(0xFFF8FAFC);
  static const Color textSecondary = Color(0xFF94A3B8);
  static const Color textMuted = Color(0xFF475569);
  static const Color surfaceDark = Color(0xFF1E293B);

  // Gradients
  static const LinearGradient primaryGradient = LinearGradient(
    colors: [cyan, Color(0xFF3B82F6), violet],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const LinearGradient logoGradient = LinearGradient(
    colors: [cyan, Color(0xFF38BDF8), violet],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const LinearGradient cardGradient = LinearGradient(
    colors: [Color(0xFF0D111E), Color(0xFF12172A)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static ThemeData get darkTheme {
    return ThemeData(
      brightness: Brightness.dark,
      scaffoldBackgroundColor: darkBackground,
      primaryColor: cyan,
      colorScheme: const ColorScheme.dark(
        primary: cyan,
        secondary: violet,
        surface: cardBackground,
        error: dangerRose,
      ),
      textTheme: GoogleFonts.interTextTheme(ThemeData.dark().textTheme).copyWith(
        displayLarge: const TextStyle(color: textPrimary, fontWeight: FontWeight.w900),
        titleLarge: const TextStyle(color: textPrimary, fontWeight: FontWeight.w800),
        bodyLarge: const TextStyle(color: textPrimary),
        bodyMedium: const TextStyle(color: textSecondary),
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: darkBackground,
        elevation: 0,
        centerTitle: false,
        iconTheme: IconThemeData(color: textPrimary),
      ),
      cardTheme: CardTheme(
        color: cardBackground,
        elevation: 4,
        shape: RoundedRectangleBorder(
          side: const BorderSide(color: cardBorder, width: 1),
          borderRadius: BorderRadius.circular(20),
        ),
      ),
      bottomNavigationBarTheme: const BottomNavigationBarThemeData(
        backgroundColor: Color(0xF6060812), // rgba(6,8,18,0.97)
        selectedItemColor: cyan,
        unselectedItemColor: textSecondary,
        type: BottomNavigationBarType.fixed,
        elevation: 12,
      ),
    );
  }
}
