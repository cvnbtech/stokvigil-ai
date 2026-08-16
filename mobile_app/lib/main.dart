import 'dart:async';
import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'config/theme.dart';
import 'screens/auth_screen.dart';
import 'screens/icici_credentials_screen.dart';
import 'screens/dashboard_screen.dart';
import 'screens/alerts_screen.dart';
import 'screens/notification_settings_screen.dart';
import 'screens/watchlist_screen.dart';
import 'services/supabase_service.dart';
import 'services/fcm_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await SupabaseService.initialize();
  await FcmService().initialize();
  runApp(const StokVigilApp());
}

class StokVigilApp extends StatelessWidget {
  const StokVigilApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'StokVigil AI',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.darkTheme,
      home: const MainNavigationWrapper(),
    );
  }
}

class MainNavigationWrapper extends StatefulWidget {
  const MainNavigationWrapper({super.key});

  @override
  State<MainNavigationWrapper> createState() => _MainNavigationWrapperState();
}

class _MainNavigationWrapperState extends State<MainNavigationWrapper> {
  int _currentIndex = 0;
  StreamSubscription<AuthState>? _authSubscription;

  @override
  void initState() {
    super.initState();
    if (SupabaseService.isConfigured) {
      _authSubscription = SupabaseService().client.auth.onAuthStateChange.listen((data) {
        if (mounted) {
          setState(() {
            _currentIndex = 0;
          });
        }
      });
    }
  }

  @override
  void dispose() {
    _authSubscription?.cancel();
    super.dispose();
  }

  void _onTabTapped(int index) {
    setState(() => _currentIndex = index);
  }

  void _openCredentialsSetup() {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => IciciCredentialsScreen(
          onSaved: () {
            Navigator.of(context).pop();
            setState(() {});
          },
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final currentUser = SupabaseService().currentUser;

    // Strict Authentication Guard
    if (currentUser == null) {
      return AuthScreen(
        onLoginSuccess: () {
          setState(() {});
        },
      );
    }

    final pages = [
      DashboardScreen(onOpenCredentials: _openCredentialsSetup),
      const AlertsScreen(),
      const WatchlistScreen(),
      const NotificationSettingsScreen(),
    ];

    return Scaffold(
      body: Stack(
        children: [
          // Background ambient radial lights
          Positioned.fill(
            child: Container(
              decoration: const BoxDecoration(
                color: AppTheme.darkBackground,
              ),
            ),
          ),
          pages[_currentIndex],
        ],
      ),
      bottomNavigationBar: Container(
        decoration: const BoxDecoration(
          color: Color(0xF6060812), // rgba(6,8,18,0.97)
          border: Border(
            top: BorderSide(color: AppTheme.cardBorder, width: 1),
          ),
        ),
        child: BottomNavigationBar(
          currentIndex: _currentIndex,
          onTap: _onTabTapped,
          backgroundColor: Colors.transparent,
          selectedItemColor: AppTheme.cyan,
          unselectedItemColor: AppTheme.textSecondary,
          selectedFontSize: 11,
          unselectedFontSize: 11,
          type: BottomNavigationBarType.fixed,
          selectedLabelStyle: const TextStyle(fontWeight: FontWeight.w900),
          unselectedLabelStyle: const TextStyle(fontWeight: FontWeight.w600),
          items: const [
            BottomNavigationBarItem(
              icon: Icon(Icons.bar_chart_rounded),
              activeIcon: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.bar_chart_rounded, color: AppTheme.cyan),
                  SizedBox(height: 2),
                ],
              ),
              label: 'Home',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.notifications_none_rounded),
              activeIcon: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.notifications_rounded, color: AppTheme.cyan),
                  SizedBox(height: 2),
                ],
              ),
              label: 'Alerts',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.format_list_bulleted_rounded),
              activeIcon: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.format_list_bulleted_rounded, color: AppTheme.cyan),
                  SizedBox(height: 2),
                ],
              ),
              label: 'Watchlist',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.settings_outlined),
              activeIcon: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.settings_rounded, color: AppTheme.cyan),
                  SizedBox(height: 2),
                ],
              ),
              label: 'Settings',
            ),
          ],
        ),
      ),
    );
  }
}
