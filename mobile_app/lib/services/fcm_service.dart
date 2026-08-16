import 'package:flutter/foundation.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'supabase_service.dart';
import 'api_service.dart';

class FcmService {
  static final FcmService _instance = FcmService._internal();
  factory FcmService() => _instance;
  FcmService._internal();

  FirebaseMessaging get messaging => FirebaseMessaging.instance;
  String? fcmToken;

  Future<void> initialize() async {
    try {
      await Firebase.initializeApp();
      NotificationSettings settings = await messaging.requestPermission(
        alert: true,
        badge: true,
        sound: true,
      );

      if (settings.authorizationStatus == AuthorizationStatus.authorized) {
        debugPrint('FCM User granted notification permission');
      }

      fcmToken = await messaging.getToken();
      debugPrint('FCM Device Token retrieved: $fcmToken');

      // Auto-sync token if user is already signed in
      final currentUser = SupabaseService().currentUser;
      if (currentUser != null && fcmToken != null) {
        await syncDeviceToken(currentUser.id);
      }

      // Listen for token refresh events
      FirebaseMessaging.instance.onTokenRefresh.listen((newToken) {
        fcmToken = newToken;
        debugPrint('FCM Token refreshed: $newToken');
        final user = SupabaseService().currentUser;
        if (user != null) {
          syncDeviceToken(user.id);
        }
      });

      FirebaseMessaging.onMessage.listen((RemoteMessage message) {
        debugPrint('Foreground FCM Alert received: ${message.notification?.title}');
      });
    } catch (e) {
      debugPrint('Firebase init error / fallback: $e');
    }
  }

  Future<String?> getDeviceToken() async {
    try {
      final token = await messaging.getToken();
      if (token != null) fcmToken = token;
      return fcmToken;
    } catch (e) {
      debugPrint('Error getting FCM token: $e');
      return fcmToken;
    }
  }

  Future<void> syncDeviceToken(String userId) async {
    try {
      final token = fcmToken ?? await getDeviceToken();
      if (token == null || token.isEmpty) {
        debugPrint('Cannot sync FCM token: token is null or empty');
        return;
      }

      debugPrint('Syncing FCM token to Supabase & Backend for user: $userId');
      
      // 1. Direct Supabase update for immediate database persistence
      await SupabaseService().updateProfile({
        'fcm_device_token': token,
        'fcm_enabled': true,
      });

      // 2. Notify Backend API
      await ApiService().registerDeviceToken(
        userId: userId,
        fcmToken: token,
        fcmEnabled: true,
      );
      
      debugPrint('✅ FCM device token successfully synced to database!');
    } catch (e) {
      debugPrint('Failed to sync FCM token: $e');
    }
  }
}
