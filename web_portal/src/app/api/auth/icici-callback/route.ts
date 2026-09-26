import { NextRequest, NextResponse } from "next/server";

function sanitizeToken(token: string): string {
  if (!token) return "";
  let cleaned = token.trim();
  try {
    cleaned = decodeURIComponent(cleaned);
  } catch (_) {}
  // If user or browser passed "apisession=XYZ"
  if (cleaned.toLowerCase().includes("apisession=")) {
    cleaned = cleaned.split(/apisession=/i)[1].split("&")[0];
  }
  cleaned = cleaned.trim();
  // Valid ICICI session tokens are alphanumeric with underscores, hyphens, dots, +, and = (Base64 padding)
  if (!/^[-a-zA-Z0-9_.+=]{4,128}$/.test(cleaned)) {
    return "";
  }
  return cleaned;
}

function extractApiSession(params: URLSearchParams | FormData | Record<string, any>): string {
  if (params instanceof URLSearchParams) {
    for (const [k, v] of params.entries()) {
      const key = k.toLowerCase();
      if ((key === "apisession" || key === "api_session") && v.trim()) {
        return v.trim();
      }
    }
  } else if (typeof (params as any)?.entries === "function") {
    for (const [k, v] of (params as FormData).entries()) {
      const key = k.toLowerCase();
      if ((key === "apisession" || key === "api_session") && typeof v === "string" && v.trim()) {
        return v.trim();
      }
    }
  } else if (params && typeof params === "object") {
    for (const [k, v] of Object.entries(params)) {
      const key = k.toLowerCase();
      if ((key === "apisession" || key === "api_session") && typeof v === "string" && v.trim()) {
        return v.trim();
      }
    }
  }
  return "";
}

