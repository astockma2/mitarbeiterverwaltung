class ShiftAssignment {
  final int id;
  final String date;
  final String shiftName;
  final String shiftCode;
  final String shiftStart;
  final String shiftEnd;
  final String status;

  ShiftAssignment({
    required this.id,
    required this.date,
    required this.shiftName,
    required this.shiftCode,
    required this.shiftStart,
    required this.shiftEnd,
    required this.status,
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
    );
  }
}
