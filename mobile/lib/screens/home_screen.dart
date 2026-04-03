import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'package:url_launcher/url_launcher.dart';
import '../services/auth_provider.dart';
import '../services/api_service.dart';
import 'time_clock_screen.dart';
import 'shift_plan_screen.dart';
import 'absences_screen.dart';
import 'chat_screen.dart';
import 'profile_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _currentIndex = 0;

  final _screens = const [
    ProfileScreen(),
    TimeClockScreen(),
    ShiftPlanScreen(),
    AbsencesScreen(),
    ChatListScreen(),
  ];

  @override
  void initState() {
    super.initState();
    _checkForUpdate();
  }

  Future<void> _checkForUpdate() async {
    try {
      final versionInfo = await ApiService.checkAppVersion();
      if (versionInfo == null || !mounted) return;

      final serverVersion = versionInfo['version'] as String;
      final downloadUrl = versionInfo['download_url'] as String;
      final forceUpdate = versionInfo['force_update'] as bool? ?? false;

      final packageInfo = await PackageInfo.fromPlatform();
      final currentVersion = packageInfo.version;

      if (_isNewerVersion(serverVersion, currentVersion)) {
        if (!mounted) return;
        _showUpdateDialog(serverVersion, downloadUrl, forceUpdate);
      }
    } catch (_) {
      // Update-Check fehlgeschlagen — still ignorieren
    }
  }

  bool _isNewerVersion(String server, String current) {
    final s = server.split('.').map(int.parse).toList();
    final c = current.split('.').map(int.parse).toList();
    for (var i = 0; i < 3; i++) {
      final sv = i < s.length ? s[i] : 0;
      final cv = i < c.length ? c[i] : 0;
      if (sv > cv) return true;
      if (sv < cv) return false;
    }
    return false;
  }

  void _showUpdateDialog(String version, String url, bool force) {
    showDialog(
      context: context,
      barrierDismissible: !force,
      builder: (ctx) => AlertDialog(
        title: const Text('Update verfuegbar'),
        content: Text('Version $version ist verfuegbar. Bitte aktualisieren Sie die App.'),
        actions: [
          if (!force)
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(),
              child: const Text('Spaeter'),
            ),
          FilledButton(
            onPressed: () async {
              final uri = Uri.parse(url);
              if (await canLaunchUrl(uri)) {
                await launchUrl(uri, mode: LaunchMode.externalApplication);
              }
            },
            child: const Text('Jetzt aktualisieren'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(
        index: _currentIndex,
        children: _screens,
      ),
      bottomNavigationBar: Theme(
        data: Theme.of(context).copyWith(
          navigationBarTheme: NavigationBarThemeData(
            labelTextStyle: WidgetStateProperty.all(
              const TextStyle(fontSize: 11, overflow: TextOverflow.ellipsis),
            ),
          ),
        ),
        child: NavigationBar(
          selectedIndex: _currentIndex,
          onDestinationSelected: (i) => setState(() => _currentIndex = i),
          labelBehavior: NavigationDestinationLabelBehavior.alwaysShow,
          destinations: const [
            NavigationDestination(
              icon: Icon(Icons.person_outline, size: 22),
              selectedIcon: Icon(Icons.person, size: 22),
              label: 'Profil',
            ),
            NavigationDestination(
              icon: Icon(Icons.access_time_outlined, size: 22),
              selectedIcon: Icon(Icons.access_time_filled, size: 22),
              label: 'Stempeln',
            ),
            NavigationDestination(
              icon: Icon(Icons.calendar_month_outlined, size: 22),
              selectedIcon: Icon(Icons.calendar_month, size: 22),
              label: 'Dienstplan',
            ),
            NavigationDestination(
              icon: Icon(Icons.event_busy_outlined, size: 22),
              selectedIcon: Icon(Icons.event_busy, size: 22),
              label: 'Abwesend',
            ),
            NavigationDestination(
              icon: Icon(Icons.chat_bubble_outline, size: 22),
              selectedIcon: Icon(Icons.chat_bubble, size: 22),
              label: 'Chat',
            ),
          ],
        ),
      ),
    );
  }
}
