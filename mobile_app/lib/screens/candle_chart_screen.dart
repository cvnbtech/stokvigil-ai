import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:webview_flutter/webview_flutter.dart';
import '../config/theme.dart';
import '../services/api_service.dart';

/// Dedicated Fullscreen TradingView Lightweight Candlestick & Camarilla Chart Screen.
/// Automatically adapts to device screen resolution, supports landscape orientation,
/// dynamic touch crosshair OHLC HUD, and interactive indicator toggles.
class CandleChartScreen extends StatefulWidget {
  final String symbol;
  final String initialInterval;

  const CandleChartScreen({
    super.key,
    required this.symbol,
    this.initialInterval = "5m",
  });

  @override
  State<CandleChartScreen> createState() => _CandleChartScreenState();
}

class _CandleChartScreenState extends State<CandleChartScreen> {
  late String _selectedInterval;
  bool _isLoading = true;
  String? _errorMessage;
  Map<String, dynamic>? _candlePayload;
  WebViewController? _webViewController;
  String? _bundledJs;
  bool _isLandscape = false;

  // Real-time touch crosshair OHLC values
  Map<String, dynamic>? _crosshairData;

  // Indicator Visibility Toggles
  bool _showCamarilla = true;
  bool _showVwap = true;
  bool _showChandelier = true;
  bool _showVolume = true;

  static const List<String> _intervals = ["1m", "5m", "15m", "1h", "1d"];

  @override
  void initState() {
    super.initState();
    _selectedInterval = widget.initialInterval;
    _initAndLoad();
  }

  @override
  void dispose() {
    // Reset orientation to portrait on exit
    SystemChrome.setPreferredOrientations([
      DeviceOrientation.portraitUp,
      DeviceOrientation.portraitDown,
    ]);
    super.dispose();
  }

