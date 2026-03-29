import 'dart:async';

import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../models/time_entry.dart';
import 'package:intl/intl.dart';

class TimeClockScreen extends StatefulWidget {
  const TimeClockScreen({super.key});

  @override
  TimeClockScreenState createState() => TimeClockScreenState();
}

class TimeClockScreenState extends State<TimeClockScreen> {
  ClockStatus? _status;
  DailySummary? _today;
  List<TimeEntry> _entries = [];
  bool _loading = true;
  bool _acting = false;
  int _breakMinutes = 30;
  Timer? _ticker;
  DateTime _now = DateTime.now();

  // Tages-Soll in Stunden (38.5h/Woche / 5 Tage)
  static const double _dailyTargetHours = 7.7;

  @override
  void initState() {
    super.initState();
    _ticker = Timer.periodic(const Duration(seconds: 1), (_) {
      setState(() => _now = DateTime.now());
    });
    _load();
  }

  @override
  void dispose() {
    _ticker?.cancel();
    super.dispose();
  }

  Future<void> reload() => _load();

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final now = DateFormat('yyyy-MM-dd').format(DateTime.now());
      final results = await Future.wait([
        ApiService.getClockStatus(),
        ApiService.getDailySummary(now),
        ApiService.getTimeEntries(startDate: now, endDate: now),
      ]);
      _status = results[0] as ClockStatus;
      _today = results[1] as DailySummary;
      _entries = results[2] as List<TimeEntry>;
    } catch (_) {}
    setState(() => _loading = false);
  }

  Future<void> _clockIn() async {
    setState(() => _acting = true);
    try {
      await ApiService.clockIn();
      await _load();
    } on ApiException catch (e) {
      _showError(e.message);
    }
    setState(() => _acting = false);
  }

  Future<void> _clockOut() async {
    final result = await showDialog<int>(
      context: context,
      builder: (ctx) => _BreakDialog(initialMinutes: _breakMinutes),
    );
    if (result == null) return;

    setState(() {
      _acting = true;
      _breakMinutes = result;
    });
    try {
      await ApiService.clockOut(breakMinutes: result);
      await _load();
    } on ApiException catch (e) {
      _showError(e.message);
    }
    setState(() => _acting = false);
  }

  void _showError(String msg) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(msg), backgroundColor: Colors.red),
    );
  }

  /// Berechnet die laufende Arbeitszeit seit Einstempeln
  Duration _elapsedSinceClockedIn() {
    if (_status?.since == null) return Duration.zero;
    try {
      final since = DateTime.parse(_status!.since!);
      return _now.difference(since);
    } catch (_) {
      return Duration.zero;
    }
  }

  /// Berechnet die verbleibende Arbeitszeit bis Tages-Soll erreicht
  Duration _remainingWorkTime() {
    final alreadyWorked = (_today?.totalHours ?? 0.0) * 60; // in Minuten
    final currentSessionMinutes = _elapsedSinceClockedIn().inMinutes;
    final totalWorkedMinutes = alreadyWorked + currentSessionMinutes;
    final targetMinutes = (_dailyTargetHours * 60).round();
    final remaining = targetMinutes - totalWorkedMinutes.round();
    return Duration(minutes: remaining > 0 ? remaining : 0);
  }

  String _formatDuration(Duration d) {
    final h = d.inHours;
    final m = d.inMinutes.remainder(60);
    final s = d.inSeconds.remainder(60);
    return '${h.toString().padLeft(2, '0')}:${m.toString().padLeft(2, '0')}:${s.toString().padLeft(2, '0')}';
  }

  @override
  Widget build(BuildContext context) {
    final isIn = _status?.clockedIn ?? false;

    return Scaffold(
      appBar: AppBar(title: const Text('Zeiterfassung')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  // Aktuelle Uhrzeit
                  Center(
                    child: Text(
                      DateFormat('HH:mm:ss').format(_now),
                      style: TextStyle(
                        fontSize: 40,
                        fontWeight: FontWeight.w200,
                        fontFamily: 'monospace',
                        color: Colors.grey.shade700,
                        letterSpacing: 4,
                      ),
                    ),
                  ),
                  Center(
                    child: Text(
                      DateFormat('EEEE, d. MMMM yyyy', 'de_DE').format(_now),
                      style: TextStyle(fontSize: 13, color: Colors.grey.shade500),
                    ),
                  ),
                  const SizedBox(height: 20),

                  // Grosser Stempel-Button
                  Center(
                    child: GestureDetector(
                      onTap: _acting ? null : (isIn ? _clockOut : _clockIn),
                      child: AnimatedContainer(
                        duration: const Duration(milliseconds: 300),
                        width: 170,
                        height: 170,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: isIn ? Colors.red : Colors.green,
                          boxShadow: [
                            BoxShadow(
                              color: (isIn ? Colors.red : Colors.green)
                                  .withValues(alpha: 0.3),
                              blurRadius: 20,
                              spreadRadius: 5,
                            ),
                          ],
                        ),
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(
                              isIn ? Icons.logout : Icons.login,
                              size: 44,
                              color: Colors.white,
                            ),
                            const SizedBox(height: 6),
                            Text(
                              isIn ? 'Ausstempeln' : 'Einstempeln',
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 15,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),

                  // Laufende Arbeitszeit & Restzeit
                  if (isIn && _status?.since != null) ...[
                    Card(
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      child: Padding(
                        padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 20),
                        child: Row(
                          children: [
                            // Laufende Zeit
                            Expanded(
                              child: Column(
                                children: [
                                  Icon(Icons.play_circle_outline, color: Colors.green.shade600, size: 22),
                                  const SizedBox(height: 4),
                                  Text(
                                    _formatDuration(_elapsedSinceClockedIn()),
                                    style: TextStyle(
                                      fontSize: 20,
                                      fontWeight: FontWeight.w700,
                                      fontFamily: 'monospace',
                                      color: Colors.green.shade700,
                                    ),
                                  ),
                                  const SizedBox(height: 2),
                                  Text(
                                    'Arbeitszeit',
                                    style: TextStyle(fontSize: 11, color: Colors.grey.shade600),
                                  ),
                                  Text(
                                    'seit ${_formatTime(_status!.since!)}',
                                    style: TextStyle(fontSize: 10, color: Colors.grey.shade400),
                                  ),
                                ],
                              ),
                            ),
                            Container(
                              width: 1,
                              height: 50,
                              color: Colors.grey.shade200,
                            ),
                            // Restzeit
                            Expanded(
                              child: Column(
                                children: [
                                  Icon(
                                    _remainingWorkTime().inMinutes > 0
                                        ? Icons.hourglass_bottom
                                        : Icons.check_circle_outline,
                                    color: _remainingWorkTime().inMinutes > 0
                                        ? Colors.orange.shade600
                                        : Colors.green.shade600,
                                    size: 22,
                                  ),
                                  const SizedBox(height: 4),
                                  Text(
                                    _remainingWorkTime().inMinutes > 0
                                        ? _formatDuration(_remainingWorkTime())
                                        : 'Erreicht!',
                                    style: TextStyle(
                                      fontSize: 20,
                                      fontWeight: FontWeight.w700,
                                      fontFamily: 'monospace',
                                      color: _remainingWorkTime().inMinutes > 0
                                          ? Colors.orange.shade700
                                          : Colors.green.shade700,
                                    ),
                                  ),
                                  const SizedBox(height: 2),
                                  Text(
                                    'Restzeit',
                                    style: TextStyle(fontSize: 11, color: Colors.grey.shade600),
                                  ),
                                  Text(
                                    'Soll: ${_dailyTargetHours.toStringAsFixed(1)}h',
                                    style: TextStyle(fontSize: 10, color: Colors.grey.shade400),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 8),
                  ],

                  // Nicht eingestempelt: Hinweis
                  if (!isIn)
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 4),
                      child: Center(
                        child: Text(
                          'Nicht eingestempelt',
                          style: TextStyle(fontSize: 13, color: Colors.grey.shade500),
                        ),
                      ),
                    ),
                  const SizedBox(height: 16),

                  // Tagesuebersicht
                  if (_today != null)
                    Card(
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.spaceAround,
                          children: [
                            _statCol('Stunden', '${_today!.totalHours}h'),
                            _statCol('Pause', '${_today!.totalBreakMinutes} Min'),
                            _statCol('Eintraege', '${_today!.entryCount}'),
                          ],
                        ),
                      ),
                    ),
                  const SizedBox(height: 24),

                  // Heutige Eintraege
                  Text(
                    'Heutige Eintraege',
                    style: TextStyle(
                      fontWeight: FontWeight.w600,
                      fontSize: 15,
                      color: Colors.grey.shade800,
                    ),
                  ),
                  const SizedBox(height: 8),
                  if (_entries.isEmpty)
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(24),
                        child: Center(
                          child: Text(
                            'Noch keine Eintraege heute',
                            style: TextStyle(color: Colors.grey.shade400),
                          ),
                        ),
                      ),
                    ),
                  ..._entries.map((e) => Card(
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                        child: ListTile(
                          leading: Container(
                            width: 40,
                            height: 40,
                            decoration: BoxDecoration(
                              color: Colors.blue.shade50,
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: Icon(Icons.access_time, color: Colors.blue.shade700),
                          ),
                          title: Text(
                            '${_formatTime(e.clockIn.toIso8601String())} — ${e.clockOut != null ? _formatTime(e.clockOut!.toIso8601String()) : "offen"}',
                            style: const TextStyle(fontWeight: FontWeight.w500),
                          ),
                          subtitle: Text(
                            'Pause: ${e.breakMinutes} Min${e.netHours != null ? " | Netto: ${e.netHours}h" : ""}',
                          ),
                          trailing: e.surcharges.isNotEmpty
                              ? Chip(
                                  label: Text(
                                    e.surcharges.map((s) => s.type).join(', '),
                                    style: const TextStyle(fontSize: 10),
                                  ),
                                  backgroundColor: Colors.purple.shade50,
                                )
                              : null,
                        ),
                      )),
                ],
              ),
            ),
    );
  }

  Widget _statCol(String label, String value) {
    return Column(
      children: [
        Text(value, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
        const SizedBox(height: 2),
        Text(label, style: TextStyle(fontSize: 11, color: Colors.grey.shade500)),
      ],
    );
  }

  String _formatTime(String iso) {
    try {
      final dt = DateTime.parse(iso);
      return DateFormat('HH:mm').format(dt);
    } catch (_) {
      return iso;
    }
  }
}

class _BreakDialog extends StatefulWidget {
  final int initialMinutes;
  const _BreakDialog({required this.initialMinutes});

  @override
  State<_BreakDialog> createState() => _BreakDialogState();
}

class _BreakDialogState extends State<_BreakDialog> {
  late int _minutes;

  @override
  void initState() {
    super.initState();
    _minutes = widget.initialMinutes;
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Pause eingeben'),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text('Pausenminuten: $_minutes'),
          Slider(
            value: _minutes.toDouble(),
            min: 0,
            max: 120,
            divisions: 24,
            label: '$_minutes Min',
            onChanged: (v) => setState(() => _minutes = v.round()),
          ),
          Wrap(
            spacing: 8,
            children: [0, 15, 30, 45, 60].map((m) {
              return ChoiceChip(
                label: Text('$m Min'),
                selected: _minutes == m,
                onSelected: (_) => setState(() => _minutes = m),
              );
            }).toList(),
          ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Abbrechen'),
        ),
        FilledButton(
          onPressed: () => Navigator.pop(context, _minutes),
          child: const Text('Ausstempeln'),
        ),
      ],
    );
  }
}
