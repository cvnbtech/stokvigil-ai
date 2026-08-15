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

    // Supabase Rate Limit Exceptions (e.g. over_email_send_rate_limit / 429)
    if (errStr.contains('over_email_send_rate_limit') || errStr.contains('rate_limit') || errStr.contains('429')) {
      final match = RegExp(r'after\s+(\d+\s*(?:seconds?|minutes?))', caseSensitive: false).firstMatch(error.toString());
      if (match != null) {
        final timeStr = match.group(1);
        return "⏳ Please wait $timeStr before trying again.";
      }
      return "⏳ Please wait a minute before requesting another email or verification code.";
    }

    // Format / Syntax Errors
    if (error is FormatException || errStr.contains('formatexception')) {
      return "⚙️ Server data error. Please try refreshing again shortly.";
    }

    // Supabase Configuration / Placeholder / API Key Errors
    if (errStr.contains('your-supabase-project') ||
        errStr.contains('your-anon-key') ||
        errStr.contains('invalid api key') ||
        errStr.contains('apikey') ||
        errStr.contains('jwt') ||
        errStr.contains('unauthorized')) {
      return "🔑 Supabase API Keys not configured yet. Tap 'Continue with Google' or sign in to enter Demo Investor Mode.";
    }

    // Custom String Errors
    if (error is String) {
      return error;
    }

    // Clean raw AuthApiException(message: ..., statusCode: ...) wrappers
    final msgMatch = RegExp(r'message:\s*([^,)]+)', caseSensitive: false).firstMatch(error.toString());
    if (msgMatch != null) {
      final extractedMsg = msgMatch.group(1)?.trim();
      if (extractedMsg != null && extractedMsg.isNotEmpty) {
        return "⚠️ $extractedMsg";
      }
    }

    // Fallback cleaned error message
    final cleanMsg = error.toString()
        .replaceAll(RegExp(r'^(AuthApiException|Exception|AuthException|PostgrestException):\s*'), '')
        .trim();

    return "⚠️ $cleanMsg";
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
