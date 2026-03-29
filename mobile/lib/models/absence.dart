class Absence {
  final int id;
  final String type;
  final String startDate;
  final String endDate;
  final int days;
  final String status;
  final String? notes;

  Absence({
    required this.id,
    required this.type,
    required this.startDate,
    required this.endDate,
    required this.days,
    required this.status,
    this.notes,
  });

  factory Absence.fromJson(Map<String, dynamic> json) {
    return Absence(
      id: json['id'] ?? 0,
      type: json['type'] ?? '',
      startDate: json['start_date'] ?? '',
      endDate: json['end_date'] ?? '',
      days: json['days'] ?? 0,
      status: json['status'] ?? '',
      notes: json['notes'],
    );
  }

  String get typeLabel {
    switch (type) {
      case 'VACATION':
        return 'Urlaub';
      case 'SICK':
        return 'Krankheit';
      case 'TRAINING':
        return 'Fortbildung';
      case 'SPECIAL':
        return 'Sonderurlaub';
      case 'COMP_TIME':
        return 'Freizeitausgleich';
      default:
        return type;
    }
  }

  String get statusLabel {
    switch (status) {
      case 'REQUESTED':
        return 'Beantragt';
      case 'APPROVED':
        return 'Genehmigt';
      case 'REJECTED':
        return 'Abgelehnt';
      case 'CANCELLED':
        return 'Storniert';
      default:
        return status;
    }
  }
}

class VacationBalance {
  final int year;
  final int entitlement;
  final int taken;
  final int pending;
  final int remaining;

  VacationBalance({
    required this.year,
    required this.entitlement,
    required this.taken,
    required this.pending,
    required this.remaining,
  });

  factory VacationBalance.fromJson(Map<String, dynamic> json) {
    return VacationBalance(
      year: json['year'] ?? DateTime.now().year,
      entitlement: json['entitlement'] ?? 0,
      taken: json['taken'] ?? 0,
      pending: json['pending'] ?? 0,
      remaining: json['remaining'] ?? 0,
    );
  }
}
