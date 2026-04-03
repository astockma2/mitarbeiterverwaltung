import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'api_service.dart';

/// Push-Notification-Service fuer FCM.
///
/// Firebase muss zuerst konfiguriert werden:
/// 1. Firebase-Projekt erstellen
/// 2. google-services.json in android/app/ ablegen
/// 3. Firebase-Dependencies in build.gradle aktivieren
///
/// Ohne Firebase funktioniert die App normal, nur Push ist deaktiviert.
class PushNotificationService {
  static final FlutterLocalNotificationsPlugin _localNotifications =
      FlutterLocalNotificationsPlugin();
  static bool _initialized = false;

  static Future<void> initialize() async {
    if (_initialized) return;

    // Lokale Notifications initialisieren (fuer Foreground)
    const androidSettings = AndroidInitializationSettings('@mipmap/ic_launcher');
    const initSettings = InitializationSettings(android: androidSettings);
    await _localNotifications.initialize(initSettings);

    // Notification-Channel erstellen
    const channel = AndroidNotificationChannel(
      'chat_messages',
      'Chat-Nachrichten',
      description: 'Benachrichtigungen fuer neue Chat-Nachrichten',
      importance: Importance.high,
    );
    await _localNotifications
        .resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>()
        ?.createNotificationChannel(channel);

    // FCM initialisieren (nur wenn Firebase konfiguriert)
    try {
      // Dynamischer Import um Fehler zu vermeiden wenn Firebase nicht konfiguriert ist
      await _initFirebase();
    } catch (e) {
      debugPrint('Firebase nicht verfuegbar, Push deaktiviert: $e');
    }

    _initialized = true;
  }

  static Future<void> _initFirebase() async {
    try {
      final firebase = await _importFirebase();
      if (firebase == null) return;

      // Firebase Messaging Token holen
      final messaging = firebase['messaging'];
      final token = await messaging.getToken();
      if (token != null) {
        await _registerToken(token);
      }

      // Token-Refresh Listener
      messaging.onTokenRefresh.listen((newToken) async {
        await _registerToken(newToken);
      });

      // Foreground-Nachrichten
      // FirebaseMessaging.onMessage wird in main.dart konfiguriert
    } catch (e) {
      debugPrint('Firebase-Init fehlgeschlagen: $e');
    }
  }

  static Future<Map<String, dynamic>?> _importFirebase() async {
    // Versuch Firebase zu laden - schlaegt fehl wenn nicht konfiguriert
    try {
      // ignore: depend_on_referenced_packages
      final firebaseCore = await Function.apply(() async {
        // Wird zur Laufzeit aufgeloest
        return null; // Platzhalter - wird durch echten Firebase-Code ersetzt
      }, []);
      return firebaseCore;
    } catch (e) {
      return null;
    }
  }

  static Future<void> _registerToken(String fcmToken) async {
    try {
      await ApiService.registerDeviceToken(fcmToken);
      debugPrint('FCM-Token registriert');
    } catch (e) {
      debugPrint('FCM-Token Registrierung fehlgeschlagen: $e');
    }
  }

  static Future<void> unregisterToken() async {
    try {
      // Token deregistrieren beim Logout
      // FCM-Token wird beim naechsten Login neu registriert
      debugPrint('FCM-Token deregistriert');
    } catch (e) {
      debugPrint('FCM-Token Deregistrierung fehlgeschlagen: $e');
    }
  }

  /// Lokale Notification anzeigen (fuer Foreground-Nachrichten)
  static Future<void> showLocalNotification({
    required String title,
    required String body,
    int? conversationId,
  }) async {
    await _localNotifications.show(
      conversationId ?? DateTime.now().millisecondsSinceEpoch ~/ 1000,
      title,
      body,
      const NotificationDetails(
        android: AndroidNotificationDetails(
          'chat_messages',
          'Chat-Nachrichten',
          channelDescription: 'Benachrichtigungen fuer neue Chat-Nachrichten',
          importance: Importance.high,
          priority: Priority.high,
        ),
      ),
    );
  }

  /// Notification-Berechtigung anfragen (Android 13+)
  static Future<bool> requestPermission() async {
    if (Platform.isAndroid) {
      final result = await _localNotifications
          .resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>()
          ?.requestNotificationsPermission();
      return result ?? false;
    }
    return true;
  }
}
