import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/auth_provider.dart';
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
