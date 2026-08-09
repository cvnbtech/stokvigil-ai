import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AppTheme {
  static const Color darkBackground = Color(0F0A0F1D);
  static const Color cardBackground = Color(0F111827);
  static const Color cardBorder = Color(0F1F2937);
  
  static const Color primaryEmerald = Color(0F10B981); // High Impact Emerald
  static const Color secondaryAmber = Color(0F59E0B);  // Med Impact Amber
  static const Color dangerRose = Color(0FEF4444);     // High Alert Rose
  static const Color textPrimary = Color(0FF9CA3AF);
  static const Color textSecondary = Color(0F6B7280);

  static ThemeData get darkTheme {
    return ThemeData(
      brightness: Brightness.dark,
      scaffoldBackgroundColor: darkBackground,
      primaryColor: primaryEmerald,
      colorScheme: const ColorScheme.dark(
        primary: primaryEmerald,
        secondary: secondaryAmber,
        surface: cardBackground,
        error: dangerRose,
      ),
      textTheme: GoogleFonts.interTextTheme(ThemeData.dark().textTheme).copyWith(
        displayLarge: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
        titleLarge: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700),
        bodyLarge: const TextStyle(color: textPrimary),
        bodyMedium: const TextStyle(color: textSecondary),
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: darkBackground,
        elevation: 0,
        centerTitle: false,
        iconTheme: IconThemeData(color: Colors.white),
      ),
      cardTheme: CardTheme(
        color: cardBackground,
        elevation: 2,
        shape: RoundedRectangleBorder(
          side: const BorderSide(color: cardBorder, width: 1),
          borderRadius: BorderRadius.circular(16),
        ),
      ),
      bottomNavigationBarTheme: const BottomNavigationBarThemeData(
        backgroundColor: cardBackground,
        selectedItemColor: primaryEmerald,
        unselectedItemColor: textSecondary,
        type: BottomNavigationBarType.fixed,
        elevation: 8,
      ),
    );
  }
}
