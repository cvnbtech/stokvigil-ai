import 'package:flutter/foundation.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';

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
        debugPrint('FCM User granted permission');
      }

      fcmToken = await messaging.getToken();

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
}
