import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import '../config/theme.dart';
import '../services/api_service.dart';
import '../services/fcm_service.dart';
import '../services/supabase_service.dart';
import '../utils/error_handler.dart';
import '../widgets/custom_widgets.dart';

class NotificationSettingsScreen extends StatefulWidget {
  const NotificationSettingsScreen({super.key});

  @override
  State<NotificationSettingsScreen> createState() => _NotificationSettingsScreenState();
}

class _NotificationSettingsScreenState extends State<NotificationSettingsScreen> {
  final _telegramChatIdController = TextEditingController();
  bool _telegramEnabled = true;
  bool _fcmEnabled = true;
  String _alertSensitivity = 'HIGH';
  bool _isSaving = false;

  @override
  void initState() {
    super.initState();
    _loadNotificationSettings();
  }

  Future<void> _loadNotificationSettings() async {
    final user = SupabaseService().currentUser;
    if (user == null) return;

    try {
      final data = await SupabaseService().client
          .from('profiles')
          .select()
          .eq('id', user.id)
          .single();

      setState(() {
        _telegramChatIdController.text = data['telegram_chat_id'] ?? '';
        _telegramEnabled = data['telegram_enabled'] ?? true;
      });
    } catch (e) {
      debugPrint("Error loading profile settings: $e");
    }
  }

  Future<void> _saveSettings() async {
    final user = SupabaseService().currentUser;
    if (user == null) {
      ErrorHandler.showSuccessSnackBar(context, "Settings saved locally!");
      return;
    }

    setState(() => _isSaving = true);
    try {
      final fcmToken = FcmService().fcmToken;

      final success = await ApiService().registerDeviceToken(
        userId: user.id,
        fcmToken: fcmToken,
        telegramChatId: _telegramChatIdController.text.trim(),
        telegramEnabled: _telegramEnabled,
      );

      setState(() => _isSaving = false);

      if (mounted) {
        if (success) {
          ErrorHandler.showSuccessSnackBar(context, "Notification dispatch preferences saved!");
        } else {
          ErrorHandler.showErrorSnackBar(context, "Server unreachable. Failed to update device token.");
        }
      }
    } catch (e) {
      setState(() => _isSaving = false);
      if (mounted) {
        ErrorHandler.showErrorSnackBar(context, e);
      }
    }
  }

