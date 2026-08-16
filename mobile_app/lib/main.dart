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
            top: BorderSide(color: Color(0x33334155), width: 1),
          ),
        ),
        child: SafeArea(
          top: false,
          child: Container(
            height: 62,
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                _buildNavItem(0, 'Home', Icons.bar_chart_rounded, Icons.bar_chart_rounded),
                _buildNavItem(1, 'Alerts', Icons.notifications_none_rounded, Icons.notifications_rounded),
                _buildNavItem(2, 'Watchlist', Icons.format_list_bulleted_rounded, Icons.format_list_bulleted_rounded),
                _buildNavItem(3, 'Settings', Icons.settings_outlined, Icons.settings_rounded),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildNavItem(int index, String label, IconData icon, IconData activeIcon) {
    final isSelected = _currentIndex == index;

    return Expanded(
      child: InkWell(
        onTap: () => _onTabTapped(index),
        splashColor: Colors.transparent,
        highlightColor: Colors.transparent,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              isSelected ? activeIcon : icon,
              color: isSelected ? const Color(0xFF00B4D8) : const Color(0xFF64748B),
              size: 22,
            ),
            const SizedBox(height: 3),
            Text(
              label,
              style: TextStyle(
                color: isSelected ? const Color(0xFF00B4D8) : const Color(0xFF64748B),
                fontWeight: isSelected ? FontWeight.w900 : FontWeight.w600,
                fontSize: 11,
              ),
            ),
            const SizedBox(height: 4),
            // Glowing Indicator Pill (Matches User Screenshot)
            if (isSelected)
              Container(
                width: 24,
                height: 3,
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    colors: [Color(0xFF00B4D8), Color(0xFF8B5CF6)],
                  ),
                  borderRadius: BorderRadius.circular(2),
                  boxShadow: const [
                    BoxShadow(
                      color: Color(0xBB00B4D8),
                      blurRadius: 6,
                      offset: Offset(0, 1),
                    ),
                  ],
                ),
              )
            else
              const SizedBox(height: 3),
          ],
        ),
      ),
    );
  }
}
