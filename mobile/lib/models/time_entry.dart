class TimeEntry {
  final int id;
  final DateTime clockIn;
  final DateTime? clockOut;
  final int breakMinutes;
  final double? netHours;
  final String entryType;
  final List<Surcharge> surcharges;

  TimeEntry({
    required this.id,
    required this.clockIn,
    this.clockOut,
    required this.breakMinutes,
    this.netHours,
    required this.entryType,
    this.surcharges = const [],
  });

  factory TimeEntry.fromJson(Map<String, dynamic> json) {
    return TimeEntry(
      id: json['id'],
      clockIn: DateTime.parse(json['clock_in']),
      clockOut: json['clock_out'] != null ? DateTime.parse(json['clock_out']) : null,
      breakMinutes: json['break_minutes'] ?? 0,
      netHours: json['net_hours']?.toDouble(),
      entryType: json['entry_type'] ?? 'REGULAR',
      surcharges: (json['surcharges'] as List? ?? [])
          .map((s) => Surcharge.fromJson(s))
          .toList(),
    );
  }
}

class Surcharge {
  final String type;
  final double hours;
  final double ratePercent;

  Surcharge({required this.type, required this.hours, required this.ratePercent});

  factory Surcharge.fromJson(Map<String, dynamic> json) {
    return Surcharge(
      type: json['type'] ?? '',
      hours: (json['hours'] ?? 0).toDouble(),
      ratePercent: (json['rate_percent'] ?? 0).toDouble(),
    );
  }
}

class ClockStatus {
  final bool clockedIn;
  final String? since;
  final double? elapsedHours;

  ClockStatus({required this.clockedIn, this.since, this.elapsedHours});

  factory ClockStatus.fromJson(Map<String, dynamic> json) {
    return ClockStatus(
      clockedIn: json['clocked_in'] ?? false,
      since: json['since'],
      elapsedHours: json['elapsed_hours']?.toDouble(),
    );
  }
}

class DailySummary {
  final double totalHours;
  final int totalBreakMinutes;
  final int entryCount;

  DailySummary({
    required this.totalHours,
    required this.totalBreakMinutes,
    required this.entryCount,
  });

  factory DailySummary.fromJson(Map<String, dynamic> json) {
    return DailySummary(
      totalHours: (json['total_hours'] ?? 0).toDouble(),
      totalBreakMinutes: json['total_break_minutes'] ?? 0,
      entryCount: json['entry_count'] ?? 0,
    );
  }
}
