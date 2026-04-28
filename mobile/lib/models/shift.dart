class ScheduleExtra {
  final String type;
  final String code;
  final String label;
  final String status;
  final String color;

  ScheduleExtra({
    required this.type,
    required this.code,
    required this.label,
    required this.status,
    required this.color,
  });

  factory ScheduleExtra.fromJson(Map<String, dynamic> json) {
    return ScheduleExtra(
      type: json['type'] ?? '',
      code: json['code'] ?? '',
      label: json['label'] ?? '',
      status: json['status'] ?? '',
      color: json['color'] ?? '#64748B',
    );
  }
}

class ShiftAssignment {
  final int id;
  final String date;
  final String shiftName;
  final String shiftCode;
  final String shiftStart;
  final String shiftEnd;
  final String status;
  final List<ScheduleExtra> extras;

  ShiftAssignment({
    required this.id,
    required this.date,
    required this.shiftName,
    required this.shiftCode,
    required this.shiftStart,
    required this.shiftEnd,
    required this.status,
    required this.extras,
  });

  factory ShiftAssignment.fromJson(Map<String, dynamic> json) {
    return ShiftAssignment(
      id: json['id'] ?? 0,
      date: json['date'] ?? '',
      shiftName: json['shift_name'] ?? '',
      shiftCode: json['shift_code'] ?? '',
      shiftStart: json['shift_start'] ?? '',
      shiftEnd: json['shift_end'] ?? '',
      status: json['status'] ?? '',
      extras: ((json['extras'] ?? []) as List)
          .map((e) => ScheduleExtra.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}
