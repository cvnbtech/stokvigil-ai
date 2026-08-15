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
    if (user == null) return null;
    try {
      final data = await client.from('profiles').select().eq('id', user.id).single();
      return UserProfile.fromJson(data);
    } catch (e) {
      debugPrint("Error fetching profile: $e");
      return UserProfile(id: user.id, email: user.email ?? '', telegramEnabled: false);
    }
  }
}
