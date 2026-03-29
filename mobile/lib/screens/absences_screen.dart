import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../models/absence.dart';

class AbsencesScreen extends StatefulWidget {
  const AbsencesScreen({super.key});

  @override
  State<AbsencesScreen> createState() => _AbsencesScreenState();
}

class _AbsencesScreenState extends State<AbsencesScreen> {
  List<Absence> _absences = [];
  VacationBalance? _vacation;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final results = await Future.wait([
        ApiService.getAbsences(),
        ApiService.getVacationBalance(),
      ]);
      _absences = results[0] as List<Absence>;
      _vacation = results[1] as VacationBalance;
    } catch (_) {}
    setState(() => _loading = false);
  }

  void _showCreateDialog() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (ctx) => _AbsenceForm(
        onCreated: () {
          Navigator.pop(ctx);
          _load();
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Abwesenheiten')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _showCreateDialog,
        icon: const Icon(Icons.add),
        label: const Text('Neuer Antrag'),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  // Urlaubskonto
                  if (_vacation != null) _buildVacationCard(),
                  const SizedBox(height: 16),

                  // Abwesenheitsliste
                  Text(
                    'Meine Antraege',
                    style: TextStyle(
                      fontWeight: FontWeight.w600,
                      fontSize: 15,
                      color: Colors.grey.shade800,
                    ),
                  ),
                  const SizedBox(height: 8),
                  if (_absences.isEmpty)
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(32),
                        child: Center(
                          child: Text(
                            'Keine Antraege vorhanden',
                            style: TextStyle(color: Colors.grey.shade400),
                          ),
                        ),
                      ),
                    ),
                  ..._absences.map((a) => _buildAbsenceTile(a)),
                  const SizedBox(height: 80), // Platz fuer FAB
                ],
              ),
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
            // Fortschrittsbalken
            ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: LinearProgressIndicator(
                value: v.entitlement > 0
                    ? ((v.taken + v.pending) / v.entitlement).clamp(0.0, 1.0)
                    : 0,
                minHeight: 8,
                backgroundColor: Colors.grey.shade200,
                color: Colors.blue,
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
          Text(label, style: TextStyle(fontSize: 11, color: Colors.grey.shade500)),
        ],
      ),
    );
  }

  Widget _buildAbsenceTile(Absence a) {
    Color statusColor;
    switch (a.status) {
      case 'APPROVED':
        statusColor = Colors.green;
        break;
      case 'REJECTED':
        statusColor = Colors.red;
        break;
      case 'CANCELLED':
        statusColor = Colors.grey;
        break;
      default:
        statusColor = Colors.orange;
    }

    return Card(
      child: ListTile(
        leading: Container(
          width: 40,
          height: 40,
          decoration: BoxDecoration(
            color: statusColor.withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Icon(
            a.type == 'SICK'
                ? Icons.local_hospital
                : a.type == 'TRAINING'
                    ? Icons.school
                    : Icons.beach_access,
            color: statusColor,
            size: 20,
          ),
        ),
        title: Text(
          a.typeLabel,
          style: const TextStyle(fontWeight: FontWeight.w500),
        ),
        subtitle: Text('${a.startDate} — ${a.endDate} (${a.days} Tage)'),
        trailing: Chip(
          label: Text(
            a.statusLabel,
            style: TextStyle(fontSize: 11, color: statusColor),
          ),
          backgroundColor: statusColor.withValues(alpha: 0.1),
          side: BorderSide.none,
        ),
      ),
    );
  }
}

// --- Antragsformular als Bottom Sheet ---

class _AbsenceForm extends StatefulWidget {
  final VoidCallback onCreated;
  const _AbsenceForm({required this.onCreated});

  @override
  State<_AbsenceForm> createState() => _AbsenceFormState();
}

class _AbsenceFormState extends State<_AbsenceForm> {
  String _type = 'VACATION';
  DateTime? _start;
  DateTime? _end;
  final _notesController = TextEditingController();
  bool _submitting = false;
  String? _error;

  final _types = {
    'VACATION': 'Urlaub',
    'SICK': 'Krankheit',
    'TRAINING': 'Fortbildung',
    'SPECIAL': 'Sonderurlaub',
    'COMP_TIME': 'Freizeitausgleich',
  };

  Future<void> _pickDate(bool isStart) async {
    final picked = await showDatePicker(
      context: context,
      initialDate: DateTime.now(),
      firstDate: DateTime(2024),
      lastDate: DateTime(2030),
    );
    if (picked != null) {
      setState(() {
        if (isStart) {
          _start = picked;
        } else {
          _end = picked;
        }
      });
    }
  }

  String _formatDate(DateTime? d) {
    if (d == null) return 'Waehlen...';
    return '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';
  }

  Future<void> _submit() async {
    if (_start == null || _end == null) {
      setState(() => _error = 'Bitte Zeitraum waehlen');
      return;
    }
    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      await ApiService.createAbsence(
        type: _type,
        startDate: _formatDate(_start),
        endDate: _formatDate(_end),
        notes: _notesController.text,
      );
      widget.onCreated();
    } on ApiException catch (e) {
      setState(() => _error = e.message);
    }
    setState(() => _submitting = false);
  }

  @override
  void dispose() {
    _notesController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(
        left: 24,
        right: 24,
        top: 24,
        bottom: MediaQuery.of(context).viewInsets.bottom + 24,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Neuer Abwesenheitsantrag',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 20),

          // Typ
          DropdownButtonFormField<String>(
            value: _type,
            decoration: const InputDecoration(
              labelText: 'Typ',
              border: OutlineInputBorder(),
            ),
            items: _types.entries
                .map((e) => DropdownMenuItem(value: e.key, child: Text(e.value)))
                .toList(),
            onChanged: (v) => setState(() => _type = v ?? 'VACATION'),
          ),
          const SizedBox(height: 16),

          // Zeitraum
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: () => _pickDate(true),
                  icon: const Icon(Icons.calendar_today, size: 16),
                  label: Text(_start == null ? 'Von' : _formatDate(_start)),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: () => _pickDate(false),
                  icon: const Icon(Icons.calendar_today, size: 16),
                  label: Text(_end == null ? 'Bis' : _formatDate(_end)),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),

          // Anmerkung
          TextField(
            controller: _notesController,
            decoration: const InputDecoration(
              labelText: 'Anmerkung (optional)',
              border: OutlineInputBorder(),
            ),
            maxLines: 2,
          ),
          const SizedBox(height: 8),

          // Fehler
          if (_error != null)
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Text(
                _error!,
                style: TextStyle(color: Colors.red.shade700, fontSize: 13),
              ),
            ),

          // Absenden
          SizedBox(
            width: double.infinity,
            height: 48,
            child: FilledButton(
              onPressed: _submitting ? null : _submit,
              child: _submitting
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                    )
                  : const Text('Antrag absenden'),
            ),
          ),
        ],
      ),
    );
  }
}
