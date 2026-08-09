import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import '../config/theme.dart';
import '../models/models.dart';
import '../services/api_service.dart';
import '../services/fcm_service.dart';
import '../services/supabase_service.dart';

class NotificationSettingsScreen extends StatefulWidget {
  const NotificationSettingsScreen({super.key});

  @override
  State<NotificationSettingsScreen> createState() => _NotificationSettingsScreenState();
}

class _NotificationSettingsScreenState extends State<NotificationSettingsScreen> {
  bool _fcmEnabled = true;
  bool _telegramEnabled = false;
  String? _telegramChatId;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    final profile = await SupabaseService().fetchUserProfile();
    if (profile != null) {
      setState(() {
        _telegramChatId = profile.telegramChatId;
        _telegramEnabled = profile.telegramEnabled;
        _isLoading = false;
      });
    } else {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _toggleTelegram(bool val) async {
    final user = SupabaseService().currentUser;
    if (user == null) return;

    setState(() => _telegramEnabled = val);
    await ApiService().registerDeviceToken(
      userId: user.id,
      telegramEnabled: val,
    );
  }

  Future<void> _connectTelegramBot() async {
    final user = SupabaseService().currentUser;
    if (user == null) return;

    final botUsername = "StokVigilBot";
    final url = Uri.parse("https://t.me/$botUsername?start=${user.id}");
    if (await canLaunchUrl(url)) {
      await launchUrl(url, mode: LaunchMode.externalApplication);
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Could not open Telegram. Search @StokVigilBot on Telegram.")),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final user = SupabaseService().currentUser;

    return Scaffold(
      appBar: AppBar(title: const Text("Multi-Channel Alert Settings")),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator(color: AppTheme.primaryEmerald))
          : ListView(
              padding: const EdgeInsets.all(20),
              children: [
                const Text("Push & Messaging Delivery", style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold)),
                const SizedBox(height: 6),
                const Text("Configure how 5-minute factual alerts reach your devices.", style: TextStyle(color: AppTheme.textSecondary, fontSize: 13)),
                const SizedBox(height: 24),

                // FCM Push Setting
                Card(
                  child: SwitchListTile(
                    activeColor: AppTheme.primaryEmerald,
                    title: const Text("Android Lock-Screen Push (FCM)", style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                    subtitle: const Text("Free high-priority native notifications", style: TextStyle(color: AppTheme.textSecondary, fontSize: 12)),
                    value: _fcmEnabled,
                    onChanged: (val) {
                      setState(() => _fcmEnabled = val);
                    },
                  ),
                ),
                const SizedBox(height: 14),

                // Telegram Bot Setting
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16.0),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Row(
                              children: const [
                                Icon(Icons.send_rounded, color: Color(0F29B6F6), size: 24),
                                SizedBox(width: 10),
                                Text("Telegram Bot Alerts", style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 15)),
                              ],
                            ),
                            Switch(
                              value: _telegramEnabled,
                              activeColor: AppTheme.primaryEmerald,
                              onChanged: _toggleTelegram,
                            ),
                          ],
                        ),
                        const SizedBox(height: 8),
                        Text(
                          _telegramChatId != null
                              ? "Connected Chat ID: $_telegramChatId"
                              : "Not linked yet. Connect your Telegram Chat to receive instant market intelligence.",
                          style: const TextStyle(color: AppTheme.textSecondary, fontSize: 12),
                        ),
                        const SizedBox(height: 16),
                        SizedBox(
                          width: double.infinity,
                          child: OutlinedButton.icon(
                            style: OutlinedButton.styleFrom(
                              foregroundColor: const Color(0F29B6F6),
                              side: const BorderSide(color: Color(0F29B6F6)),
                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                            ),
                            onPressed: _connectTelegramBot,
                            icon: const Icon(Icons.telegram),
                            label: Text(
                              _telegramChatId != null ? "Re-Connect Telegram Bot" : "1-Tap Connect Telegram Bot",
                              style: const TextStyle(fontWeight: FontWeight.bold),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 30),
                const Divider(color: AppTheme.cardBorder),
                const SizedBox(height: 16),
                Center(
                  child: TextButton.icon(
                    onPressed: () async {
                      await SupabaseService().signOut();
                      Navigator.of(context).popUntil((route) => route.isFirst);
                    },
                    icon: const Icon(Icons.logout, color: AppTheme.dangerRose),
                    label: const Text("Sign Out of StokVigil AI", style: TextStyle(color: AppTheme.dangerRose, fontWeight: FontWeight.bold)),
                  ),
                )
              ],
            ),
    );
  }
}
