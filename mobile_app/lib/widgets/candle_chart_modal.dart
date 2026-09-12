import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show rootBundle;
import 'package:webview_flutter/webview_flutter.dart';
import '../config/theme.dart';
import '../screens/candle_chart_screen.dart';
import '../services/api_service.dart';

/// Modal bottom sheet that renders TradingView Lightweight Charts with
/// Camarilla Institutional Equation levels (H4, H3, L3, L4), VWAP, and
/// Chandelier Trailing Stop Loss via an optimized in-app WebView.
class CandleChartModal extends StatefulWidget {
  final String symbol;

  const CandleChartModal({super.key, required this.symbol});

  static void show(BuildContext context, {required String symbol}) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => CandleChartModal(symbol: symbol),
    );
  }

  @override
  State<CandleChartModal> createState() => _CandleChartModalState();
}

class _CandleChartModalState extends State<CandleChartModal> {
  String _selectedInterval = "5m";
  bool _isLoading = true;
  String? _errorMessage;
  Map<String, dynamic>? _candlePayload;
  WebViewController? _webViewController;
  String _bundledJs = "";

  static const List<String> _intervals = ["1m", "5m", "15m", "1h", "1d"];

  @override
  void initState() {
    super.initState();
    _initWebView();
    _initAndLoad();
  }

  Future<void> _initAndLoad() async {
    await _loadJsBundle();
    await _loadChartData();
  }

  void _initWebView() {
    _webViewController = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setBackgroundColor(const Color(0xFF080B16))
      ..setNavigationDelegate(
        NavigationDelegate(
          onWebResourceError: (error) {
            debugPrint("WebView error: ${error.description}");
          },
        ),
      );
  }

  Future<void> _loadJsBundle() async {
    try {
      final js = await rootBundle.loadString(
        'assets/js/lightweight-charts.standalone.production.js',
      );
      if (mounted) {
        _bundledJs = js;
      }
    } catch (e) {
      debugPrint("Note: Bundled JS asset not found in bundle, using CDN: $e");
    }
  }

  Future<void> _loadChartData() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    final period = (_selectedInterval == "1d") ? "1y" : "5d";
    final data = await ApiService().fetchStockCandles(
      symbol: widget.symbol,
      interval: _selectedInterval,
      period: period,
    );

    if (!mounted) return;

    if (data == null) {
      setState(() {
        _isLoading = false;
        _errorMessage = "Unable to fetch candle data from backend.";
      });
      return;
    }

    final candles = (data['candles'] as List?) ?? [];
    if (candles.isEmpty) {
      setState(() {
        _isLoading = false;
        _errorMessage = "No historical bars available for ${widget.symbol}.";
      });
      return;
    }

    setState(() {
      _candlePayload = data;
      _isLoading = false;
    });

    if (_bundledJs.isEmpty) {
      await _loadJsBundle();
    }

