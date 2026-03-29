import 'dart:math';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/auth_provider.dart';
import '../services/api_service.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  Map<String, dynamic>? _monthly;
  late String _quote;

  static const _quotes = [
    // Motivation & Anfangen
    'Erfolg ist die Summe kleiner Anstrengungen, die sich Tag fuer Tag wiederholen.',
    'Der beste Weg, die Zukunft vorherzusagen, ist sie zu gestalten.',
    'Das Geheimnis des Erfolgs ist anzufangen.',
    'Motivation bringt dich in Gang. Gewohnheit bringt dich weiter.',
    'Jeder Experte war einmal ein Anfaenger.',
    'Ein guter Plan heute ist besser als ein perfekter Plan morgen.',
    'Tu was du kannst, mit dem was du hast, dort wo du bist.',
    'Der einzige Weg, grossartige Arbeit zu leisten, ist zu lieben, was man tut.',
    'Wer aufhoert besser zu werden, hat aufgehoert gut zu sein.',
    'Auch der laengste Weg beginnt mit dem ersten Schritt.',
    'Nicht weil es schwer ist, wagen wir es nicht — weil wir es nicht wagen, ist es schwer.',
    'Wer immer tut, was er schon kann, bleibt immer das, was er schon ist.',
    'Zwischen Schwierigkeit und Meisterschaft liegt nur Beharrlichkeit.',
    'Hindernisse sind Dinge, die man sieht, wenn man den Blick vom Ziel abwendet.',
    'Ein Ziel ohne Plan ist nur ein Wunsch.',

    // Teamwork & Zusammenhalt
    'Zusammen erreichen wir mehr als jeder fuer sich allein.',
    'Teamarbeit macht aus einem guten Ergebnis ein grossartiges.',
    'Gemeinsam sind wir nicht nur ein Team — wir sind eine Familie.',
    'Allein koennen wir so wenig tun, zusammen koennen wir so viel bewegen.',
    'Das Beste an Teamarbeit: Man ist nie allein mit einem Problem.',
    'Starke Teams werden nicht aus perfekten Menschen gebaut, sondern aus Menschen, die fuereinander einstehen.',
    'Vertrauen ist der Klebstoff, der ein Team zusammenhaelt.',
    'Keiner von uns ist so klug wie wir alle zusammen.',
    'Ein Team ist mehr als die Summe seiner Teile.',
    'Wer anderen hilft, hilft sich selbst am meisten.',

    // Positives Mindset
    'Jeder Tag ist eine neue Chance, das zu tun, was dich gluecklich macht.',
    'Gib jedem Tag die Chance, der beste deines Lebens zu werden.',
    'Deine Einstellung bestimmt deine Richtung.',
    'Optimismus ist der Glaube, der zum Erfolg fuehrt.',
    'Lache so oft du kannst — es ist die beste Medizin.',
    'Wer lacht, hat noch Reserven.',
    'Freude an der Arbeit laesst das Werk trefflich geraten.',
    'Das Glueck besteht darin, zu leben wie alle Welt und doch wie kein anderer zu sein.',
    'Sei du selbst die Veraenderung, die du dir wuenschst fuer diese Welt.',
    'Jeder Morgen bringt neue Moeglichkeiten — nutze sie.',

    // Wertschaetzung & Beruf
    'Deine Arbeit macht einen Unterschied — jeden einzelnen Tag.',
    'Qualitaet kommt von Leidenschaft und Praezision.',
    'Pflege ist keine Arbeit — es ist eine Berufung.',
    'Wer Menschen heilt, veraendert die Welt — einen Patienten nach dem anderen.',
    'Hinter jeder Genesung steckt ein Team, das nie aufgegeben hat.',
    'Was man mit Liebe tut, das gelingt.',
    'Kleine Gesten der Fuersorge koennen grosse Wirkung haben.',
    'Dein Einsatz wird gesehen — auch wenn es manchmal nicht so scheint.',
    'Jede Schicht zaehlt. Jede Hand zaehlt. Jeder Mensch zaehlt.',
    'Wer sich um andere kuemmert, verdient selbst die groesste Wertschaetzung.',

    // Durchhalten & Staerke
    'Es sind die kleinen Schritte, die auf Dauer den Unterschied machen.',
    'Staerke waechst nicht aus koerperlicher Kraft — sie kommt aus unbeugsamen Willen.',
    'Schwierige Wege fuehren oft zu den schoensten Zielen.',
    'Geduld und Fleiss besiegen alles.',
    'Auch in der dunkelsten Nacht geht irgendwann die Sonne auf.',
    'Mut steht am Anfang des Handelns, Glueck am Ende.',
    'Durchhalten lohnt sich — immer.',
    'Wer kaempft, kann verlieren. Wer nicht kaempft, hat schon verloren.',
    'Krisen sind Chancen in Arbeitskleidung.',
    'Nach dem Sturm scheint die Sonne umso heller.',

    // Wachstum & Lernen
    'Fehler sind das Tor zu neuen Entdeckungen.',
    'Wissen ist der einzige Schatz, der sich vermehrt, wenn man ihn teilt.',
    'Heute besser als gestern, morgen besser als heute.',
    'Aus Fehlern lernt man — aus Erfolgen auch.',
    'Neugier ist der Motor des Fortschritts.',
    'Wer fragt, ist ein Narr fuer fuenf Minuten. Wer nicht fragt, bleibt ein Narr fuer immer.',
    'Lerne aus der Vergangenheit, lebe in der Gegenwart, plane fuer die Zukunft.',
    'Jeder Tag bietet die Moeglichkeit, etwas Neues zu lernen.',

    // Humor & Leichtigkeit
    'Kaffee ist das Schmiermittel der Produktivitaet.',
    'Feierabend: der schoenste Beweis, dass jeder Tag ein Ende hat.',
    'Du bist nicht muede — du bist nur noch nicht beim Kaffee angelangt.',
    'Montag: der Tag, an dem die Kaffeemaschine am haertesten arbeitet.',
    'Heute ist ein guter Tag fuer einen guten Tag.',
    'Nicht vergessen: nach der Schicht kommt das Sofa.',
    'Haende, die pflegen, brauchen auch mal eine Pause — nimm sie dir.',
    'Das Leben ist zu kurz fuer schlechten Kaffee und schlechte Laune.',
    'Wochenende: Ladestation fuer die Seele.',
    'Lachen ist die beste Teambildung.',
  ];

  @override
  void initState() {
    super.initState();
    // Jeden Tag einen anderen Spruch (basierend auf Tag des Jahres)
    final dayOfYear = DateTime.now().difference(DateTime(DateTime.now().year)).inDays;
    _quote = _quotes[dayOfYear % _quotes.length];
    _loadMonthly();
  }

  Future<void> _loadMonthly() async {
    try {
      final now = DateTime.now();
      _monthly = await ApiService.getMonthlySummary(now.year, now.month);
      setState(() {});
    } catch (_) {}
  }

  String _greeting() {
    final hour = DateTime.now().hour;
    if (hour < 6) return 'Gute Nacht';
    if (hour < 11) return 'Guten Morgen';
    if (hour < 14) return 'Mahlzeit';
    if (hour < 18) return 'Guten Nachmittag';
    return 'Guten Abend';
  }

  String _firstName(String fullName) {
    final parts = fullName.split(' ');
    return parts.isNotEmpty ? parts.first : fullName;
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final user = auth.user;
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(title: const Text('Profil')),
      body: RefreshIndicator(
        onRefresh: _loadMonthly,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            // Begruessung
            Card(
              elevation: 2,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
              child: Container(
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(16),
                  gradient: LinearGradient(
                    colors: [
                      theme.colorScheme.primary,
                      theme.colorScheme.primary.withValues(alpha: 0.7),
                    ],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                ),
                padding: const EdgeInsets.all(24),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        CircleAvatar(
                          radius: 32,
                          backgroundColor: Colors.white.withValues(alpha: 0.2),
                          child: Text(
                            _initials(user?.name ?? ''),
                            style: const TextStyle(
                              fontSize: 24,
                              fontWeight: FontWeight.w700,
                              color: Colors.white,
                            ),
                          ),
                        ),
                        const SizedBox(width: 16),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                '${_greeting()},',
                                style: TextStyle(
                                  fontSize: 14,
                                  color: Colors.white.withValues(alpha: 0.85),
                                ),
                              ),
                              const SizedBox(height: 2),
                              Text(
                                _firstName(user?.name ?? ''),
                                style: const TextStyle(
                                  fontSize: 22,
                                  fontWeight: FontWeight.w700,
                                  color: Colors.white,
                                ),
                              ),
                              const SizedBox(height: 4),
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                                decoration: BoxDecoration(
                                  color: Colors.white.withValues(alpha: 0.2),
                                  borderRadius: BorderRadius.circular(8),
                                ),
                                child: Text(
                                  user?.roleLabel ?? '',
                                  style: const TextStyle(
                                    color: Colors.white,
                                    fontSize: 12,
                                    fontWeight: FontWeight.w500,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Colors.white.withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Icon(
                            Icons.format_quote_rounded,
                            color: Colors.white.withValues(alpha: 0.6),
                            size: 20,
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              _quote,
                              style: TextStyle(
                                color: Colors.white.withValues(alpha: 0.9),
                                fontSize: 13,
                                fontStyle: FontStyle.italic,
                                height: 1.4,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),

            // Arbeitszeitkarte
            if (_monthly != null) _buildWorkTimeCard(),
            if (_monthly == null)
              const Card(
                child: Padding(
                  padding: EdgeInsets.all(24),
                  child: Center(child: CircularProgressIndicator()),
                ),
              ),
            const SizedBox(height: 16),

            // App-Infos
            Card(
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              child: Column(
                children: [
                  ListTile(
                    leading: const Icon(Icons.badge_outlined),
                    title: const Text('Personalnummer'),
                    trailing: Text(
                      user?.personnelNumber ?? '--',
                      style: TextStyle(
                        color: Colors.grey.shade700,
                        fontFamily: 'monospace',
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                  const Divider(height: 1),
                  ListTile(
                    leading: const Icon(Icons.info_outline),
                    title: const Text('App-Version'),
                    trailing: Text(
                      '1.0.0',
                      style: TextStyle(color: Colors.grey.shade600),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),

            // Abmelden
            SizedBox(
              width: double.infinity,
              height: 48,
              child: OutlinedButton.icon(
                onPressed: () => auth.logout(),
                icon: const Icon(Icons.logout, color: Colors.red),
                label: const Text(
                  'Abmelden',
                  style: TextStyle(color: Colors.red),
                ),
                style: OutlinedButton.styleFrom(
                  side: const BorderSide(color: Colors.red),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildWorkTimeCard() {
    final totalHours = (_monthly!['total_hours'] as num).toDouble();
    final targetHours = (_monthly!['target_hours'] as num).toDouble();
    final overtimeHours = (_monthly!['overtime_hours'] as num).toDouble();
    final workDays = _monthly!['work_days'] as int;
    final progress = targetHours > 0 ? (totalHours / targetHours).clamp(0.0, 1.5) : 0.0;

    final now = DateTime.now();
    final monthNames = [
      '', 'Januar', 'Februar', 'Maerz', 'April', 'Mai', 'Juni',
      'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember',
    ];

    return Card(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.access_time_rounded, size: 20, color: Colors.grey.shade700),
                const SizedBox(width: 8),
                Text(
                  '${monthNames[now.month]} ${now.year}',
                  style: TextStyle(
                    fontWeight: FontWeight.w600,
                    fontSize: 15,
                    color: Colors.grey.shade800,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),

            // Fortschrittsbalken
            ClipRRect(
              borderRadius: BorderRadius.circular(6),
              child: LinearProgressIndicator(
                value: progress.toDouble(),
                minHeight: 10,
                backgroundColor: Colors.grey.shade200,
                valueColor: AlwaysStoppedAnimation<Color>(
                  overtimeHours > 0 ? Colors.orange.shade400 : Colors.green.shade400,
                ),
              ),
            ),
            const SizedBox(height: 6),
            Text(
              '${totalHours.toStringAsFixed(1)} von ${targetHours.toStringAsFixed(1)} Stunden',
              style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
            ),
            const SizedBox(height: 16),

            // Kennzahlen
            Row(
              children: [
                Expanded(
                  child: _statTile(
                    Icons.trending_up_rounded,
                    'Ist',
                    '${totalHours.toStringAsFixed(1)}h',
                    Colors.blue,
                  ),
                ),
                Expanded(
                  child: _statTile(
                    Icons.flag_rounded,
                    'Soll',
                    '${targetHours.toStringAsFixed(1)}h',
                    Colors.grey,
                  ),
                ),
                Expanded(
                  child: _statTile(
                    overtimeHours >= 0 ? Icons.add_circle_outline : Icons.remove_circle_outline,
                    overtimeHours >= 0 ? 'Plus' : 'Minus',
                    '${overtimeHours.abs().toStringAsFixed(1)}h',
                    overtimeHours > 0 ? Colors.orange : (overtimeHours < 0 ? Colors.red : Colors.grey),
                  ),
                ),
                Expanded(
                  child: _statTile(
                    Icons.calendar_today_rounded,
                    'Tage',
                    '$workDays',
                    Colors.indigo,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _statTile(IconData icon, String label, String value, Color color) {
    return Column(
      children: [
        Icon(icon, size: 20, color: color),
        const SizedBox(height: 4),
        Text(
          value,
          style: TextStyle(
            fontWeight: FontWeight.w700,
            fontSize: 15,
            color: color,
          ),
        ),
        Text(
          label,
          style: TextStyle(fontSize: 11, color: Colors.grey.shade600),
        ),
      ],
    );
  }

  String _initials(String name) {
    final parts = name.split(' ');
    if (parts.length >= 2) {
      return '${parts.first[0]}${parts.last[0]}'.toUpperCase();
    }
    return name.isNotEmpty ? name[0].toUpperCase() : '?';
  }
}
