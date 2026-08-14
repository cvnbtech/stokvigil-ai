import 'package:flutter/foundation.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import '../models/models.dart';

class SupabaseService {
  static final SupabaseService _instance = SupabaseService._internal();
  factory SupabaseService() => _instance;
  SupabaseService._internal();

  static const String supabaseUrl = String.fromEnvironment(
    'SUPABASE_URL',
    defaultValue: "https://your-supabase-project.supabase.co",
  );
  static const String supabaseAnonKey = String.fromEnvironment(
    'SUPABASE_ANON_KEY',
    defaultValue: "your-anon-key",
  );

  SupabaseClient get client => Supabase.instance.client;
  User? get currentUser => client.auth.currentUser;

  static Future<void> initialize() async {
    try {
      await Supabase.initialize(
        url: supabaseUrl,
        anonKey: supabaseAnonKey,
      );
    } catch (e) {
      debugPrint("Supabase init error / demo mode: $e");
    }
  }

  Future<AuthResponse> signUpWithEmail(String email, String password) async {
    return await client.auth.signUp(email: email, password: password);
  }

  Future<AuthResponse> signInWithEmail(String email, String password) async {
    return await client.auth.signInWithPassword(email: email, password: password);
  }

  Future<void> signOut() async {
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
