import 'package:flutter/material.dart';
import '../models/user.dart';
import 'api_service.dart';
import 'biometric_service.dart';

class AuthProvider extends ChangeNotifier {
  User? _user;
  bool _loading = true;

  User? get user => _user;
  bool get loading => _loading;
  bool get isLoggedIn => _user != null;

  Future<void> init() async {
    _loading = true;
    notifyListeners();
    try {
      final token = await ApiService.getToken();
      if (token != null) {
        _user = await ApiService.getMe();
      }
    } catch (_) {
      _user = null;
      await ApiService.clearTokens();
    }
    _loading = false;
    notifyListeners();
  }

  Future<void> login(String username, String password) async {
    await ApiService.login(username, password);
    _user = await ApiService.getMe();

    // Credentials fuer Biometrie-Login speichern
    if (await BiometricService.isAvailable()) {
      await BiometricService.saveCredentials(username, password);
    }

    notifyListeners();
  }

  Future<void> loginWithBiometric() async {
    final credentials = await BiometricService.authenticate();
    if (credentials == null) {
      throw ApiException('Biometrie-Authentifizierung fehlgeschlagen', 0);
    }
    await login(credentials.username, credentials.password);
  }

  Future<void> logout() async {
    await ApiService.clearTokens();
    // Biometrie-Credentials bewusst NICHT loeschen,
    // damit der Fingerabdruck-Login nach Logout weiterhin funktioniert
    _user = null;
    notifyListeners();
  }
}