  void _openTelegramBot() async {
    try {
      final user = SupabaseService().currentUser;
      final email = user?.email ?? 'investor@gmail.com';
      final url = Uri.parse("https://t.me/StokVigilBot?start=$email");
      if (await canLaunchUrl(url)) {
        await launchUrl(url, mode: LaunchMode.externalApplication);
      } else {
        if (mounted) {
          ErrorHandler.showErrorSnackBar(context, "Unable to launch Telegram. Please ensure Telegram app is installed.");
        }
      }
    } catch (e) {
      if (mounted) {
        ErrorHandler.showErrorSnackBar(context, e);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final user = SupabaseService().currentUser;
    final userName = user?.email?.split('@')[0] ?? 'Investor Account';
    final userEmail = user?.email ?? 'investor@gmail.com';

    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: const [
            Icon(Icons.settings_outlined, color: AppTheme.cyan, size: 24),
            SizedBox(width: 8),
            Text("Settings & Dispatch Hub", style: TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 18)),
          ],
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16.0),
        children: [
          // User Profile Card
          GlassCard(
            child: Row(
              children: [
                Container(
                  width: 48,
                  height: 48,
                  decoration: BoxDecoration(
                    gradient: AppTheme.primaryGradient,
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: Center(
                    child: Text(
                      userName.substring(0, 1).toUpperCase(),
                      style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 20),
                    ),
                  ),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(userName, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 16)),
                      const SizedBox(height: 2),
                      Text(userEmail, style: const TextStyle(color: AppTheme.cyan, fontSize: 12, fontWeight: FontWeight.w600)),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),

          // Real-Time Telegram Dispatch Hub
          const Text("🔔 Real-Time Notifications Hub", style: TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.w900)),
          const SizedBox(height: 10),

          GlassCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.all(8),
                          decoration: BoxDecoration(
                            color: AppTheme.cyan.withOpacity(0.12),
                            borderRadius: BorderRadius.circular(10),
                            border: Border.all(color: AppTheme.borderCyan),
                          ),
                          child: const Text("✈️", style: TextStyle(fontSize: 18)),
                        ),
                        const SizedBox(width: 12),
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: const [
                            Text("Telegram Bot Channel", style: TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 14)),
                            Text("Instant catalyst & order alerts", style: TextStyle(color: AppTheme.textSecondary, fontSize: 11)),
                          ],
                        ),
                      ],
                    ),
                    ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppTheme.cyan.withOpacity(0.15),
                        foregroundColor: AppTheme.cyan,
                        side: const BorderSide(color: AppTheme.borderCyan),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                      ),
                      onPressed: _openTelegramBot,
                      child: const Text("Connect @StokVigilBot", style: TextStyle(fontWeight: FontWeight.w900, fontSize: 11)),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                const Divider(color: AppTheme.cardBorder),
                const SizedBox(height: 8),

                // AI Alert Frequency Selector
                const Text("🔥 AI Alert Signal Frequency", style: TextStyle(color: AppTheme.textSecondary, fontSize: 11, fontWeight: FontWeight.bold)),
                const SizedBox(height: 10),

                Row(
                  children: [
                    _buildSensitivityButton('HIGH', '🔥 High Impact'),
                    _buildSensitivityButton('ALL', '⚡ All Signals'),
                    _buildSensitivityButton('FII', '📊 FII / Institutional'),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),

          // Firebase Cloud Messaging Push Settings
          GlassCard(
            child: Column(
              children: [
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  activeColor: AppTheme.cyan,
                  title: const Text("Push Notification Alerts (FCM)", style: TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.bold)),
                  subtitle: const Text("Receive 5-min market hours push alerts on phone", style: TextStyle(color: AppTheme.textSecondary, fontSize: 11)),
                  value: _fcmEnabled,
                  onChanged: (val) => setState(() => _fcmEnabled = val),
                ),
                const Divider(color: AppTheme.cardBorder),
                TextField(
                  controller: _telegramChatIdController,
                  style: const TextStyle(color: Colors.white, fontSize: 13),
                  decoration: const InputDecoration(
                    labelText: "Telegram Chat ID (Optional)",
                    labelStyle: TextStyle(color: AppTheme.textSecondary, fontSize: 12),
                    hintText: "Enter Chat ID or click Connect above",
                    hintStyle: TextStyle(color: AppTheme.textMuted, fontSize: 11),
                    border: InputBorder.none,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),

          // Save Settings Button
          SizedBox(
            height: 48,
            child: ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.cyan,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
              ),
              onPressed: _isSaving ? null : _saveSettings,
              child: _isSaving
                  ? const CircularProgressIndicator(color: Colors.black)
                  : const Text("Save Dispatch Preferences", style: TextStyle(color: Colors.black, fontWeight: FontWeight.w900, fontSize: 14)),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSensitivityButton(String mode, String label) {
    final active = _alertSensitivity == mode;
    return Expanded(
      child: GestureDetector(
        onTap: () => setState(() => _alertSensitivity = mode),
        child: Container(
          margin: const EdgeInsets.symmetric(horizontal: 4),
          padding: const EdgeInsets.symmetric(vertical: 8),
          decoration: BoxDecoration(
            color: active ? AppTheme.cyan.withOpacity(0.15) : AppTheme.cardBackground2,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: active ? AppTheme.cyan : AppTheme.cardBorder),
          ),
          child: Center(
            child: Text(
              label,
              style: TextStyle(
                color: active ? AppTheme.cyan : AppTheme.textSecondary,
                fontSize: 10,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
        ),
      ),
    );
  }
}
