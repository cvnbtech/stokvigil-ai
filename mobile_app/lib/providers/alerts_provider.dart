import 'dart:async';
import 'package:flutter/foundation.dart';
import '../models/models.dart';
import '../services/api_service.dart';
import '../services/supabase_service.dart';

class AlertsProvider extends ChangeNotifier {
  List<StokAlert> _alerts = [];
  bool _isLoading = true;
  String _selectedFilter = 'all';
  String? _currentUserId;

  StreamSubscription<List<StokAlert>>? _alertsSub;

  List<StokAlert> get alerts => _alerts;
  bool get isLoading => _isLoading;
  String get selectedFilter => _selectedFilter;

  List<StokAlert> get filteredAlerts {
    return _alerts.where((a) {
      if (_selectedFilter == 'defense') {
        final b = a.actionBias.toUpperCase();
        return b.contains('CAPITAL_PRESERVATION') ||
            b.contains('MIS_SHORT') ||
            b.contains('INTRADAY_MIS') ||
            a.alertTitle.toUpperCase().contains('CAPITAL') ||
            a.alertTitle.toUpperCase().contains('MIS');
      }
      if (_selectedFilter == 'high') return a.impactScore >= 80;
      if (_selectedFilter == 'earnings') {
        return a.catalystType == 'EARNINGS_BEAT' ||
            a.alertTitle.toUpperCase().contains('EARNING') ||
            a.alertTitle.toUpperCase().contains('REVENUE');
      }
      if (_selectedFilter == 'breakout') {
        return a.catalystType == 'PRICE_BREAKOUT' ||
            a.alertTitle.toUpperCase().contains('BREAKOUT') ||
            a.alertTitle.toUpperCase().contains('HIGH');
      }
      if (_selectedFilter == 'volume') {
        return a.catalystType == 'VOLUME_SURGE' ||
            a.alertTitle.toUpperCase().contains('VOLUME') ||
            a.factualReasons.any((r) => r.toUpperCase().contains('VOLUME'));
      }
      if (_selectedFilter == 'fii') {
        return a.catalystType == 'BLOCK_DEAL' ||
            a.catalystType == 'DEBT_CHANGE' ||
            a.alertTitle.toUpperCase().contains('FII') ||
            a.alertTitle.toUpperCase().contains('DEAL') ||
            a.alertTitle.toUpperCase().contains('BLOCK');
      }
      if (_selectedFilter == 'trailing') {
        return a.actionBias.contains('TRAILING') ||
            a.alertTitle.toUpperCase().contains('TRAILING');
      }
      return true;
    }).toList();
  }

  void initialize(String? userId) {
    if (_currentUserId == userId && _alertsSub != null) {
      return;
    }
    _currentUserId = userId;
    _alertsSub?.cancel();

    if (userId == null || userId.isEmpty) {
      _alerts = [];
      _isLoading = false;
      notifyListeners();
      return;
    }

    _subscribeToAlerts(userId);
  }

  void setFilter(String filter) {
    if (_selectedFilter != filter) {
      _selectedFilter = filter;
      notifyListeners();
    }
  }

  void clear() {
    _alertsSub?.cancel();
    _alertsSub = null;
    _currentUserId = null;
    _alerts = [];
    _isLoading = false;
    notifyListeners();
  }

  void _subscribeToAlerts(String userId) {
    _isLoading = true;
    notifyListeners();

    _alertsSub = SupabaseService().streamAlerts().listen(
      (liveAlerts) {
        _alerts = liveAlerts;
        _isLoading = false;
        notifyListeners();
      },
      onError: (err) {
        debugPrint("Realtime alerts stream error in provider: $err");
        fetchAlertsFallback(userId);
      },
    );
  }

  Future<void> fetchAlertsFallback(String userId) async {
    try {
      final list = await ApiService().fetchAlerts(userId);
      _alerts = list;
      _isLoading = false;
      notifyListeners();
    } catch (e) {
      debugPrint("Error fetching alerts fallback: $e");
      _isLoading = false;
      notifyListeners();
    }
  }

  @override
  void dispose() {
    _alertsSub?.cancel();
    super.dispose();
  }
}
