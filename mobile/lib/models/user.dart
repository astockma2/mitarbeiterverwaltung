class User {
  final int id;
  final String personnelNumber;
  final String name;
  final String role;
  final int? departmentId;

  User({
    required this.id,
    required this.personnelNumber,
    required this.name,
    required this.role,
    this.departmentId,
  });

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['id'],
      personnelNumber: json['personnel_number'] ?? '',
      name: json['name'] ?? '',
      role: json['role'] ?? 'EMPLOYEE',
      departmentId: json['department_id'],
    );
  }

  bool get isAdmin => role == 'ADMIN';
  bool get isHR => role == 'HR' || isAdmin;
  bool get isManager =>
      isHR || role == 'DEPARTMENT_MANAGER' || role == 'TEAM_LEADER';

  String get roleLabel {
    switch (role) {
      case 'ADMIN':
        return 'Administrator';
      case 'HR':
        return 'Personalabteilung';
      case 'DEPARTMENT_MANAGER':
        return 'Abteilungsleitung';
      case 'TEAM_LEADER':
        return 'Teamleitung';
      default:
        return 'Mitarbeiter';
    }
  }
}
