import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../models/user.dart';
import '../models/time_entry.dart';
import '../models/shift.dart';
import '../models/absence.dart';
import '../models/chat.dart';

class ApiService {
  // Konfigurierbar via: flutter run --dart-define=API_URL=http://192.168.1.100:8000/api/v1
  static String baseUrl = const String.fromEnvironment(
    'API_URL',
    defaultValue: 'https://gui-martha-works-fda.trycloudflare.com/api/v1',
  );

  static final _storage = FlutterSecureStorage();

  // --- Token-Verwaltung ---

  static Future<String?> getToken() async {
    return await _storage.read(key: 'access_token');
  }

  static Future<void> saveTokens(String access, String refresh) async {
    await _storage.write(key: 'access_token', value: access);
    await _storage.write(key: 'refresh_token', value: refresh);
  }

  static Future<void> clearTokens() async {
    await _storage.delete(key: 'access_token');
    await _storage.delete(key: 'refresh_token');
  }

  static Future<Map<String, String>> _authHeaders() async {
    final token = await getToken();
    return {
      'Content-Type': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
  }

  // --- Generische HTTP-Methoden ---

  static Future<dynamic> _get(String path, {Map<String, String>? params}) async {
    try {
      final uri = Uri.parse('$baseUrl$path').replace(queryParameters: params);
      final headers = await _authHeaders();
      final response = await http.get(uri, headers: headers);
      return _handleResponse(response);
    } on ApiException {
      rethrow;
    } on SocketException {
      throw ApiException('Server nicht erreichbar', 0);
    } on TimeoutException {
      throw ApiException('Zeitüberschreitung – bitte erneut versuchen', 0);
    }
  }

  static Future<dynamic> _post(String path, {Map<String, dynamic>? body}) async {
    try {
      final uri = Uri.parse('$baseUrl$path');
      final headers = await _authHeaders();
      final response = await http.post(
        uri,
        headers: headers,
        body: body != null ? jsonEncode(body) : null,
      );
      return _handleResponse(response);
    } on ApiException {
      rethrow;
    } on SocketException {
      throw ApiException('Server nicht erreichbar', 0);
    } on TimeoutException {
      throw ApiException('Zeitüberschreitung – bitte erneut versuchen', 0);
    }
  }

  static dynamic _handleResponse(http.Response response) {
    if (response.statusCode == 401) {
      clearTokens();
      throw ApiException('Nicht authentifiziert', 401);
    }
    if (response.statusCode >= 400) {
      String message = 'Fehler';
      try {
        final data = jsonDecode(response.body);
        message = data['detail'] ?? 'Unbekannter Fehler';
      } catch (_) {}
      throw ApiException(message, response.statusCode);
    }
    if (response.body.isEmpty) return null;
    return jsonDecode(response.body);
  }

  // --- Auth ---

  static Future<Map<String, dynamic>> login(String username, String password) async {
    final uri = Uri.parse('$baseUrl/auth/login');
    final response = await http.post(
      uri,
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'username': username, 'password': password}),
    );
    final data = _handleResponse(response);
    await saveTokens(data['access_token'], data['refresh_token']);
    return data;
  }

  static Future<User> getMe() async {
    final data = await _get('/auth/me');
    return User.fromJson(data);
  }

  // --- Zeiterfassung ---

  static Future<ClockStatus> getClockStatus() async {
    final data = await _get('/time/status');
    return ClockStatus.fromJson(data);
  }

  static Future<void> clockIn() async {
    await _post('/time/clock-in', body: {});
  }

  static Future<void> clockOut({int breakMinutes = 30}) async {
    await _post('/time/clock-out', body: {'break_minutes': breakMinutes});
  }

  static Future<List<TimeEntry>> getTimeEntries({
    required String startDate,
    required String endDate,
  }) async {
    final data = await _get('/time/entries', params: {
      'start_date': startDate,
      'end_date': endDate,
    });
    return (data as List).map((e) => TimeEntry.fromJson(e)).toList();
  }

  static Future<DailySummary> getDailySummary(String day) async {
    final data = await _get('/time/daily', params: {'day': day});
    return DailySummary.fromJson(data);
  }

  static Future<Map<String, dynamic>> getMonthlySummary(int year, int month) async {
    final data = await _get('/time/monthly', params: {
      'year': year.toString(),
      'month': month.toString(),
    });
    return data;
  }

  // --- Dienstplan ---

  static Future<List<ShiftAssignment>> getMySchedule(
      String startDate, String endDate) async {
    final data = await _get('/shifts/my-schedule', params: {
      'start_date': startDate,
      'end_date': endDate,
    });
    return (data as List).map((e) => ShiftAssignment.fromJson(e)).toList();
  }

  // --- Abwesenheiten ---

  static Future<List<Absence>> getAbsences() async {
    final data = await _get('/absences');
    return (data as List).map((e) => Absence.fromJson(e)).toList();
  }

  static Future<void> createAbsence({
    required String type,
    required String startDate,
    required String endDate,
    String? notes,
  }) async {
    await _post('/absences', body: {
      'type': type,
      'start_date': startDate,
      'end_date': endDate,
      if (notes != null && notes.isNotEmpty) 'notes': notes,
    });
  }

  static Future<VacationBalance> getVacationBalance() async {
    final data = await _get('/absences/vacation-balance');
    return VacationBalance.fromJson(data);
  }
  // --- Chat ---

  static Future<List<ChatConversation>> getConversations() async {
    final data = await _get('/chat/conversations');
    return (data as List).map((e) => ChatConversation.fromJson(e)).toList();
  }

  static Future<Map<String, dynamic>> createConversation({
    required String type,
    required List<int> memberIds,
    String? name,
  }) async {
    return await _post('/chat/conversations', body: {
      'type': type,
      'member_ids': memberIds,
      if (name != null) 'name': name,
    });
  }

  static Future<List<ChatMessage>> getMessages(int conversationId) async {
    final data = await _get('/chat/conversations/$conversationId/messages');
    return (data as List).map((e) => ChatMessage.fromJson(e)).toList();
  }

  static Future<ChatMessage> sendChatMessage(int conversationId, String content) async {
    final data = await _post('/chat/conversations/$conversationId/messages', body: {
      'content': content,
    });
    return ChatMessage.fromJson(data);
  }

  static Future<List<ChatEmployee>> getChatEmployees() async {
    final data = await _get('/chat/employees');
    return (data as List).map((e) => ChatEmployee.fromJson(e)).toList();
  }

  static Future<List<Map<String, dynamic>>> getBots() async {
    try {
      final data = await _get('/chat/bots');
      return (data as List).map((e) => Map<String, dynamic>.from(e as Map)).toList();
    } catch (_) {
      return [];
    }
  }

  static String get wsUrl {
    return baseUrl.replaceFirst('http', 'ws').replaceFirst('/api/v1', '');
  }
}

class ApiException implements Exception {
  final String message;
  final int statusCode;

  ApiException(this.message, this.statusCode);

  @override
  String toString() => message;
}
