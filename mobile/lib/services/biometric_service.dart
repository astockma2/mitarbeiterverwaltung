import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:local_auth/local_auth.dart';

class BiometricService {
  static final _auth = LocalAuthentication();
  static final _storage = FlutterSecureStorage();

  static const _keyUsername = 'bio_username';
  static const _keyPassword = 'bio_password';

  /// Prueft ob Biometrie auf dem Geraet verfuegbar ist.
  static Future<bool> isAvailable() async {
    try {
      final canCheck = await _auth.canCheckBiometrics;
      final isSupported = await _auth.isDeviceSupported();
      return canCheck && isSupported;
    } catch (_) {
      return false;
    }
  }

  /// Prueft ob gespeicherte Credentials vorhanden sind.
  static Future<bool> hasCredentials() async {
    final username = await _storage.read(key: _keyUsername);
    return username != null && username.isNotEmpty;
  }

  /// Speichert Credentials nach erfolgreichem Login.
  static Future<void> saveCredentials(String username, String password) async {
    await _storage.write(key: _keyUsername, value: username);
    await _storage.write(key: _keyPassword, value: password);
  }

  /// Loescht gespeicherte Credentials (z.B. bei Logout).
  static Future<void> clearCredentials() async {
    await _storage.delete(key: _keyUsername);
    await _storage.delete(key: _keyPassword);
  }

  /// Authentifiziert per Fingerabdruck und gibt Credentials zurueck.
  static Future<({String username, String password})?> authenticate() async {
    try {
      final authenticated = await _auth.authenticate(
        localizedReason: 'Bitte Fingerabdruck scannen zum Anmelden',
        options: const AuthenticationOptions(
          stickyAuth: true,
          biometricOnly: false,
        ),
      );
      if (!authenticated) return null;

      final username = await _storage.read(key: _keyUsername);
      final password = await _storage.read(key: _keyPassword);
      if (username == null || password == null) return null;

      return (username: username, password: password);
    } catch (_) {
      return null;
    }
  }
}
