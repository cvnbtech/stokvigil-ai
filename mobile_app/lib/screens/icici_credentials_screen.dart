import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import '../config/theme.dart';
import '../services/api_service.dart';
import '../services/supabase_service.dart';

class IciciCredentialsScreen extends StatefulWidget {
  final VoidCallback onSaved;

  const IciciCredentialsScreen({super.key, required this.onSaved});

  @override
  State<IciciCredentialsScreen> createState() => _IciciCredentialsScreenState();
}

class _IciciCredentialsScreenState extends State<IciciCredentialsScreen> {
  final _appKeyController = TextEditingController();
  final _secretKeyController = TextEditingController();
  final _sessionTokenController = TextEditingController();
  bool _isLoading = false;
  String? _statusMessage;

  Future<void> _launchIciciLogin() async {
    final appKey = _appKeyController.text.trim();
    if (appKey.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Please enter your ICICI Breeze App Key first.")),
      );
      return;
    }
    final url = Uri.parse("https://api.icicidirect.com/apiuser/login?api_key=${Uri.encodeComponent(appKey)}");
    if (await canLaunchUrl(url)) {
      await launchUrl(url, mode: LaunchMode.externalApplication);
    }
  }

  Future<void> _saveCredentials() async {
    final user = SupabaseService().currentUser;
    if (user == null) return;

    setState(() {
      _isLoading = true;
      _statusMessage = null;
    });

    final success = await ApiService().saveIciciCredentials(
      userId: user.id,
      appKey: _appKeyController.text.trim(),
      secretKey: _secretKeyController.text.trim(),
      sessionToken: _sessionTokenController.text.trim(),
    );

    setState(() {
      _isLoading = false;
    });

    if (success) {
      widget.onSaved();
    } else {
      setState(() {
        _statusMessage = "Failed to save credentials. Please check inputs.";
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("ICICI Breeze API Setup")),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppTheme.primaryEmerald.withOpacity(0.1),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: AppTheme.primaryEmerald.withOpacity(0.3)),
              ),
              child: Row(
                children: const [
                  Icon(Icons.lock_clock, color: AppTheme.primaryEmerald, size: 28),
                  SizedBox(width: 14),
                  Expanded(
                    child: Text(
                      "Daily Session Token Vault\nEncrypted using AES-256 (PostgreSQL RLS)",
                      style: TextStyle(color: Colors.white, fontSize: 13, height: 1.4),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),
            TextField(
              controller: _appKeyController,
              style: const TextStyle(color: Colors.white),
              decoration: InputDecoration(
                labelText: "ICICI Breeze App Key",
                labelStyle: const TextStyle(color: AppTheme.textSecondary),
                filled: true,
                fillColor: AppTheme.cardBackground,
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
              ),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _secretKeyController,
              obscureText: true,
              style: const TextStyle(color: Colors.white),
              decoration: InputDecoration(
                labelText: "ICICI Breeze Secret Key",
                labelStyle: const TextStyle(color: AppTheme.textSecondary),
                filled: true,
                fillColor: AppTheme.cardBackground,
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
              ),
            ),
            const SizedBox(height: 24),
            OutlinedButton.icon(
              style: OutlinedButton.styleFrom(
                foregroundColor: AppTheme.primaryEmerald,
                side: const BorderSide(color: AppTheme.primaryEmerald),
                minimumSize: const Size(double.infinity, 48),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
              onPressed: _launchIciciLogin,
              icon: const Icon(Icons.open_in_browser),
              label: const Text("Launch 1-Tap ICICI Login for Today's Token", style: TextStyle(fontWeight: FontWeight.bold)),
            ),
            const SizedBox(height: 24),
            TextField(
              controller: _sessionTokenController,
              style: const TextStyle(color: Colors.white),
              decoration: InputDecoration(
                labelText: "Paste Today's Session Token",
                labelStyle: const TextStyle(color: AppTheme.textSecondary),
                filled: true,
                fillColor: AppTheme.cardBackground,
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
              ),
            ),
            const SizedBox(height: 24),
            if (_statusMessage != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 16.0),
                child: Text(_statusMessage!, style: const TextStyle(color: AppTheme.dangerRose, fontSize: 13)),
              ),
            SizedBox(
              width: double.infinity,
              height: 50,
              child: ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.primaryEmerald,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
                onPressed: _isLoading ? null : _saveCredentials,
                child: _isLoading
                    ? const CircularProgressIndicator(color: Colors.black)
                    : const Text("Encrypt & Save Credentials", style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold, fontSize: 16)),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
