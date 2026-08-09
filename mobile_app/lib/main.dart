import 'package:flutter/material.dart';
import 'config/theme.dart';
import 'screens/onboarding_modal.dart';
import 'screens/auth_screen.dart';
import 'screens/icici_credentials_screen.dart';
import 'screens/dashboard_screen.dart';
import 'screens/alert_radar_screen.dart';
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
  bool _hasAgreedDisclaimer = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _checkDisclaimer();
    });
  }

  void _checkDisclaimer() {
    if (!_hasAgreedDisclaimer) {
      showDialog(
        context: context,
        barrierDismissible: false,
        builder: (context) => OnboardingDisclaimerModal(
          onAccept: () {
            setState(() => _hasAgreedDisclaimer = true);
            Navigator.of(context).pop();
          },
        ),
      );
    }
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

    if (currentUser == null) {
      return AuthScreen(
        onLoginSuccess: () {
          setState(() {});
        },
      );
    }

    final pages = [
      DashboardScreen(onOpenCredentials: _openCredentialsSetup),
      const AlertRadarScreen(),
      const WatchlistScreen(),
      const NotificationSettingsScreen(),
    ];

    return Scaffold(
      body: pages[_currentIndex],
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _currentIndex,
        onTap: _onTabTapped,
        items: const [
          BottomNavigationBarItem(icon: Icon(Icons.dashboard_outlined), activeIcon: Icon(Icons.dashboard), label: 'Dashboard'),
          BottomNavigationBarItem(icon: Icon(Icons.radar_outlined), activeIcon: Icon(Icons.radar), label: 'Radar'),
          BottomNavigationBarItem(icon: Icon(Icons.list_alt_outlined), activeIcon: Icon(Icons.list_alt), label: 'Watchlist'),
          BottomNavigationBarItem(icon: Icon(Icons.notifications_outlined), activeIcon: Icon(Icons.notifications), label: 'Alerts'),
        ],
      ),
    );
  }
}