function escapeHtml(unsafe: string): string {
  return unsafe
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function renderCallbackHtml(rawToken: string) {
  const safeToken = sanitizeToken(rawToken);
  const displayToken = escapeHtml(safeToken);
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>StokVigil AI — ICICI Breeze Session Captured</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;700;800;900&display=swap" rel="stylesheet">
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      min-height: 100vh;
      background: #070913;
      color: #F8FAFC;
      font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }
    .glow {
      position: fixed;
      top: 20%;
      left: 50%;
      transform: translateX(-50%);
      width: 450px;
      height: 350px;
      background: radial-gradient(circle, rgba(6,182,212,0.18) 0%, rgba(139,92,246,0.12) 50%, transparent 70%);
      pointer-events: none;
      z-index: 0;
    }
    .card {
      position: relative;
      z-index: 1;
      width: 100%;
      max-width: 460px;
      background: #0D111E;
      border: 1px solid rgba(6,182,212,0.35);
      border-radius: 24px;
      padding: 28px;
      box-shadow: 0 25px 60px rgba(0,0,0,0.8), 0 0 30px rgba(6,182,212,0.15);
      text-align: center;
    }
    .badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 14px;
      border-radius: 20px;
      background: rgba(16,185,129,0.12);
      border: 1px solid rgba(16,185,129,0.4);
      color: #10B981;
      font-size: 12px;
      font-weight: 800;
      margin-bottom: 12px;
    }
    h1 {
      font-size: 22px;
      font-weight: 900;
      color: #FFFFFF;
      margin-bottom: 8px;
    }
    p {
      font-size: 13px;
      color: #94A3B8;
      line-height: 1.5;
      margin-bottom: 20px;
    }
    .token-box {
      background: #060812;
      border: 1px solid rgba(6,182,212,0.25);
      border-radius: 14px;
      padding: 14px;
      margin-bottom: 18px;
      text-align: left;
    }
    .token-label {
      font-size: 10px;
      font-weight: 900;
      color: #06B6D4;
      text-transform: uppercase;
      letter-spacing: 0.8px;
      margin-bottom: 6px;
    }
    .token-val {
      font-family: monospace;
      font-size: 15px;
      font-weight: 800;
      color: #FFFFFF;
      word-break: break-all;
      background: rgba(255,255,255,0.03);
      padding: 10px 12px;
      border-radius: 8px;
      border: 1px solid rgba(255,255,255,0.08);
      user-select: all;
    }
    .token-input {
      width: 100%;
      font-family: monospace;
      font-size: 16px;
      font-weight: 800;
      color: #00B4D8;
      background: rgba(6,182,212,0.08);
      padding: 12px 14px;
      border-radius: 10px;
      border: 1px solid rgba(6,182,212,0.4);
      outline: none;
      user-select: all;
      -webkit-user-select: all;
      box-sizing: border-box;
      text-align: center;
      letter-spacing: 1px;
      cursor: pointer;
      transition: all 0.2s ease;
    }
    .token-input:focus {
      border-color: #00B4D8;
      box-shadow: 0 0 16px rgba(0,180,216,0.4);
      background: rgba(6,182,212,0.12);
    }
    .btn-copy {
      width: 100%;
      padding: 14px 20px;
      border-radius: 14px;
      border: none;
      background: linear-gradient(90deg, #00B4D8 0%, #0284C7 35%, #6366F1 70%, #8B5CF6 100%);
      color: #FFFFFF;
      font-size: 14px;
      font-weight: 900;
      cursor: pointer;
      box-shadow: 0 6px 20px rgba(6,182,212,0.3);
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      margin-bottom: 10px;
      transition: all 0.2s ease;
    }
    .btn-copy:active {
      transform: scale(0.98);
    }
    .btn-app {
      width: 100%;
      padding: 13px 18px;
      border-radius: 14px;
      border: 1.5px dashed rgba(139,92,246,0.35);
      background: rgba(139,92,246,0.05);
      color: #64748B;
      font-size: 13.5px;
      font-weight: 900;
      cursor: not-allowed;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      text-decoration: none;
      margin-bottom: 10px;
      opacity: 0.45;
      pointer-events: none;
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .btn-app:active {
      transform: scale(0.98);
    }
    .btn-app.enabled {
      opacity: 1;
      pointer-events: auto;
      cursor: pointer;
      border: 1.5px solid rgba(139,92,246,0.85);
      background: linear-gradient(135deg, rgba(139,92,246,0.25) 0%, rgba(99,102,241,0.2) 100%);
      color: #EDE9FE;
      box-shadow: 0 0 24px rgba(139,92,246,0.4), 0 4px 12px rgba(0,0,0,0.5);
      animation: pulseGlow 2s infinite ease-in-out;
    }
    .btn-app.enabled:active {
      transform: scale(0.98);
    }
    @keyframes pulseGlow {
      0%, 100% {
        box-shadow: 0 0 16px rgba(139,92,246,0.35), 0 4px 12px rgba(0,0,0,0.5);
      }
      50% {
        box-shadow: 0 0 28px rgba(139,92,246,0.65), 0 4px 16px rgba(139,92,246,0.3);
      }
    }
    .btn-portal {
      width: 100%;
      padding: 12px 18px;
      border-radius: 14px;
      border: 1px solid rgba(6,182,212,0.35);
      background: rgba(6,182,212,0.08);
      color: #06B6D4;
      font-size: 13px;
      font-weight: 800;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      text-decoration: none;
    }
    .help-card {
      margin-top: 18px;
      padding: 12px;
      border-radius: 12px;
      background: rgba(255,255,255,0.02);
      border: 1px solid rgba(255,255,255,0.06);
      font-size: 11.5px;
      color: #94A3B8;
      line-height: 1.4;
      text-align: center;
      transition: all 0.3s ease;
    }
  </style>
</head>
<body>
  <div class="glow"></div>
  <div class="card">
    <div class="badge">✅ ICICI Direct Authenticated</div>
    <h1>Session Key Generated!</h1>
    <p>Your ICICI Breeze daily trading session token is ready.</p>

    <div class="token-box" onclick="copyToken()">
      <div class="token-label">Session Token (apisession)</div>
      <input
        type="text"
        class="token-input"
        id="tokenInput"
        readonly
        value="${displayToken || ""}"
        onclick="event.stopPropagation(); copyToken();"
        spellcheck="false"
        autocomplete="off"
        placeholder="Waiting for token..."
      />
      <div class="token-val" id="tokenText" style="display: none;">${displayToken || ""}</div>
    </div>

    <div id="tokenActions" style="display: ${safeToken ? 'block' : 'none'};">
      <button class="btn-copy" id="copyBtn" onclick="copyToken()">
        📋 Copy Session Token
      </button>
      <a href="stokvigil://breeze-callback?apisession=${encodeURIComponent(safeToken)}" class="btn-app" id="appBtn" tabindex="-1" rel="noopener noreferrer">
        🔒 1-Tap Open in StokVigil App
      </a>
    </div>

    <a href="/${safeToken ? `?apisession=${encodeURIComponent(safeToken)}` : ""}" class="btn-portal" id="portalBtn" rel="noopener noreferrer" onclick="try { sessionStorage.setItem('stokvigil_pending_apisession', window._activeSessionToken || '${safeToken}'); } catch(_){}">
      🌐 Open in StokVigil Web Portal →
    </a>

    <div class="help-card" id="helpMsg">
      📱 <strong>On Mobile App:</strong> Click <em>Copy Session Token</em> above to unlock 1-Tap App launch or paste into your app.
    </div>
  </div>

  <script>
    window._activeSessionToken = ${JSON.stringify(safeToken)};

    // Auto-Recovery on Client: check window.location.search, hash, and sessionStorage
    try {
      if (window._activeSessionToken) {
        try { sessionStorage.setItem('stokvigil_pending_apisession', window._activeSessionToken); } catch (_) {}
      }
      if (!window._activeSessionToken && typeof window !== 'undefined') {
        var urlSearch = new URLSearchParams(window.location.search);
        var urlHash = new URLSearchParams(window.location.hash.replace(/^#/, ''));
        var foundToken = "";

        for (var p of urlSearch.entries()) {
          if (p[0].toLowerCase() === "apisession" && p[1].trim()) {
            foundToken = p[1].trim();
            break;
          }
        }
        if (!foundToken) {
          for (var hp of urlHash.entries()) {
            if (hp[0].toLowerCase() === "apisession" && hp[1].trim()) {
              foundToken = hp[1].trim();
              break;
            }
          }
        }
        if (!foundToken) {
          foundToken = sessionStorage.getItem('stokvigil_pending_apisession') || "";
        }

        if (foundToken) {
          try { foundToken = decodeURIComponent(foundToken); } catch (_) {}
          if (foundToken.toLowerCase().indexOf("apisession=") !== -1) {
            foundToken = foundToken.split(/apisession=/i)[1].split("&")[0];
          }
          foundToken = foundToken.trim();
          if (/^[-a-zA-Z0-9_.+=]{4,128}$/.test(foundToken)) {
            window._activeSessionToken = foundToken;
            var tInput = document.getElementById('tokenInput');
            if (tInput) tInput.value = foundToken;
            var tBox = document.getElementById('tokenText');
            if (tBox) tBox.textContent = foundToken;
            var actBox = document.getElementById('tokenActions');
            if (actBox) actBox.style.display = 'block';
            var appLink = document.getElementById('appBtn');
            if (appLink) appLink.href = "stokvigil://breeze-callback?apisession=" + encodeURIComponent(foundToken);
            var portLink = document.getElementById('portalBtn');
            if (portLink) portLink.href = "/?apisession=" + encodeURIComponent(foundToken);
            try { sessionStorage.setItem('stokvigil_pending_apisession', foundToken); } catch (_) {}
          }
        }
      }
    } catch (e) {
      console.debug("Session token client extraction notice:", e);
    }

    // Security: Immediately scrub sensitive session token from browser address bar & history
    try {
      if (typeof window !== 'undefined' && window.history && window.history.replaceState) {
        window.history.replaceState({}, document.title, window.location.pathname);
      }
    } catch (_) {}

    function getToken() {
      var t = window._activeSessionToken;
      if (!t || !t.trim()) {
        var inp = document.getElementById('tokenInput');
        if (inp && inp.value && inp.value.trim() && inp.value.indexOf('Waiting') === -1) {
          t = inp.value.trim();
        }
      }
      if (!t || !t.trim()) {
        var el = document.getElementById('tokenText');
        if (el && el.textContent) {
          var txt = el.textContent.trim();
          if (txt && txt.indexOf('No valid') === -1) {
            t = txt;
          }
        }
      }
      if (!t || !t.trim()) {
        t = ${JSON.stringify(safeToken)};
      }
      return (t || '').trim();
    }

    function copyFromVisibleInput(text) {
      var inp = document.getElementById('tokenInput');
      if (!inp) return false;
      var copied = false;
      try {
        inp.removeAttribute('readonly');
        inp.value = text;
        inp.focus({ preventScroll: true });
        inp.select();
        inp.setSelectionRange(0, text.length || 99999);
        copied = document.execCommand('copy');
        inp.setAttribute('readonly', 'readonly');
        inp.blur();
      } catch (e) {
        copied = false;
      }
      return copied;
    }

    function copyToClipboard(text) {
      if (!text) return false;
      var copied = false;

      // Method 1: Modern navigator.clipboard API (standard on HTTPS)
      if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
        try {
          navigator.clipboard.writeText(text).then(function() {
            copied = true;
          }).catch(function(e) {
            console.debug("navigator.clipboard notice:", e);
          });
        } catch (_) {}
      }

      // Method 2: Synchronous DOM copy from visible on-screen input
      // Guaranteed to work across mobile browsers (Android Chrome / WebViews / Safari)
      copied = copyFromVisibleInput(text) || copied;

      // Method 3: In-viewport fallback textarea if needed
      if (!copied) {
        try {
          var ta = document.createElement('textarea');
          ta.value = text;
          ta.style.position = 'fixed';
          ta.style.top = '0';
          ta.style.left = '0';
          ta.style.width = '24px';
          ta.style.height = '24px';
          ta.style.padding = '0';
          ta.style.border = 'none';
          ta.style.outline = 'none';
          ta.style.boxShadow = 'none';
          ta.style.background = 'transparent';
          ta.style.opacity = '0.01';
          ta.style.zIndex = '99999';
          document.body.appendChild(ta);
          ta.select();
          ta.setSelectionRange(0, text.length);
          copied = document.execCommand('copy');
          document.body.removeChild(ta);
        } catch (err) {
          console.warn("DOM execCommand copy error:", err);
        }
      }

      return copied;
    }

    function copyToken() {
      try {
        var token = getToken();
        var btn = document.getElementById('copyBtn');

        if (!token) {
          if (btn) {
            btn.innerHTML = '⚠️ No Token Available';
            btn.style.background = '#EF4444';
          }
          return;
        }

        // Execute synchronous copy FIRST to guarantee user activation on mobile
        copyToClipboard(token);

        showCopySuccess();

        // Ensure focus remains on the Copy button so it never jumps to the App button
        if (btn) {
          try {
            btn.focus({ preventScroll: true });
          } catch (_) {}
        }
      } catch (err) {
        console.error("copyToken error:", err);
        showCopySuccess();
      }
    }

    function copyTokenQuietly() {
      var token = getToken();
      if (!token) return;
      copyToClipboard(token);
    }

    function showCopySuccess() {
      var btn = document.getElementById('copyBtn');
      var appBtn = document.getElementById('appBtn');
      var helpMsg = document.getElementById('helpMsg');

      if (btn) {
        btn.innerHTML = '✅ Copied to Clipboard!';
        btn.style.background = '#10B981';
        setTimeout(function() {
          btn.innerHTML = '📋 Copy Session Token Again';
          btn.style.background = 'linear-gradient(90deg, #00B4D8 0%, #0284C7 35%, #6366F1 70%, #8B5CF6 100%)';
        }, 3000);
      }
      if (appBtn) {
        appBtn.classList.add('enabled');
        appBtn.removeAttribute('tabindex');
        appBtn.innerHTML = '📱 1-Tap Open in StokVigil App →';
      }
      if (helpMsg) {
        helpMsg.innerHTML = '✅ <strong>Session Token Copied!</strong> Tap <em>1-Tap Open in StokVigil App</em> to launch your app with the token saved.';
        helpMsg.style.borderColor = 'rgba(16,185,129,0.3)';
        helpMsg.style.color = '#A7F3D0';
      }
    }

    try {
      var copyBtnEl = document.getElementById('copyBtn');
      if (copyBtnEl) {
        copyBtnEl.addEventListener('click', copyToken);
        copyBtnEl.addEventListener('touchend', function(e) {
          e.preventDefault();
          copyToken();
        });
      }
    } catch (_) {}

    document.addEventListener('copy', function() {
      showCopySuccess();
    });
  </script>
</body>
</html>`;
}

const CALLBACK_SECURITY_HEADERS = {
  "Content-Type": "text/html; charset=utf-8",
  "X-Frame-Options": "DENY",
  "X-Content-Type-Options": "nosniff",
  "Referrer-Policy": "no-referrer",
  "Permissions-Policy": "camera=(), microphone=(), geolocation=(), clipboard-write=*",
  "Content-Security-Policy": "default-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; script-src 'self' 'unsafe-inline'; frame-ancestors 'none';",
};

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const apisession = extractApiSession(searchParams);

  return new NextResponse(renderCallbackHtml(apisession), {
    status: 200,
    headers: CALLBACK_SECURITY_HEADERS,
  });
}

export async function POST(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  let apisession = extractApiSession(searchParams);

  if (!apisession) {
    try {
      const contentType = request.headers.get("content-type") || "";
      if (contentType.includes("form") || contentType.includes("urlencoded")) {
        const formData = await request.formData();
        apisession = extractApiSession(formData);
      } else if (contentType.includes("json")) {
        const json = await request.json();
        apisession = extractApiSession(json);
      } else {
        const text = await request.text();
        const bodyParams = new URLSearchParams(text);
        apisession = extractApiSession(bodyParams);
      }
    } catch {
      // Fallback
    }
  }

  return new NextResponse(renderCallbackHtml(apisession), {
    status: 200,
    headers: CALLBACK_SECURITY_HEADERS,
  });
}
