import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/auth_provider.dart';
import '../services/api_service.dart';
import '../models/time_entry.dart';
import '../models/absence.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => DashboardScreenState();
}

class DashboardScreenState extends State<DashboardScreen> {
  ClockStatus? _clockStatus;
  Map<String, dynamic>? _monthly;
  VacationBalance? _vacation;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> reload() => _load();

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final now = DateTime.now();
      final results = await Future.wait([
        ApiService.getClockStatus(),
        ApiService.getMonthlySummary(now.year, now.month),
        ApiService.getVacationBalance(),
      ]);
      _clockStatus = results[0] as ClockStatus;
      _monthly = results[1] as Map<String, dynamic>;
      _vacation = results[2] as VacationBalance;
    } catch (_) {}
    setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    final user = context.read<AuthProvider>().user;
    final firstName = user?.name.split(' ').first ?? '';

    return Scaffold(
      appBar: AppBar(
        title: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Image.asset('assets/logo.png', height: 32),
            const SizedBox(width: 10),
            Text('Hallo, $firstName'),
          ],
        ),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  // Stempel-Status
                  _buildStatusCard(),
                  const SizedBox(height: 16),

                  // Monatsübersicht
                  if (_monthly != null) _buildMonthlyCard(),
                  const SizedBox(height: 16),

                  // Urlaubskonto
                  if (_vacation != null) _buildVacationCard(),
                ],
              ),
            ),
    );
  }

  Widget _buildStatusCard() {
    final isIn = _clockStatus?.clockedIn ?? false;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Row(
          children: [
            Container(
              width: 48,
              height: 48,
              decoration: BoxDecoration(
                color: isIn ? Colors.green.shade50 : Colors.grey.shade100,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(
                isIn ? Icons.login : Icons.logout,
                color: isIn ? Colors.green : Colors.grey,
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    isIn ? 'Eingestempelt' : 'Nicht eingestempelt',
                    style: TextStyle(
                      fontWeight: FontWeight.w600,
                      fontSize: 16,
                      color: isIn ? Colors.green.shade700 : Colors.grey.shade600,
                    ),
                  ),
                  if (isIn && _clockStatus?.elapsedHours != null)
                    Text(
                      '${_clockStatus!.elapsedHours!.toStringAsFixed(1)}h heute',
                      style: TextStyle(color: Colors.grey.shade600, fontSize: 13),
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMonthlyCard() {
    final m = _monthly!;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Monatsuebersicht',
              style: TextStyle(
                fontWeight: FontWeight.w600,
                fontSize: 15,
                color: Colors.grey.shade800,
              ),
            ),
            const SizedBox(height: 16),
            // Fortschrittsbalken
            ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: LinearProgressIndicator(
                value: (m['target_hours'] ?? 1) > 0
                    ? ((m['total_hours'] ?? 0) / m['target_hours']).clamp(0.0, 1.0)
                    : 0,
                minHeight: 8,
                backgroundColor: Colors.grey.shade200,
              ),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                _statItem('Soll', '${m['target_hours']}h'),
                _statItem('Ist', '${m['total_hours']}h'),
                _statItem('Ueber', '${m['overtime_hours']}h',
                    color: (m['overtime_hours'] ?? 0) > 0
                        ? Colors.orange
                        : Colors.grey.shade600),
                _statItem('Tage', '${m['work_days']}'),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _statItem(String label, String value, {Color? color}) {
    return Expanded(
      child: Column(
        children: [
          Text(
            value,
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.w700,
              color: color ?? Colors.grey.shade800,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            label,
            style: TextStyle(fontSize: 11, color: Colors.grey.shade500),
          ),
        ],
      ),
    );
  }

  Widget _buildVacationCard() {
    final v = _vacation!;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Urlaubskonto ${v.year}',
              style: TextStyle(
                fontWeight: FontWeight.w600,
                fontSize: 15,
                color: Colors.grey.shade800,
              ),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                _statItem('Anspruch', '${v.entitlement}'),
                _statItem('Genommen', '${v.taken}', color: Colors.blue),
                _statItem('Beantragt', '${v.pending}', color: Colors.orange),
                _statItem('Rest', '${v.remaining}', color: Colors.green),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
