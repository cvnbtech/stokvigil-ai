import 'package:flutter/foundation.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import '../models/models.dart';

class SupabaseService {
  static final SupabaseService _instance = SupabaseService._internal();
  factory SupabaseService() => _instance;
  SupabaseService._internal();

  static String supabaseUrl = const String.fromEnvironment(
    'SUPABASE_URL',
    defaultValue: "https://your-supabase-project.supabase.co",
  );
  static String supabaseAnonKey = const String.fromEnvironment(
    'SUPABASE_ANON_KEY',
    defaultValue: "your-anon-key",
  );

  static bool get isConfigured =>
      supabaseUrl.isNotEmpty &&
      supabaseUrl != "https://your-supabase-project.supabase.co" &&
      supabaseAnonKey.isNotEmpty &&
      supabaseAnonKey != "your-anon-key";

  SupabaseClient get client => Supabase.instance.client;
  User? get currentUser => isConfigured ? Supabase.instance.client.auth.currentUser : null;

  static Future<void> initialize() async {
    try {
      await Supabase.initialize(
        url: isConfigured ? supabaseUrl : "https://your-supabase-project.supabase.co",
        anonKey: isConfigured ? supabaseAnonKey : "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.dummy",
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
      updates['updated_at'] = DateTime.now().toIso8601String();
      await client.from('profiles').update(updates).eq('id', user.id);
      return true;
    } catch (e) {
      debugPrint("Error updating profile: $e");
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

  Future<bool> addToWatchlist(String symbol) async {
    final user = currentUser;
    if (user == null || !isConfigured) return false;
    try {
      await client.from('user_watchlists').upsert({
        'user_id': user.id,
        'symbol': symbol.toUpperCase(),
        'is_auto_synced': false,
      });
      return true;
    } catch (e) {
      debugPrint("Error adding to watchlist: $e");
      return false;
    }
  }

  Future<bool> removeFromWatchlist(String id) async {
    final user = currentUser;
    if (user == null || !isConfigured) return false;
    try {
      await client.from('user_watchlists').delete().eq('id', id);
      return true;
    } catch (e) {
      debugPrint("Error removing from watchlist: $e");
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
      return data;
    } catch (e) {
      debugPrint("Error checking credentials: $e");
      return null;
    }
  }
}
