import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../models/shift.dart';
import 'package:intl/intl.dart';

class ShiftPlanScreen extends StatefulWidget {
  const ShiftPlanScreen({super.key});

  @override
  State<ShiftPlanScreen> createState() => _ShiftPlanScreenState();
}

class _ShiftPlanScreenState extends State<ShiftPlanScreen> {
  List<ShiftAssignment> _shifts = [];
  bool _loading = true;
  late DateTime _currentMonth;

  final _weekdays = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'];

  // Schichtfarben
  static const _shiftColors = {
    'D': Color(0xFFDBEAFE), // Normaldienst - Blau
    'F': Color(0xFFDCFCE7), // Frueh - Gruen
    'S': Color(0xFFFEF3C7), // Spaet - Gelb
    'N': Color(0xFFE0E7FF), // Nacht - Lila
  };
  static const _shiftTextColors = {
    'D': Color(0xFF1E40AF),
    'F': Color(0xFF166534),
    'S': Color(0xFF92400E),
    'N': Color(0xFF3730A3),
  };

  @override
  void initState() {
    super.initState();
    final now = DateTime.now();
    _currentMonth = DateTime(now.year, now.month);
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final start = DateFormat('yyyy-MM-dd').format(_currentMonth);
      final lastDay = DateTime(_currentMonth.year, _currentMonth.month + 1, 0);
      final end = DateFormat('yyyy-MM-dd').format(lastDay);
      _shifts = await ApiService.getMySchedule(start, end);
    } catch (_) {
      _shifts = [];
    }
    setState(() => _loading = false);
  }

  void _changeMonth(int delta) {
    setState(() {
      _currentMonth = DateTime(_currentMonth.year, _currentMonth.month + delta);
    });
    _load();
  }

  @override
  Widget build(BuildContext context) {
    final monthLabel = DateFormat('MMMM yyyy', 'de_DE').format(_currentMonth);

    return Scaffold(
      appBar: AppBar(title: const Text('Mein Dienstplan')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  // Monatsnavigation
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      IconButton(
                        icon: const Icon(Icons.chevron_left),
                        onPressed: () => _changeMonth(-1),
                      ),
                      Text(
                        monthLabel,
                        style: const TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      IconButton(
                        icon: const Icon(Icons.chevron_right),
                        onPressed: () => _changeMonth(1),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),

                  // Schichtanzahl
                  Center(
                    child: Text(
                      '${_shifts.length} Schichten',
                      style:
                          TextStyle(color: Colors.grey.shade600, fontSize: 13),
                    ),
                  ),
                  const SizedBox(height: 16),

                  // Kalender-Grid
                  _buildCalendar(),
                  const SizedBox(height: 24),

                  // Schichtliste
                  if (_shifts.isNotEmpty) ...[
                    Text(
                      'Schichtliste',
                      style: TextStyle(
                        fontWeight: FontWeight.w600,
                        fontSize: 15,
                        color: Colors.grey.shade800,
                      ),
                    ),
                    const SizedBox(height: 8),
                    ..._shifts.map((s) => _buildShiftTile(s)),
                  ],
                  if (_shifts.isEmpty)
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(32),
                        child: Center(
                          child: Text(
                            'Kein Dienstplan fuer diesen Monat',
                            style: TextStyle(color: Colors.grey.shade400),
                          ),
                        ),
                      ),
                    ),
                ],
              ),
            ),
    );
  }

  Widget _buildCalendar() {
    final daysInMonth =
        DateTime(_currentMonth.year, _currentMonth.month + 1, 0).day;
    // Montag = 0
    int firstWeekday =
        DateTime(_currentMonth.year, _currentMonth.month, 1).weekday - 1;

    // Shift-Map
    final shiftMap = <String, ShiftAssignment>{};
    for (final s in _shifts) {
      shiftMap[s.date] = s;
    }

    final today = DateFormat('yyyy-MM-dd').format(DateTime.now());

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(8),
        child: Column(
          children: [
            // Wochentag-Header
            Row(
              children: _weekdays
                  .map((d) => Expanded(
                        child: Center(
                          child: Text(
                            d,
                            style: TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.w600,
                              color: Colors.grey.shade600,
                            ),
                          ),
                        ),
                      ))
                  .toList(),
            ),
            const SizedBox(height: 4),
            // Kalender-Zeilen
            ...List.generate(
              ((firstWeekday + daysInMonth + 6) ~/ 7),
              (week) {
                return Row(
                  children: List.generate(7, (col) {
                    final dayIndex = week * 7 + col - firstWeekday + 1;
                    if (dayIndex < 1 || dayIndex > daysInMonth) {
                      return Expanded(child: SizedBox(height: 72));
                    }

                    final dateStr = DateFormat('yyyy-MM-dd').format(
                      DateTime(
                          _currentMonth.year, _currentMonth.month, dayIndex),
                    );
                    final shift = shiftMap[dateStr];
                    final isToday = dateStr == today;
                    final isWeekend = col >= 5;

                    return Expanded(
                      child: Container(
                        height: 72,
                        margin: const EdgeInsets.all(1),
                        decoration: BoxDecoration(
                          border: isToday
                              ? Border.all(color: Colors.blue, width: 2)
                              : Border.all(color: Colors.grey.shade200),
                          borderRadius: BorderRadius.circular(6),
                          color: isWeekend ? Colors.grey.shade50 : Colors.white,
                        ),
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Text(
                              '$dayIndex',
                              style: TextStyle(
                                fontSize: 11,
                                color: Colors.grey.shade600,
                              ),
                            ),
                            if (shift != null)
                              Container(
                                margin: const EdgeInsets.only(top: 2),
                                padding: const EdgeInsets.symmetric(
                                    horizontal: 4, vertical: 1),
                                decoration: BoxDecoration(
                                  color: _shiftColors[shift.shiftCode] ??
                                      Colors.grey.shade100,
                                  borderRadius: BorderRadius.circular(3),
                                ),
                                child: Text(
                                  shift.shiftCode,
                                  style: TextStyle(
                                    fontSize: 10,
                                    fontWeight: FontWeight.w700,
                                    color: _shiftTextColors[shift.shiftCode] ??
                                        Colors.grey.shade700,
                                  ),
                                ),
                              ),
                            if (shift != null && shift.extras.isNotEmpty)
                              Padding(
                                padding: const EdgeInsets.only(top: 2),
                                child: Wrap(
                                  alignment: WrapAlignment.center,
                                  spacing: 2,
                                  runSpacing: 1,
                                  children: shift.extras
                                      .take(2)
                                      .map((extra) =>
                                          _buildExtraChip(extra, compact: true))
                                      .toList(),
                                ),
                              ),
                          ],
                        ),
                      ),
                    );
                  }),
                );
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildShiftTile(ShiftAssignment s) {
    final bg = _shiftColors[s.shiftCode] ?? Colors.grey.shade100;
    final textColor = _shiftTextColors[s.shiftCode] ?? Colors.grey.shade700;

    return Card(
      child: ListTile(
        leading: Container(
          width: 40,
          height: 40,
          decoration: BoxDecoration(
            color: bg,
            borderRadius: BorderRadius.circular(8),
          ),
          child: Center(
            child: Text(
              s.shiftCode,
              style: TextStyle(
                fontWeight: FontWeight.w700,
                color: textColor,
              ),
            ),
          ),
        ),
        title: Text(
          s.shiftName,
          style: const TextStyle(fontWeight: FontWeight.w500),
        ),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(_formatShiftTime(s)),
            if (s.extras.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(top: 6),
                child: Wrap(
                  spacing: 4,
                  runSpacing: 4,
                  children: s.extras.map(_buildExtraChip).toList(),
                ),
              ),
          ],
        ),
        trailing: Text(
          s.date,
          style: TextStyle(color: Colors.grey.shade600, fontSize: 13),
        ),
      ),
    );
  }

  Widget _buildExtraChip(ScheduleExtra extra, {bool compact = false}) {
    final color = _parseHexColor(extra.color);
    return Tooltip(
      message: '${extra.label} (${extra.status})',
      child: Container(
        padding: EdgeInsets.symmetric(
          horizontal: compact ? 3 : 6,
          vertical: compact ? 1 : 2,
        ),
        decoration: BoxDecoration(
          color: color,
          borderRadius: BorderRadius.circular(4),
        ),
        child: Text(
          extra.code,
          style: TextStyle(
            color: _readableTextColor(color),
            fontSize: compact ? 9 : 11,
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
    );
  }

  Color _parseHexColor(String value) {
    final normalized = value.replaceAll('#', '').trim();
    if (normalized.length != 6) return Colors.grey.shade600;
    final parsed = int.tryParse('FF$normalized', radix: 16);
    if (parsed == null) return Colors.grey.shade600;
    return Color(parsed);
  }

  Color _readableTextColor(Color color) {
    final luminance = color.computeLuminance();
    return luminance > 0.55 ? Colors.grey.shade900 : Colors.white;
  }

  String _formatShiftTime(ShiftAssignment shift) {
    if (shift.shiftStart.isEmpty && shift.shiftEnd.isEmpty) {
      return 'Zusatzdienst';
    }
    return '${shift.shiftStart} - ${shift.shiftEnd}';
  }
}
