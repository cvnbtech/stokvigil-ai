import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../config/theme.dart';
import '../services/api_service.dart';
import '../widgets/custom_widgets.dart';

/// Public Audited Accuracy Ledger & Track Record Screen.
/// Displays verifiable signal outcomes, Target 1 hit rates %, risk-to-reward ratios,
/// and complete signal execution history tracked against live NSE ticks.
class AuditLedgerScreen extends StatefulWidget {
  const AuditLedgerScreen({super.key});

  @override
  State<AuditLedgerScreen> createState() => _AuditLedgerScreenState();
}

class _AuditLedgerScreenState extends State<AuditLedgerScreen> {
  bool _isLoading = true;
  String? _errorMessage;
  Map<String, dynamic>? _summary;
  List<Map<String, dynamic>> _ledger = [];
  String _searchQuery = "";
  String _selectedOutcomeFilter = "ALL";
  final TextEditingController _searchController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _loadLedger();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _loadLedger() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    final data = await ApiService().fetchAccuracyLedger();
    if (!mounted) return;

    if (data == null) {
      setState(() {
        _isLoading = false;
        _errorMessage = "Unable to connect to audited ledger service. Please try again.";
      });
      return;
    }

    setState(() {
      _summary = data['audited_summary'] as Map<String, dynamic>?;
      final rawList = (data['ledger'] as List?) ?? [];
      _ledger = rawList.map((e) => Map<String, dynamic>.from(e)).toList();
      _isLoading = false;
    });
  }

  List<Map<String, dynamic>> get _filteredLedger {
    return _ledger.where((item) {
      final sym = (item['symbol'] ?? '').toString().toLowerCase();
      final title = (item['title'] ?? '').toString().toLowerCase();
      final catalyst = (item['catalyst'] ?? '').toString().toLowerCase();
      final q = _searchQuery.toLowerCase().trim();

      final matchesSearch = q.isEmpty || sym.contains(q) || title.contains(q) || catalyst.contains(q);
      final outcome = (item['outcome'] ?? '').toString();
      final matchesOutcome = _selectedOutcomeFilter == "ALL" || outcome == _selectedOutcomeFilter;

      return matchesSearch && matchesOutcome;
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    final filtered = _filteredLedger;

    return Scaffold(
      backgroundColor: AppTheme.darkBackground,
      appBar: AppBar(
        backgroundColor: AppTheme.darkBackground,
        elevation: 0,
        title: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(6),
              decoration: BoxDecoration(
                color: AppTheme.primaryEmerald.withOpacity(0.15),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: AppTheme.primaryEmerald.withOpacity(0.4)),
              ),
              child: const Icon(Icons.verified_outlined, color: AppTheme.primaryEmerald, size: 18),
            ),
            const SizedBox(width: 10),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: const [
                Text(
                  "Audit Ledger",
                  style: TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 16),
                ),
                Text(
                  "100% NON-REPUDIATION VERIFIED",
                  style: TextStyle(color: AppTheme.cyan, fontWeight: FontWeight.w800, fontSize: 9.5, letterSpacing: 0.6),
                ),
              ],
            ),
          ],
        ),
        actions: [
          IconButton(
            onPressed: _loadLedger,
            icon: const Icon(Icons.refresh, color: AppTheme.cyan),
            tooltip: "Refresh Ledger",
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _loadLedger,
        color: AppTheme.cyan,
        backgroundColor: AppTheme.cardBackground,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            // Top Hero Card
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [Color(0xFF0D1629), Color(0xFF080B16)],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                borderRadius: BorderRadius.circular(18),
                border: Border.all(color: AppTheme.borderCyan),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: AppTheme.primaryEmerald.withOpacity(0.12),
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(color: AppTheme.primaryEmerald.withOpacity(0.35)),
                    ),
                    child: const Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text("🛡️", style: TextStyle(fontSize: 12)),
                        SizedBox(width: 6),
                        Text(
                          "IMMUTABLE TRACK RECORD",
                          style: TextStyle(color: AppTheme.primaryEmerald, fontWeight: FontWeight.w900, fontSize: 10),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 10),
                  const Text(
                    "Public Audited Accuracy Ledger",
                    style: TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 18),
                  ),
                  const SizedBox(height: 6),
                  const Text(
                    "Every surveillance alert is recorded with an immutable timestamp and audited against tick-level National Stock Exchange (NSE) execution.",
                    style: TextStyle(color: AppTheme.textSecondary, fontSize: 11.5, height: 1.4),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 14),

            // KPI Scorecards 2x2 Grid
            Row(
              children: [
                Expanded(
                  child: _buildKpiCard(
                    title: "TARGET 1 HIT RATE",
                    value: _summary != null && (_summary!['total_verified_signals'] ?? 0) > 0
                        ? "${_summary!['win_rate_pct']}%"
                        : (_isLoading ? "..." : "--"),
                    sub: "Signals hitting Target 1 before SL",
                    accentColor: AppTheme.primaryEmerald,
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: _buildKpiCard(
                    title: "VERIFIED SIGNALS",
                    value: _summary != null ? "${_summary!['total_verified_signals']}" : (_isLoading ? "..." : "--"),
                    sub: "Audited NIFTY & F&O alerts",
                    accentColor: AppTheme.cyan,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            Row(
              children: [
                Expanded(
                  child: _buildKpiCard(
                    title: "AVG RISK:REWARD",
                    value: _summary != null && _summary!['avg_risk_reward'] != "-"
                        ? "${_summary!['avg_risk_reward']}"
                        : (_isLoading ? "..." : "--"),
                    sub: "Asymmetric Volatility Ratio",
                    accentColor: const Color(0xFF38BDF8),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: _buildKpiCard(
                    title: "PROFIT FACTOR",
                    value: _summary != null && (_summary!['profit_factor'] ?? 0) > 0
                        ? "${_summary!['profit_factor']}"
                        : (_isLoading ? "..." : "--"),
                    sub: "Gross profit vs gross loss",
                    accentColor: const Color(0xFFA855F7),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),

            // Quantitative Methodology Card
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: AppTheme.cyan.withOpacity(0.04),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: AppTheme.borderCyan),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: const [
                      Text("🔬", style: TextStyle(fontSize: 14)),
                      SizedBox(width: 8),
                      Text(
                        "QUANTITATIVE VERIFICATION STANDARDS",
                        style: TextStyle(color: AppTheme.cyan, fontWeight: FontWeight.w900, fontSize: 11),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Text(
                    _summary?['audit_methodology'] ??
                        "A signal is verified as 'TARGET_1_REACHED' only if price achieves Target 1 prior to breaching the protective stop-loss floor on NSE cash/F&O market sessions.",
                    style: const TextStyle(color: Color(0xFFCBD5E1), fontSize: 11, height: 1.45),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // Search Bar
            Container(
              decoration: BoxDecoration(
                color: const Color(0xFF080B16),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppTheme.cardBorder),
              ),
              child: TextField(
                controller: _searchController,
                style: const TextStyle(color: Colors.white, fontSize: 12.5),
                onChanged: (val) => setState(() => _searchQuery = val),
                decoration: InputDecoration(
                  hintText: "Search ticker or catalyst (e.g. RELIANCE)...",
                  hintStyle: const TextStyle(color: AppTheme.textMuted, fontSize: 11.5),
                  prefixIcon: const Icon(Icons.search, color: AppTheme.cyan, size: 18),
                  suffixIcon: _searchQuery.isNotEmpty
                      ? IconButton(
                          icon: const Icon(Icons.clear, color: AppTheme.textSecondary, size: 16),
                          onPressed: () {
                            _searchController.clear();
                            setState(() => _searchQuery = "");
                          },
                        )
                      : null,
                  border: InputBorder.none,
                  contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                ),
              ),
            ),
            const SizedBox(height: 10),

            // Outcome Filter Chips
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  _buildFilterChip("ALL", "All Signals"),
                  _buildFilterChip("TARGET_1_REACHED", "🎯 Target 1 Reached"),
                  _buildFilterChip("STOP_LOSS_DEFENDED", "🛡️ Stop Loss Defended"),
                ],
              ),
            ),
            const SizedBox(height: 14),

            // Ledger Cards List
            if (_isLoading) ...[
              const Center(
                child: Padding(
                  padding: EdgeInsets.all(32.0),
                  child: CircularProgressIndicator(color: AppTheme.cyan),
                ),
              ),
            ] else if (_errorMessage != null) ...[
              Center(
                child: Padding(
                  padding: const EdgeInsets.all(24.0),
                  child: Column(
                    children: [
                      const Icon(Icons.error_outline, color: AppTheme.dangerRose, size: 36),
                      const SizedBox(height: 10),
                      Text(_errorMessage!, style: const TextStyle(color: AppTheme.dangerRose, fontSize: 12), textAlign: TextAlign.center),
                      const SizedBox(height: 12),
                      OutlinedButton(
                        onPressed: _loadLedger,
                        style: OutlinedButton.styleFrom(side: const BorderSide(color: AppTheme.borderCyan)),
                        child: const Text("Retry", style: TextStyle(color: AppTheme.cyan)),
                      ),
                    ],
                  ),
                ),
              ),
            ] else if (filtered.isEmpty) ...[
              Center(
                child: Padding(
                  padding: const EdgeInsets.all(32.0),
                  child: Column(
                    children: const [
                      Icon(Icons.inbox_outlined, color: AppTheme.textMuted, size: 48),
                      SizedBox(height: 12),
                      Text("No signals match the selected filter.", style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                      SizedBox(height: 6),
                      Text("New signals will appear automatically once evaluated.", style: TextStyle(color: AppTheme.textSecondary, fontSize: 11)),
                    ],
                  ),
                ),
              ),
            ] else ...[
              ...filtered.map((item) {
                final symbol = (item['symbol'] ?? '').toString();
                final title = (item['title'] ?? '').toString();
                final catalyst = (item['catalyst'] ?? '').toString().replaceAll('_', ' ');
                final score = (item['confluence_score'] ?? 0) as num;
                final entry = (item['entry_range'] ?? '-').toString();
                final target = (item['target_1'] ?? '-').toString();
                final sl = (item['stop_loss'] ?? '-').toString();
                final rr = (item['risk_reward'] ?? '-').toString();
                final outcome = (item['outcome'] ?? '').toString();
                final isWin = outcome == "TARGET_1_REACHED";

                String dateStr = "";
                if (item['created_at'] != null) {
                  try {
                    final dt = DateTime.parse(item['created_at'].toString());
                    dateStr = DateFormat('dd MMM, hh:mm a').format(dt.toLocal());
                  } catch (_) {
                    dateStr = item['created_at'].toString();
                  }
                }

                return GlassCard(
                  margin: const EdgeInsets.only(bottom: 12),
                  borderColor: isWin ? AppTheme.primaryEmerald.withOpacity(0.35) : AppTheme.cardBorder,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Top Row: Symbol, Date, Outcome Badge
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Row(
                            children: [
                              Text(
                                "[$symbol]",
                                style: const TextStyle(color: AppTheme.cyan, fontWeight: FontWeight.w900, fontSize: 15),
                              ),
                              const SizedBox(width: 8),
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                decoration: BoxDecoration(
                                  color: AppTheme.cyan.withOpacity(0.12),
                                  borderRadius: BorderRadius.circular(6),
                                  border: Border.all(color: AppTheme.cyan.withOpacity(0.3)),
                                ),
                                child: Text(
                                  catalyst,
                                  style: const TextStyle(color: AppTheme.cyan, fontSize: 9.5, fontWeight: FontWeight.w800),
                                ),
                              ),
                            ],
                          ),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                            decoration: BoxDecoration(
                              color: isWin ? AppTheme.primaryEmerald.withOpacity(0.15) : AppTheme.secondaryAmber.withOpacity(0.15),
                              borderRadius: BorderRadius.circular(8),
                              border: Border.all(
                                color: isWin ? AppTheme.primaryEmerald : AppTheme.secondaryAmber,
                              ),
                            ),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(
                                  isWin ? Icons.check_circle_outline : Icons.shield_outlined,
                                  color: isWin ? AppTheme.primaryEmerald : AppTheme.secondaryAmber,
                                  size: 11,
                                ),
                                const SizedBox(width: 4),
                                Text(
                                  isWin ? "TARGET 1 REACHED" : "SL DEFENDED",
                                  style: TextStyle(
                                    color: isWin ? AppTheme.primaryEmerald : AppTheme.secondaryAmber,
                                    fontSize: 9.5,
                                    fontWeight: FontWeight.w900,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),

                      // Title
                      Text(
                        title,
                        style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 13, height: 1.3),
                      ),
                      if (dateStr.isNotEmpty) ...[
                        const SizedBox(height: 4),
                        Text(
                          dateStr,
                          style: const TextStyle(color: AppTheme.textMuted, fontSize: 10, fontWeight: FontWeight.w600),
                        ),
                      ],
                      const SizedBox(height: 10),

                      // Tactical Levels Grid
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                        decoration: BoxDecoration(
                          color: const Color(0xFF080B16),
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(color: AppTheme.cardBorder),
                        ),
                        child: Wrap(
                          spacing: 12,
                          runSpacing: 4,
                          alignment: WrapAlignment.spaceBetween,
                          children: [
                            Text("📍 Entry: $entry", style: const TextStyle(color: AppTheme.textSecondary, fontSize: 11, fontWeight: FontWeight.w700)),
                            Text("🎯 Target: $target", style: const TextStyle(color: AppTheme.primaryEmerald, fontSize: 11, fontWeight: FontWeight.w900)),
                            Text("🛡️ SL: $sl", style: const TextStyle(color: AppTheme.dangerRose, fontSize: 11, fontWeight: FontWeight.w900)),
                            Text("⚖️ R:R: $rr", style: const TextStyle(color: AppTheme.cyan, fontSize: 11, fontWeight: FontWeight.w800)),
                            Text("Score: $score/100", style: TextStyle(color: score >= 75 ? AppTheme.primaryEmerald : AppTheme.secondaryAmber, fontSize: 11, fontWeight: FontWeight.w800)),
                          ],
                        ),
                      ),
                    ],
                  ),
                );
              }),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildKpiCard({
    required String title,
    required String value,
    required String sub,
    required Color accentColor,
  }) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFF080B16),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppTheme.cardBorder),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: const TextStyle(color: AppTheme.textMuted, fontSize: 9.5, fontWeight: FontWeight.w800, letterSpacing: 0.5),
          ),
          const SizedBox(height: 6),
          Text(
            value,
            style: TextStyle(color: accentColor, fontSize: 22, fontWeight: FontWeight.w900),
          ),
          const SizedBox(height: 4),
          Text(
            sub,
            style: const TextStyle(color: AppTheme.textSecondary, fontSize: 10, height: 1.2),
          ),
        ],
      ),
    );
  }

  Widget _buildFilterChip(String key, String label) {
    final isSelected = _selectedOutcomeFilter == key;
    return GestureDetector(
      onTap: () => setState(() => _selectedOutcomeFilter = key),
      child: Container(
        margin: const EdgeInsets.only(right: 8),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: isSelected ? AppTheme.cyan.withOpacity(0.18) : const Color(0xFF080B16),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(
            color: isSelected ? AppTheme.cyan.withOpacity(0.5) : AppTheme.cardBorder,
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: isSelected ? AppTheme.cyan : AppTheme.textSecondary,
            fontSize: 11,
            fontWeight: isSelected ? FontWeight.w900 : FontWeight.w600,
          ),
        ),
      ),
    );
  }
}

