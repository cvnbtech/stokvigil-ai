import 'dart:async';
import 'dart:io';
import 'package:flutter/material.dart';
import '../config/theme.dart';

class ErrorHandler {
  /// Converts raw technical exceptions into clean, human-readable UI messages.
  static String parseError(dynamic error) {
    if (error == null) return "An unexpected error occurred. Please try again.";

    final errStr = error.toString().toLowerCase();

    // Network / Socket / Timeout Errors
    if (error is SocketException || errStr.contains('socketexception') || errStr.contains('failed host lookup')) {
      return "📶 Network offline. Please check your internet connection.";
    }
    if (error is TimeoutException || errStr.contains('timeoutexception') || errStr.contains('timed out')) {
      return "⏳ Server connection timed out. Please pull down to refresh.";
    }

    // Supabase Auth Exceptions
    if (errStr.contains('invalid login credentials') || errStr.contains('invalid_credentials')) {
      return "🔑 Invalid email or password. Please check your details and try again.";
    }
    if (errStr.contains('user already registered') || errStr.contains('email_exists')) {
      return "👤 An account with this email already exists. Try signing in.";
    }
    if (errStr.contains('password should be at least')) {
      return "🔒 Password must be at least 6 characters long.";
    }

    // Credentials / Session Token Errors
    if (errStr.contains('session token expired') || errStr.contains('token expired')) {
      return "🔑 ICICI Breeze Session token has expired. Please update your morning session key.";
    }

    // Format / Syntax Errors
    if (error is FormatException || errStr.contains('formatexception')) {
      return "⚙️ Server data error. Please try refreshing again shortly.";
    }

    // Custom String Errors
    if (error is String) {
      return error;
    }

    // Fallback cleaned error message
    final cleanMsg = error.toString().replaceAll(RegExp(r'^(Exception|AuthException|PostgrestException):\s*'), '');
    if (cleanMsg.length > 80) {
      return "Unable to complete request. Please verify your connection and try again.";
    }
    return cleanMsg;
  }

  /// Displays a clean styled SnackBar with user-friendly error messages.
  static void showErrorSnackBar(BuildContext context, dynamic error) {
    final message = parseError(error);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            const Icon(Icons.error_outline, color: Colors.white, size: 20),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                message,
                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13),
              ),
            ),
          ],
        ),
        backgroundColor: AppTheme.dangerRose,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        duration: const Duration(seconds: 4),
      ),
    );
  }

  /// Displays a clean success SnackBar.
  static void showSuccessSnackBar(BuildContext context, String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            const Icon(Icons.check_circle_outline, color: Colors.black, size: 20),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                message,
                style: const TextStyle(color: Colors.black, fontWeight: FontWeight.bold, fontSize: 13),
              ),
            ),
          ],
        ),
        backgroundColor: AppTheme.primaryEmerald,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        duration: const Duration(seconds: 3),
      ),
    );
  }
}