  Future<void> _initAndLoad() async {
    // Pre-load local bundled JS asset first to eliminate CDN race condition
    await _loadJsBundle();
    _initWebView();
    await _loadChartData();
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

  void _initWebView() {
    _webViewController = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setBackgroundColor(const Color(0xFF080B16))
      ..addJavaScriptChannel(
        'ChartChannel',
        onMessageReceived: (JavaScriptMessage message) {
          try {
            final data = jsonDecode(message.message) as Map<String, dynamic>;
            if (mounted) {
              setState(() {
                _crosshairData = data;
              });
            }
          } catch (_) {}
        },
      )
      ..setNavigationDelegate(
        NavigationDelegate(
          onWebResourceError: (error) {
            debugPrint("WebView error: ${error.description}");
          },
        ),
      );
  }

  Future<void> _loadChartData() async {
    if (!mounted) return;
    setState(() {
      _isLoading = true;
      _errorMessage = null;
      _crosshairData = null;
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

    // Make sure bundled JS is loaded before building HTML
    if (_bundledJs == null) {
      await _loadJsBundle();
    }

    final htmlContent = _buildHtmlString(data);
    _webViewController?.loadHtmlString(
      htmlContent,
      baseUrl: "https://appassets.androidplatform.net",
    );
  }

  void _toggleOrientation() {
    setState(() {
      _isLandscape = !_isLandscape;
    });

    if (_isLandscape) {
      SystemChrome.setPreferredOrientations([
        DeviceOrientation.landscapeLeft,
        DeviceOrientation.landscapeRight,
      ]);
    } else {
      SystemChrome.setPreferredOrientations([
        DeviceOrientation.portraitUp,
        DeviceOrientation.portraitDown,
      ]);
    }
  }

  void _updateIndicatorToggles() {
    final jsCode = '''
      if (typeof window.setIndicatorVisibility === 'function') {
        window.setIndicatorVisibility({
          camarilla: $_showCamarilla,
          vwap: $_showVwap,
          chandelier: $_showChandelier,
          volume: $_showVolume
        });
      }
    ''';
    _webViewController?.runJavaScript(jsCode);
  }

  String _buildHtmlString(Map<String, dynamic> data) {
    final candles = data['candles'] ?? [];
    final camarilla = data['camarilla'] ?? {};
    final candlesJson = jsonEncode(candles);
    final camarillaJson = jsonEncode(camarilla);

    final scriptContent = (_bundledJs != null && _bundledJs!.isNotEmpty)
        ? '<script>$_bundledJs</script>'
        : '<script src="https://unpkg.com/lightweight-charts@5.2.1/dist/lightweight-charts.standalone.production.js"></script>';

    return '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; user-select: none; -webkit-user-select: none; -webkit-tap-highlight-color: transparent; }
    html, body {
      width: 100%;
      height: 100%;
      background-color: #080B16;
      color: #94a3b8;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      overflow: hidden;
    }
    #chart-container {
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      width: 100%;
      height: 100%;
    }
  </style>
  $scriptContent
  <script>
    if (typeof window.LightweightCharts === 'undefined') {
      var s = document.createElement('script');
      s.src = 'https://unpkg.com/lightweight-charts@5.2.1/dist/lightweight-charts.standalone.production.js';
      document.head.appendChild(s);
    }
  </script>
</head>
<body>
  <div id="chart-container"></div>
  <script>
    (function initChart() {
      if (typeof window.LightweightCharts === 'undefined') {
        setTimeout(initChart, 30);
        return;
      }

      var LC = window.LightweightCharts;
      var container = document.getElementById('chart-container');

      function getContainerSize() {
        var w = container.clientWidth || window.innerWidth || document.documentElement.clientWidth;
        var h = container.clientHeight || window.innerHeight || document.documentElement.clientHeight;
        return { width: Math.max(w, 200), height: Math.max(h, 200) };
      }

      var size = getContainerSize();

      var chart = LC.createChart(container, {
        layout: {
          background: { color: '#080B16' },
          textColor: '#94a3b8',
          fontSize: (window.innerWidth < 400 ? 10 : 11),
        },
        grid: {
          vertLines: { color: 'rgba(255, 255, 255, 0.04)' },
          horzLines: { color: 'rgba(255, 255, 255, 0.04)' },
        },
        timeScale: {
          borderColor: 'rgba(255, 255, 255, 0.1)',
          timeVisible: true,
          secondsVisible: false,
          fixLeftEdge: true,
          fixRightEdge: true,
        },
        crosshair: {
          vertLine: { color: '#06b6d4', width: 1, style: (LC.LineStyle ? LC.LineStyle.Dashed : 2) },
          horzLine: { color: '#06b6d4', width: 1, style: (LC.LineStyle ? LC.LineStyle.Dashed : 2) },
        },
        rightPriceScale: {
          borderColor: 'rgba(255, 255, 255, 0.1)',
          scaleMargins: { top: 0.1, bottom: 0.15 },
          alignLabels: true,
        },
        width: size.width,
        height: size.height,
      });

      var candles = $candlesJson;
      var camarilla = $camarillaJson;

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
      var vwapSeries = null;
      var vwapData = candles.filter(function(c) { return c.vwap != null; }).map(function(c) {
        return { time: c.time, value: c.vwap };
      });
      if (vwapData.length > 0) {
        vwapSeries = addSeries('LineSeries', {
          color: '#06b6d4',
          lineWidth: 2,
          title: 'VWAP',
        });
        if (vwapSeries) vwapSeries.setData(vwapData);
      }

      // 4. Chandelier Trailing Stop Line Series
      var slSeries = null;
      var slData = candles.filter(function(c) { return c.chandelier_sl != null; }).map(function(c) {
        return { time: c.time, value: c.chandelier_sl };
      });
      if (slData.length > 0) {
        slSeries = addSeries('LineSeries', {
          color: '#f59e0b',
          lineWidth: 1.5,
          lineStyle: (LC.LineStyle ? LC.LineStyle.Dotted : 1),
          title: 'Chandelier SL',
        });
        if (slSeries) slSeries.setData(slData);
      }

      // 5. Camarilla Price Lines
      var camarillaLines = [];
      function setupCamarillaLines() {
        if (!candleSeries || !camarilla) return;
        if (camarilla.h4 > 0) {
          camarillaLines.push(candleSeries.createPriceLine({
            price: camarilla.h4,
            color: '#ec4899',
            lineWidth: 1,
            lineStyle: (LC.LineStyle ? LC.LineStyle.Dashed : 2),
            axisLabelVisible: true,
            title: 'H4 Breakout (₹' + camarilla.h4 + ')',
          }));
        }
        if (camarilla.h3 > 0) {
          camarillaLines.push(candleSeries.createPriceLine({
            price: camarilla.h3,
            color: '#10b981',
            lineWidth: 1,
            lineStyle: (LC.LineStyle ? LC.LineStyle.Dotted : 1),
            axisLabelVisible: true,
            title: 'H3 Target 1 (₹' + camarilla.h3 + ')',
          }));
        }
        if (camarilla.l3 > 0) {
          camarillaLines.push(candleSeries.createPriceLine({
            price: camarilla.l3,
            color: '#06b6d4',
            lineWidth: 1,
            lineStyle: (LC.LineStyle ? LC.LineStyle.Dotted : 1),
            axisLabelVisible: true,
            title: 'L3 Liquidity (₹' + camarilla.l3 + ')',
          }));
        }
        if (camarilla.l4 > 0) {
          camarillaLines.push(candleSeries.createPriceLine({
            price: camarilla.l4,
            color: '#f43f5e',
            lineWidth: 1,
            lineStyle: (LC.LineStyle ? LC.LineStyle.Dashed : 2),
            axisLabelVisible: true,
            title: 'L4 Hard SL (₹' + camarilla.l4 + ')',
          }));
        }
      }
      setupCamarillaLines();

      // Subscribe to Crosshair Movement for Live HUD
      chart.subscribeCrosshairMove(function(param) {
        if (!window.ChartChannel) return;
        if (!param || !param.time || !param.seriesData) {
          window.ChartChannel.postMessage(JSON.stringify({ isHover: false }));
          return;
        }
        var cData = param.seriesData.get(candleSeries);
        if (cData) {
          window.ChartChannel.postMessage(JSON.stringify({
            isHover: true,
            time: param.time,
            open: cData.open,
            high: cData.high,
            low: cData.low,
            close: cData.close,
            volume: (volumeSeries ? (param.seriesData.get(volumeSeries) || {}).value : null),
            vwap: (vwapSeries ? (param.seriesData.get(vwapSeries) || {}).value : null),
          }));
        }
      });

      // Indicator Visibility API
      window.setIndicatorVisibility = function(options) {
        if (volumeSeries) {
          volumeSeries.applyOptions({ visible: !!options.volume });
        }
        if (vwapSeries) {
          vwapSeries.applyOptions({ visible: !!options.vwap });
        }
        if (slSeries) {
          slSeries.applyOptions({ visible: !!options.chandelier });
        }
        // Camarilla lines
        camarillaLines.forEach(function(line) {
          if (candleSeries && line) {
            candleSeries.removePriceLine(line);
          }
        });
        camarillaLines = [];
        if (options.camarilla) {
          setupCamarillaLines();
        }
      };

      // Fit content neatly
      chart.timeScale().fitContent();

      // Dynamic Auto-Resolution Resize Observer
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
        var s = getContainerSize();
        chart.applyOptions({ width: s.width, height: s.height });
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

    // Determine values to show in HUD (Crosshair or Latest Bar)
    final hudOpen = _crosshairData?['open'] ?? (candles.isNotEmpty ? candles.last['open'] : null);
    final hudHigh = _crosshairData?['high'] ?? (candles.isNotEmpty ? candles.last['high'] : null);
    final hudLow = _crosshairData?['low'] ?? (candles.isNotEmpty ? candles.last['low'] : null);
    final hudClose = _crosshairData?['close'] ?? lastPrice;
    final hudVol = _crosshairData?['volume'] ?? (candles.isNotEmpty ? candles.last['volume'] : null);

    return Scaffold(
      backgroundColor: const Color(0xFF080B16),
      body: SafeArea(
        child: Column(
          children: [
            // Top Bar: Symbol, Live Price, Controls, Landscape Rotate
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: const BoxDecoration(
                color: Color(0xFF080B16),
                border: Border(bottom: BorderSide(color: Color(0x15FFFFFF), width: 1)),
              ),
              child: Row(
                children: [
                  // Back Button
                  IconButton(
                    icon: const Icon(Icons.arrow_back, color: Colors.white, size: 20),
                    onPressed: () => Navigator.of(context).pop(),
                    padding: EdgeInsets.zero,
                    constraints: const BoxConstraints(),
                  ),
                  const SizedBox(width: 8),

                  // Symbol & Change
                  Expanded(
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.baseline,
                      textBaseline: TextBaseline.alphabetic,
                      children: [
                        Text(
                          cleanSym,
                          style: const TextStyle(
                            color: Colors.white,
                            fontWeight: FontWeight.w900,
                            fontSize: 16,
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
                          const SizedBox(width: 6),
                          Text(
                            "₹${lastPrice.toStringAsFixed(2)}",
                            style: TextStyle(
                              color: isPos ? AppTheme.primaryEmerald : AppTheme.dangerRose,
                              fontWeight: FontWeight.w800,
                              fontSize: 14,
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
                  ),

                  // Refresh Button
                  IconButton(
                    icon: const Icon(Icons.refresh, color: AppTheme.cyan, size: 18),
                    onPressed: _loadChartData,
                    tooltip: "Reload Candles",
                    padding: const EdgeInsets.symmetric(horizontal: 6),
                    constraints: const BoxConstraints(),
                  ),

                  // Rotate / Landscape Button
                  IconButton(
                    icon: Icon(
                      _isLandscape ? Icons.stay_current_portrait : Icons.screen_rotation,
                      color: AppTheme.cyan,
                      size: 19,
                    ),
                    onPressed: _toggleOrientation,
                    tooltip: _isLandscape ? "Portrait View" : "Landscape View",
                    padding: const EdgeInsets.symmetric(horizontal: 6),
                    constraints: const BoxConstraints(),
                  ),
                ],
              ),
            ),

            // Live Crosshair OHLCV HUD Bar
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
              color: const Color(0xFF0D1424),
              child: SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: [
                    if (_crosshairData?['isHover'] == true) ...[
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1.5),
                        margin: const EdgeInsets.only(right: 8),
                        decoration: BoxDecoration(
                          color: AppTheme.cyan.withOpacity(0.2),
                          borderRadius: BorderRadius.circular(4),
                          border: Border.all(color: AppTheme.cyan.withOpacity(0.4)),
                        ),
                        child: const Text(
                          "TOUCH HUD",
                          style: TextStyle(color: AppTheme.cyan, fontSize: 9, fontWeight: FontWeight.w900),
                        ),
                      ),
                    ],
                    _buildHudItem("O", hudOpen),
                    _buildHudItem("H", hudHigh),
                    _buildHudItem("L", hudLow),
                    _buildHudItem("C", hudClose),
                    if (hudVol != null) ...[
                      const SizedBox(width: 8),
                      Text(
                        "Vol: ${_formatVolume(hudVol)}",
                        style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 10.5, fontWeight: FontWeight.w600),
                      ),
                    ],
                  ],
                ),
              ),
            ),

            // Timeframe & Indicator Toggles Bar (Compact)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
              decoration: const BoxDecoration(
                color: Color(0xFF080B16),
                border: Border(bottom: BorderSide(color: Color(0x10FFFFFF), width: 1)),
              ),
              child: SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: [
                    // Timeframe Selector Pills
                    ..._intervals.map((tf) {
                      final isSelected = _selectedInterval == tf;
                      return GestureDetector(
                        onTap: () {
                          if (_selectedInterval != tf) {
                            setState(() => _selectedInterval = tf);
                            _loadChartData();
                          }
                        },
                        child: Container(
                          margin: const EdgeInsets.only(right: 6),
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3.5),
                          decoration: BoxDecoration(
                            color: isSelected ? AppTheme.cyan.withOpacity(0.2) : Colors.white.withOpacity(0.04),
                            borderRadius: BorderRadius.circular(6),
                            border: Border.all(
                              color: isSelected ? AppTheme.cyan : Colors.white.withOpacity(0.08),
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
                    }),

                    const SizedBox(width: 10),
                    Container(height: 14, width: 1, color: Colors.white24),
                    const SizedBox(width: 10),

                    // Indicator Toggles
                    _buildIndicatorChip("Camarilla", _showCamarilla, const Color(0xFFEC4899), () {
                      setState(() => _showCamarilla = !_showCamarilla);
                      _updateIndicatorToggles();
                    }),
                    _buildIndicatorChip("VWAP", _showVwap, const Color(0xFF06B6D4), () {
                      setState(() => _showVwap = !_showVwap);
                      _updateIndicatorToggles();
                    }),
                    _buildIndicatorChip("Chandelier SL", _showChandelier, const Color(0xFFF59E0B), () {
                      setState(() => _showChandelier = !_showChandelier);
                      _updateIndicatorToggles();
                    }),
                    _buildIndicatorChip("Volume", _showVolume, const Color(0xFF10B981), () {
                      setState(() => _showVolume = !_showVolume);
                      _updateIndicatorToggles();
                    }),
                  ],
                ),
              ),
            ),

            // Dynamic Chart Canvas Area (Fills remaining 100% resolution)
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
      ),
    );
  }

  Widget _buildHudItem(String label, dynamic val) {
    final str = (val is num) ? "₹${val.toStringAsFixed(2)}" : "-";
    return Padding(
      padding: const EdgeInsets.only(right: 10),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text("$label: ", style: const TextStyle(color: Color(0xFF64748B), fontSize: 10.5, fontWeight: FontWeight.bold)),
          Text(str, style: const TextStyle(color: Color(0xFFE2E8F0), fontSize: 10.5, fontWeight: FontWeight.w800)),
        ],
      ),
    );
  }

  Widget _buildIndicatorChip(String label, bool isEnabled, Color accentColor, VoidCallback onTap) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        margin: const EdgeInsets.only(right: 6),
        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
        decoration: BoxDecoration(
          color: isEnabled ? accentColor.withOpacity(0.18) : Colors.white.withOpacity(0.02),
          borderRadius: BorderRadius.circular(6),
          border: Border.all(
            color: isEnabled ? accentColor : Colors.white.withOpacity(0.08),
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 6,
              height: 6,
              decoration: BoxDecoration(
                color: isEnabled ? accentColor : Colors.grey,
                shape: BoxShape.circle,
              ),
            ),
            const SizedBox(width: 4),
            Text(
              label,
              style: TextStyle(
                color: isEnabled ? Colors.white : AppTheme.textMuted,
                fontSize: 10,
                fontWeight: isEnabled ? FontWeight.w800 : FontWeight.normal,
              ),
            ),
          ],
        ),
      ),
    );
  }

  String _formatVolume(dynamic vol) {
    if (vol is! num) return "-";
    if (vol >= 10000000) return "${(vol / 10000000).toStringAsFixed(2)}Cr";
    if (vol >= 100000) return "${(vol / 100000).toStringAsFixed(2)}L";
    if (vol >= 1000) return "${(vol / 1000).toStringAsFixed(1)}K";
    return vol.toString();
  }
}