    // Generate HTML with embedded JSON and render in WebView
    final htmlContent = _buildHtmlString(data);
    _webViewController?.loadHtmlString(
      htmlContent,
      baseUrl: "https://appassets.androidplatform.net",
    );
  }

  String _buildHtmlString(Map<String, dynamic> data) {
    final candles = data['candles'] ?? [];
    final camarilla = data['camarilla'] ?? {};
    final candlesJson = jsonEncode(candles);
    final camarillaJson = jsonEncode(camarilla);

    final scriptTag = _bundledJs.isNotEmpty
        ? '<script>$_bundledJs</script>'
        : '<script src="https://unpkg.com/lightweight-charts@5.2.1/dist/lightweight-charts.standalone.production.js"></script>';

    return '''<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; user-select: none; -webkit-user-select: none; }
    html, body {
      width: 100%;
      height: 100%;
      background-color: #080B16;
      color: #94a3b8;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      overflow: hidden;
      position: relative;
    }
    #chart {
      width: 100%;
      height: 100%;
    }
  </style>
  $scriptTag
  <script>
    if (typeof window.LightweightCharts === 'undefined') {
      var s = document.createElement('script');
      s.src = 'https://unpkg.com/lightweight-charts@5.2.1/dist/lightweight-charts.standalone.production.js';
      document.head.appendChild(s);
    }
  </script>
</head>
<body>
  <div id="chart"></div>
  <!-- StokVigil Brand Watermark -->
  <div style="position:absolute; inset:0; display:flex; flex-direction:column; align-items:center; justify-content:center; pointer-events:none; z-index:1; opacity:0.06; user-select:none;">
    <div style="font-size:72px; font-weight:900; letter-spacing:6px; color:#38bdf8;">SV</div>
    <div style="font-size:12px; font-weight:800; letter-spacing:8px; color:#ffffff; margin-top:2px;">STOKVIGIL AI</div>
  </div>
  <!-- Floating Brand Pill Badge -->
  <div style="position:absolute; top:8px; left:8px; display:flex; flex-direction:column; gap:2px; background:rgba(8,11,22,0.85); backdrop-filter:blur(8px); border:1px solid rgba(6,182,212,0.4); border-radius:7px; padding:3px 8px; z-index:2; pointer-events:none; box-shadow:0 3px 10px rgba(0,0,0,0.5), 0 0 8px rgba(6,182,212,0.15);">
    <div style="display:flex; align-items:center; gap:5px;">
      <div style="display:flex; align-items:center; gap:2px; padding:1px 4px; border-radius:3px; background:linear-gradient(135deg, #06b6d4, #10b981); font-size:8px; font-weight:900; color:#fff; letter-spacing:0.5px;"><span>⚡</span>SV</div>
      <span style="font-size:9.5px; font-weight:900; color:#ffffff; letter-spacing:0.5px;">STOKVIGIL AI</span>
      <span style="font-size:8px; color:#06b6d4; font-weight:700;">•</span>
      <span style="font-size:8.5px; font-weight:700; color:#94a3b8; letter-spacing:0.4px;">${_selectedInterval.toUpperCase()}</span>
    </div>
    <span style="font-size:7.5px; color:#64748b; font-weight:600; letter-spacing:0.3px;">StokVigil Watchtower</span>
  </div>
  <script>
    (function initChart() {
      if (typeof window.LightweightCharts === 'undefined') {
        setTimeout(initChart, 50);
        return;
      }

      var LC = window.LightweightCharts;
      var container = document.getElementById('chart');

      var chart = LC.createChart(container, {
        layout: {
          background: { color: '#080B16' },
          textColor: '#94a3b8',
        },
        grid: {
          vertLines: { color: 'rgba(255, 255, 255, 0.04)' },
          horzLines: { color: 'rgba(255, 255, 255, 0.04)' },
        },
        timeScale: {
          borderColor: 'rgba(255, 255, 255, 0.1)',
          timeVisible: true,
          secondsVisible: false,
        },
        crosshair: {
          vertLine: { color: '#06b6d4', width: 1, style: (LC.LineStyle ? LC.LineStyle.Dashed : 2) },
          horzLine: { color: '#06b6d4', width: 1, style: (LC.LineStyle ? LC.LineStyle.Dashed : 2) },
        },
        rightPriceScale: {
          borderColor: 'rgba(255, 255, 255, 0.1)',
        },
        width: container.clientWidth || window.innerWidth,
        height: container.clientHeight || window.innerHeight,
      });

      var candles = $candlesJson;
      var camarilla = $camarillaJson;

      // Helper to add series across v4 and v5
      function addSeries(typeName, options) {
        if (chart.addSeries && LC[typeName]) {
          return chart.addSeries(LC[typeName], options);
        }
        var m = 'add' + typeName;
        if (typeof chart[m] === 'function') {
          return chart[m](options);
        }
        return null;
      }

      // 1. Candlestick Series
      var candleSeries = addSeries('CandlestickSeries', {
        upColor: '#10b981',
        downColor: '#f43f5e',
        borderUpColor: '#10b981',
        borderDownColor: '#f43f5e',
        wickUpColor: '#10b981',
        wickDownColor: '#f43f5e',
      });

      if (candleSeries && candles.length > 0) {
        candleSeries.setData(candles.map(function(c) {
          return { time: c.time, open: c.open, high: c.high, low: c.low, close: c.close };
        }));
      }

      // 2. Volume Series
      var volumeSeries = addSeries('HistogramSeries', {
        color: 'rgba(6, 182, 212, 0.25)',
        priceFormat: { type: 'volume' },
        priceScaleId: '',
      });
      if (volumeSeries && candles.length > 0) {
        volumeSeries.priceScale().applyOptions({
          scaleMargins: { top: 0.82, bottom: 0 },
        });
        volumeSeries.setData(candles.map(function(c) {
          return {
            time: c.time,
            value: c.volume || 0,
            color: c.close >= c.open ? 'rgba(16, 185, 129, 0.3)' : 'rgba(244, 63, 94, 0.3)'
          };
        }));
      }

      // 3. VWAP Line Series
      var vwapData = candles.filter(function(c) { return c.vwap != null; }).map(function(c) {
        return { time: c.time, value: c.vwap };
      });
      if (vwapData.length > 0) {
        var vwapSeries = addSeries('LineSeries', {
          color: '#06b6d4',
          lineWidth: 2,
          title: 'VWAP',
        });
        if (vwapSeries) vwapSeries.setData(vwapData);
      }

      // 4. Chandelier Trailing Stop Line Series
      var slData = candles.filter(function(c) { return c.chandelier_sl != null; }).map(function(c) {
        return { time: c.time, value: c.chandelier_sl };
      });
      if (slData.length > 0) {
        var slSeries = addSeries('LineSeries', {
          color: '#f59e0b',
          lineWidth: 1,
          lineStyle: (LC.LineStyle ? LC.LineStyle.Dotted : 1),
          title: 'Chandelier SL',
        });
        if (slSeries) slSeries.setData(slData);
      }

      // 5. Overlaid Camarilla Equation Price Lines
      if (candleSeries && camarilla && camarilla.h4 > 0) {
        candleSeries.createPriceLine({
          price: camarilla.h4,
          color: '#ec4899',
          lineWidth: 1,
          lineStyle: (LC.LineStyle ? LC.LineStyle.Dashed : 2),
          axisLabelVisible: true,
          title: 'H4 Breakout (₹' + camarilla.h4 + ')',
        });
        candleSeries.createPriceLine({
          price: camarilla.h3,
          color: '#10b981',
          lineWidth: 1,
          lineStyle: (LC.LineStyle ? LC.LineStyle.Dotted : 1),
          axisLabelVisible: true,
          title: 'H3 Target 1 (₹' + camarilla.h3 + ')',
        });
        candleSeries.createPriceLine({
          price: camarilla.l3,
          color: '#06b6d4',
          lineWidth: 1,
          lineStyle: (LC.LineStyle ? LC.LineStyle.Dotted : 1),
          axisLabelVisible: true,
          title: 'L3 Liquidity Floor (₹' + camarilla.l3 + ')',
        });
        candleSeries.createPriceLine({
          price: camarilla.l4,
          color: '#f43f5e',
          lineWidth: 1,
          lineStyle: (LC.LineStyle ? LC.LineStyle.Dashed : 2),
          axisLabelVisible: true,
          title: 'L4 Hard SL (₹' + camarilla.l4 + ')',
        });
      }

      chart.timeScale().fitContent();

      var ro = new ResizeObserver(function(entries) {
        for (var i = 0; i < entries.length; i++) {
          var cr = entries[i].contentRect;
          if (cr.width > 20 && cr.height > 20) {
            chart.applyOptions({
              width: Math.floor(cr.width),
              height: Math.floor(cr.height),
            });
            chart.timeScale().fitContent();
          }
        }
      });
      ro.observe(container);

      window.addEventListener('resize', function() {
        chart.applyOptions({
          width: container.clientWidth || window.innerWidth,
          height: container.clientHeight || window.innerHeight,
        });
      });
    })();
  </script>
</body>
</html>''';
  }

  @override
  Widget build(BuildContext context) {
    final rawSym = widget.symbol.trim().toUpperCase();
    final cleanSym = rawSym.replaceAll('.BO', '').replaceAll('.NS', '');
    final exchange = rawSym.endsWith('.BO') ? 'BSE' : 'NSE';
    final candles = (_candlePayload?['candles'] as List?) ?? [];
    num? lastPrice;
    num priceChange = 0.0;
    if (candles.isNotEmpty) {
      final lastBar = candles.last;
      final firstBar = candles.first;
      lastPrice = lastBar['close'];
      if (lastPrice != null && firstBar['open'] != null) {
        priceChange = (lastPrice - firstBar['open']);
      }
    }
    final isPos = priceChange >= 0;
    final camarilla = _candlePayload?['camarilla'] as Map<String, dynamic>?;

    return Container(
      height: MediaQuery.of(context).size.height * 0.88,
      decoration: const BoxDecoration(
        color: Color(0xFF080B16),
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
        border: Border(
          top: BorderSide(color: Color(0x5906B6D4), width: 1.5),
          left: BorderSide(color: Color(0x15FFFFFF), width: 1),
          right: BorderSide(color: Color(0x15FFFFFF), width: 1),
        ),
      ),
      child: Column(
        children: [
          // Drag Handle
          Center(
            child: Container(
              margin: const EdgeInsets.only(top: 10, bottom: 8),
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.2),
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),

          // Header Bar
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                // Stock Symbol & Live Price
                Row(
                  crossAxisAlignment: CrossAxisAlignment.baseline,
                  textBaseline: TextBaseline.alphabetic,
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1.5),
                      decoration: BoxDecoration(
                        gradient: const LinearGradient(
                          colors: [Color(0xFF06B6D4), Color(0xFF6366F1)],
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                        ),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: const Text(
                        'SV',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 9.5,
                          fontWeight: FontWeight.w900,
                          letterSpacing: 0.5,
                        ),
                      ),
                    ),
                    const SizedBox(width: 6),
                    Text(
                      cleanSym,
                      style: const TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.w900,
                        fontSize: 18,
                      ),
                    ),
                    const SizedBox(width: 6),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1.5),
                      decoration: BoxDecoration(
                        color: exchange == 'BSE' ? const Color(0xFFF59E0B).withOpacity(0.15) : AppTheme.cyan.withOpacity(0.12),
                        borderRadius: BorderRadius.circular(4),
                        border: Border.all(color: exchange == 'BSE' ? const Color(0xFFF59E0B) : AppTheme.cyan, width: 0.8),
                      ),
                      child: Text(
                        exchange,
                        style: TextStyle(
                          color: exchange == 'BSE' ? const Color(0xFFF59E0B) : AppTheme.cyan,
                          fontSize: 8.5,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                    ),
                    if (lastPrice != null) ...[
                      const SizedBox(width: 8),
                      Text(
                        "₹${lastPrice.toStringAsFixed(2)}",
                        style: TextStyle(
                          color: isPos ? AppTheme.primaryEmerald : AppTheme.dangerRose,
                          fontWeight: FontWeight.w800,
                          fontSize: 15,
                        ),
                      ),
                      const SizedBox(width: 4),
                      Text(
                        "(${isPos ? '+' : ''}${priceChange.toStringAsFixed(2)})",
                        style: TextStyle(
                          color: isPos ? AppTheme.primaryEmerald : AppTheme.dangerRose,
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ],
                ),

                // Header Actions (Full Screen & Close)
                Row(
                  children: [
                    IconButton(
                      onPressed: () {
                        Navigator.of(context).pop();
                        Navigator.of(context).push(
                          MaterialPageRoute(
                            builder: (_) => CandleChartScreen(
                              symbol: widget.symbol,
                              initialInterval: _selectedInterval,
                            ),
                          ),
                        );
                      },
                      icon: const Icon(Icons.fullscreen, color: AppTheme.cyan, size: 24),
                      tooltip: "Full Screen & Landscape",
                      padding: const EdgeInsets.only(right: 8),
                      constraints: const BoxConstraints(),
                    ),
                    IconButton(
                      onPressed: () => Navigator.of(context).pop(),
                      icon: const Icon(Icons.close, color: AppTheme.textSecondary, size: 20),
                      padding: EdgeInsets.zero,
                      constraints: const BoxConstraints(),
                    ),
                  ],
                ),
              ],
            ),
          ),

          // Timeframe Selectors Bar
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
            child: Row(
              children: [
                const Text(
                  "Timeframe:",
                  style: TextStyle(color: AppTheme.textMuted, fontSize: 11, fontWeight: FontWeight.bold),
                ),
                const SizedBox(width: 8),
                Wrap(
                  spacing: 6,
                  children: _intervals.map((tf) {
                    final isSelected = _selectedInterval == tf;
                    return InkWell(
                      onTap: () {
                        if (_selectedInterval != tf) {
                          setState(() => _selectedInterval = tf);
                          _loadChartData();
                        }
                      },
                      borderRadius: BorderRadius.circular(8),
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: isSelected ? AppTheme.cyan.withOpacity(0.18) : Colors.white.withOpacity(0.04),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(
                            color: isSelected ? AppTheme.cyan.withOpacity(0.6) : Colors.white.withOpacity(0.08),
                          ),
                        ),
                        child: Text(
                          tf.toUpperCase(),
                          style: TextStyle(
                            color: isSelected ? AppTheme.cyan : AppTheme.textSecondary,
                            fontSize: 10.5,
                            fontWeight: isSelected ? FontWeight.w900 : FontWeight.w600,
                          ),
                        ),
                      ),
                    );
                  }).toList(),
                ),
              ],
            ),
          ),

          // Legend Bar (Camarilla levels, VWAP, Chandelier SL)
          Container(
            margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.03),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: Colors.white.withOpacity(0.06)),
            ),
            child: Wrap(
              spacing: 10,
              runSpacing: 4,
              children: [
                _buildLegendItem("VWAP", const Color(0xFF06B6D4)),
                _buildLegendItem("Chandelier SL", const Color(0xFFF59E0B)),
                if (camarilla != null && (camarilla['h4'] ?? 0) > 0) ...[
                  _buildLegendItem("H4: ₹${camarilla['h4']}", const Color(0xFFEC4899)),
                  _buildLegendItem("H3: ₹${camarilla['h3']}", const Color(0xFF10B981)),
                  _buildLegendItem("L3: ₹${camarilla['l3']}", const Color(0xFF06B6D4)),
                  _buildLegendItem("L4: ₹${camarilla['l4']}", const Color(0xFFF43F5E)),
                ],
              ],
            ),
          ),

          const Divider(color: AppTheme.cardBorder, height: 1),

          // Chart Canvas / Loading / Error Body
          Expanded(
            child: _isLoading
                ? const Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        SizedBox(
                          width: 32,
                          height: 32,
                          child: CircularProgressIndicator(color: AppTheme.cyan, strokeWidth: 2.5),
                        ),
                        SizedBox(height: 14),
                        Text(
                          "Loading Institutional Candles & Pivots...",
                          style: TextStyle(color: AppTheme.textSecondary, fontSize: 12),
                        ),
                      ],
                    ),
                  )
                : _errorMessage != null
                    ? Center(
                        child: Padding(
                          padding: const EdgeInsets.all(24.0),
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              const Icon(Icons.error_outline, color: AppTheme.dangerRose, size: 40),
                              const SizedBox(height: 12),
                              Text(
                                _errorMessage!,
                                textAlign: TextAlign.center,
                                style: const TextStyle(color: AppTheme.dangerRose, fontSize: 13),
                              ),
                              const SizedBox(height: 16),
                              OutlinedButton.icon(
                                onPressed: _loadChartData,
                                icon: const Icon(Icons.refresh, size: 16, color: AppTheme.cyan),
                                label: const Text("Retry", style: TextStyle(color: AppTheme.cyan)),
                                style: OutlinedButton.styleFrom(
                                  side: const BorderSide(color: AppTheme.borderCyan),
                                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                                ),
                              ),
                            ],
                          ),
                        ),
                      )
                    : (_webViewController != null)
                        ? WebViewWidget(
                            controller: _webViewController!,
                            gestureRecognizers: {
                              Factory<OneSequenceGestureRecognizer>(
                                () => EagerGestureRecognizer(),
                              ),
                            },
                          )
                        : const SizedBox.shrink(),
          ),
        ],
      ),
    );
  }

  Widget _buildLegendItem(String label, Color color) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 8,
          height: 8,
          decoration: BoxDecoration(color: color, shape: BoxShape.circle),
        ),
        const SizedBox(width: 4),
        Text(
          label,
          style: const TextStyle(color: AppTheme.textSecondary, fontSize: 10, fontWeight: FontWeight.w700),
        ),
      ],
    );
  }
}
