import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import '../models/models.dart';
import 'api_service.dart';

class SupabaseService {
  static final SupabaseService _instance = SupabaseService._internal();
  factory SupabaseService() => _instance;
  SupabaseService._internal();

  static String supabaseUrl = const String.fromEnvironment(
    'SUPABASE_URL',
    defaultValue: "",
  );
  static String supabaseAnonKey = const String.fromEnvironment(
    'SUPABASE_ANON_KEY',
    defaultValue: "",
  );

  static bool get isConfigured =>
      supabaseUrl.isNotEmpty &&
      !supabaseUrl.contains("your-supabase-project") &&
      supabaseAnonKey.isNotEmpty &&
      !supabaseAnonKey.contains("your-anon-key") &&
      !supabaseAnonKey.contains("dummy");

  SupabaseClient get client => Supabase.instance.client;
  User? get currentUser {
    if (!isConfigured) return null;
    try {
      return Supabase.instance.client.auth.currentUser;
    } catch (_) {
      return null;
    }
  }

  static Future<void> initialize() async {
    if (!isConfigured) {
      debugPrint("Supabase credentials not configured; skipping initialization.");
      return;
    }
    try {
      await Supabase.initialize(
        url: supabaseUrl,
        anonKey: supabaseAnonKey,
      );
    } catch (e) {
      debugPrint("Supabase init info: $e");
    }
  }

  Future<AuthResponse?> signUpWithEmail(String email, String password) async {
    if (!isConfigured) return null;
    return await client.auth.signUp(
      email: email,
      password: password,
      emailRedirectTo: kIsWeb ? null : 'io.supabase.flutter://login-callback',
    );
  }

  Future<AuthResponse?> signInWithEmail(String email, String password) async {
    if (!isConfigured) return null;
    return await client.auth.signInWithPassword(email: email, password: password);
  }

  Future<void> resetPasswordForEmail(String email) async {
    if (!isConfigured) return;
    await client.auth.resetPasswordForEmail(email);
  }

  Future<bool> signInWithGoogle() async {
    if (!isConfigured) return false;
    try {
      return await client.auth.signInWithOAuth(
        OAuthProvider.google,
        redirectTo: kIsWeb ? null : 'io.supabase.flutter://login-callback',
      );
    } catch (e) {
      debugPrint("Error signing in with Google OAuth: $e");
      return false;
    }
  }

  Future<void> signOut() async {
    if (!isConfigured) return;
    await client.auth.signOut();
  }

  Future<UserProfile?> fetchUserProfile() async {
    final user = currentUser;
    if (user == null || !isConfigured) return null;
    try {
      final data = await client.from('profiles').select().eq('id', user.id).maybeSingle();
      if (data == null) return null;
      return UserProfile.fromJson(data);
    } catch (e) {
      debugPrint("Error fetching profile: $e");
      return UserProfile(id: user.id, email: user.email ?? '', telegramEnabled: false);
    }
  }

  Future<bool> updateProfile(Map<String, dynamic> updates) async {
    final user = currentUser;
    if (user == null || !isConfigured) return false;
    try {
      final sanitizedUpdates = Map<String, dynamic>.from(updates);
      sanitizedUpdates['updated_at'] = DateTime.now().toIso8601String();

      // 1. Primary: Direct targeted UPDATE (Evaluates standard UPDATE RLS policy)
      final res = await client
          .from('profiles')
          .update(sanitizedUpdates)
          .eq('id', user.id)
          .select();

      if (res.isNotEmpty) {
        return true;
      }

      // 2. Fallback: If profile row was not yet created, attach user identity and upsert
      sanitizedUpdates['id'] = user.id;
      if (user.email != null && user.email!.isNotEmpty) {
        sanitizedUpdates['email'] = user.email!;
      }
      await client.from('profiles').upsert(sanitizedUpdates);
      return true;
    } catch (e) {
      debugPrint("Error updating profile in Supabase: $e");
      return false;
    }
  }

  // Real-time Alerts Streams and Queries
  Stream<List<StokAlert>> streamAlerts() {
    final user = currentUser;
    if (user == null || !isConfigured) return Stream.value([]);
    try {
      return client
          .from('stok_alerts')
          .stream(primaryKey: ['id'])
          .eq('user_id', user.id)
          .order('created_at', ascending: false)
          .map((data) => data.map((json) => StokAlert.fromJson(json)).toList());
    } catch (e) {
      debugPrint("Error streaming alerts: $e");
      return Stream.value([]);
    }
  }

  Future<List<StokAlert>> fetchAlerts() async {
    final user = currentUser;
    if (user == null || !isConfigured) return [];
    try {
      final data = await client
          .from('stok_alerts')
          .select()
          .eq('user_id', user.id)
          .order('created_at', ascending: false);
      return (data as List).map((json) => StokAlert.fromJson(json)).toList();
    } catch (e) {
      debugPrint("Error fetching alerts from Supabase: $e");
      return [];
    }
  }

