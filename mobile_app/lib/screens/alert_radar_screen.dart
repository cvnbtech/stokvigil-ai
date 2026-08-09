import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../config/theme.dart';
import '../models/models.dart';
import '../services/api_service.dart';
import '../services/supabase_service.dart';

class AlertRadarScreen extends StatefulWidget {
  const AlertRadarScreen({super.key});

  @override
  State<AlertRadarScreen> createState() => _AlertRadarScreenState();
}

class _AlertRadarScreenState extends State<AlertRadarScreen> {
  bool _isLoading = true;
  List<StokAlert> _alerts = [];

  @override
  void initState() {
    super.initState();
    _loadAlerts();
  }

  Future<void> _loadAlerts() async {
    final user = SupabaseService().currentUser;
    if (user == null) return;

    setState(() => _isLoading = true);
    final list = await ApiService().fetchAlerts(user.id);
    setState(() {
      _alerts = list;
      _isLoading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("StokVigil Alert Radar"),
        actions: [
          IconButton(onPressed: _loadAlerts, icon: const Icon(Icons.refresh)),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _loadAlerts,
        color: AppTheme.primaryEmerald,
        child: _isLoading
            ? const Center(child: CircularProgressIndicator(color: AppTheme.primaryEmerald))
            : _alerts.isEmpty
                ? Center(
                    child: Padding(
                      padding: const EdgeInsets.all(32.0),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: const [
                          Icon(Icons.radar_outlined, color: AppTheme.textSecondary, size: 64),
                          SizedBox(height: 16),
                          Text("No High-Impact Catalysts Yet", style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold)),
                          SizedBox(height: 8),
                          Text(
                            "StokVigil scans your portfolio every 5 mins during Indian market hours. Noise is filtered out automatically.",
                            textAlign: TextAlign.center,
                            style: TextStyle(color: AppTheme.textSecondary, fontSize: 13),
                          ),
                        ],
                      ),
                    ),
                  )
                : ListView.builder(
                    padding: const EdgeInsets.all(16),
                    itemCount: _alerts.length,
                    itemBuilder: (context, index) {
                      final alert = _alerts[index];
                      final isHigh = alert.impactScore >= 80;
                      final badgeColor = isHigh ? AppTheme.primaryEmerald : AppTheme.secondaryAmber;
                      final dateStr = DateFormat('dd MMM, hh:mm a').format(alert.createdAt);

                      return Card(
                        margin: const EdgeInsets.only(bottom: 14),
                        child: ExpansionTile(
                          shape: const Border(),
                          tilePadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                          title: Row(
                            children: [
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                decoration: BoxDecoration(
                                  color: badgeColor.withOpacity(0.15),
                                  borderRadius: BorderRadius.circular(6),
                                  border: Border.all(color: badgeColor, width: 1),
                                ),
                                child: Text(
                                  "${isHigh ? 'HIGH' : 'MED'} IMPACT ${alert.impactScore}%",
                                  style: TextStyle(color: badgeColor, fontSize: 10, fontWeight: FontWeight.bold),
                                ),
                              ),
                              const SizedBox(width: 10),
                              Text(alert.symbol, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16)),
                            ],
                          ),
                          subtitle: Padding(
                            padding: const EdgeInsets.only(top: 6.0),
                            child: Text(
                              alert.alertTitle,
                              style: const TextStyle(color: AppTheme.textPrimary, fontSize: 13, fontWeight: FontWeight.w600),
                            ),
                          ),
                          trailing: Text(dateStr, style: const TextStyle(color: AppTheme.textSecondary, fontSize: 10)),
                          children: [
                            Padding(
                              padding: const EdgeInsets.all(16.0),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  const Divider(color: AppTheme.cardBorder),
                                  const SizedBox(height: 8),
                                  const Text("Factual Catalyst Reasons:", style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13)),
                                  const SizedBox(height: 6),
                                  ...alert.factualReasons.map((reason) => Padding(
                                        padding: const EdgeInsets.only(bottom: 4.0),
                                        child: Row(
                                          crossAxisAlignment: CrossAxisAlignment.start,
                                          children: [
                                            const Text("• ", style: TextStyle(color: AppTheme.primaryEmerald, fontWeight: FontWeight.bold)),
                                            Expanded(child: Text(reason, style: const TextStyle(color: AppTheme.textPrimary, fontSize: 12))),
                                          ],
                                        ),
                                      )),
                                  const SizedBox(height: 12),
                                  if (alert.metricsSnapshot.isNotEmpty) ...[
                                    Container(
                                      padding: const EdgeInsets.all(10),
                                      decoration: BoxDecoration(
                                        color: AppTheme.darkBackground,
                                        borderRadius: BorderRadius.circular(8),
                                      ),
                                      child: Row(
                                        mainAxisAlignment: MainAxisAlignment.spaceAround,
                                        children: [
                                          _buildMetricChip("Live Price", "₹${alert.metricsSnapshot['price'] ?? '-'}"),
                                          _buildMetricChip("P/E Ratio", "${alert.metricsSnapshot['pe_ratio'] ?? '-'}"),
                                          _buildMetricChip("Debt/Eq", "${alert.metricsSnapshot['debt_to_equity'] ?? '-'}"),
                                        ],
                                      ),
                                    ),
                                    const SizedBox(height: 10),
                                  ],
                                  const Text(
                                    "⚠️ Pure intelligence alert — non-advisory, factual data.",
                                    style: TextStyle(color: AppTheme.textSecondary, fontSize: 10, fontStyle: FontStyle.italic),
                                  ),
                                ],
                              ),
                            )
                          ],
                        ),
                      );
                    },
                  ),
      ),
    );
  }

  Widget _buildMetricChip(String label, String val) {
    return Column(
      children: [
        Text(label, style: const TextStyle(color: AppTheme.textSecondary, fontSize: 10)),
        const SizedBox(height: 2),
        Text(val, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 12)),
      ],
    );
  }
}