  // Real-time Watchlists Streams and Queries
  Stream<List<Map<String, dynamic>>> streamWatchlist() {
    final user = currentUser;
    if (user == null || !isConfigured) return Stream.value([]);
    try {
      return client
          .from('user_watchlists')
          .stream(primaryKey: ['id'])
          .eq('user_id', user.id)
          .order('created_at', ascending: false);
    } catch (e) {
      debugPrint("Error streaming watchlist: $e");
      return Stream.value([]);
    }
  }

  Future<List<Map<String, dynamic>>> fetchWatchlist() async {
    final user = currentUser;
    if (user == null || !isConfigured) return [];
    try {
      final data = await client
          .from('user_watchlists')
          .select()
          .eq('user_id', user.id)
          .order('created_at', ascending: false);
      return List<Map<String, dynamic>>.from(data);
    } catch (e) {
      debugPrint("Error fetching watchlist: $e");
      return [];
    }
  }

  Future<bool> addToWatchlist(String symbol, {bool isAutoSynced = false}) async {
    final user = currentUser;
    if (user == null || !isConfigured) return false;
    try {
      await client.from('user_watchlists').upsert({
        'user_id': user.id,
        'symbol': symbol.toUpperCase(),
        'is_auto_synced': isAutoSynced,
      });
      return true;
    } catch (e) {
      debugPrint("Error adding to watchlist: $e");
      return false;
    }
  }

  Future<bool> batchAddToWatchlist(List<String> symbols, {bool isAutoSynced = false}) async {
    final user = currentUser;
    if (user == null || !isConfigured || symbols.isEmpty) return false;
    try {
      final records = symbols
          .where((s) => s.trim().isNotEmpty)
          .map((s) => {
                'user_id': user.id,
                'symbol': s.trim().toUpperCase(),
                'is_auto_synced': isAutoSynced,
              })
          .toList();
      if (records.isEmpty) return true;
      await client.from('user_watchlists').upsert(
        records,
        onConflict: 'user_id,symbol',
      );
      return true;
    } catch (e) {
      debugPrint("Error batch adding to watchlist: $e");
      return false;
    }
  }

  Future<bool> removeFromWatchlist(dynamic id, [String? symbol]) async {
    final user = currentUser;
    if (user == null || !isConfigured) return true;
    try {
      if (id != null && id.toString().isNotEmpty) {
        await client.from('user_watchlists').delete().eq('id', id);
        return true;
      }
      if (symbol != null && symbol.isNotEmpty) {
        await client.from('user_watchlists').delete().eq('user_id', user.id).eq('symbol', symbol.toUpperCase());
        return true;
      }
      return true;
    } catch (e) {
      debugPrint("Error removing from watchlist by ID: $e");
      if (symbol != null && symbol.isNotEmpty) {
        try {
          await client.from('user_watchlists').delete().eq('user_id', user.id).eq('symbol', symbol.toUpperCase());
          return true;
        } catch (e2) {
          debugPrint("Fallback error removing from watchlist by symbol: $e2");
        }
      }
      return false;
    }
  }

  // ICICI Credentials Status
  Future<Map<String, dynamic>?> checkCredentials() async {
    final user = currentUser;
    if (user == null || !isConfigured) return null;
    try {
      final data = await client
          .from('user_credentials')
          .select('token_date, updated_at')
          .eq('user_id', user.id)
          .maybeSingle();
      if (data == null) return null;

      final todayStr = DateTime.now().toIso8601String().split('T')[0];
      final tokenDate = data['token_date']?.toString();
      final isValidToday = tokenDate == todayStr;

      return {
        ...data,
        'is_valid_today': isValidToday,
      };
    } catch (e) {
      debugPrint("Error checking credentials: $e");
      return null;
    }
  }

  // Secure Vault Save for ICICI Credentials (Delegated to Backend AES-256 Vault)
  Future<bool> saveIciciCredentials({
    required String userId,
    required String appKey,
    required String secretKey,
    required String sessionToken,
  }) async {
    if (!isConfigured) return true; // Offline test mode returns true
    try {
      // Delegate to backend API to ensure server-side Fernet AES-256 encryption
      return await ApiService().saveIciciCredentials(
        userId: userId,
        appKey: appKey,
        secretKey: secretKey,
        sessionToken: sessionToken,
      );
    } catch (e) {
      debugPrint("Credential save error: $e");
      return false;
    }
  }

  // Complete User Account Cascade Deletion
  Future<bool> deleteAccountCascade() async {
    final user = currentUser;
    if (user == null || !isConfigured) return true;
    try {
      await client.from('user_credentials').delete().eq('user_id', user.id);
      await client.from('user_watchlists').delete().eq('user_id', user.id);
      await client.from('user_devices').delete().eq('user_id', user.id);
      try {
        await client.from('user_profiles').delete().eq('id', user.id);
      } catch (_) {}
      return true;
    } catch (e) {
      debugPrint("Error cascading deletion: $e");
      return false;
    }
  }
}
