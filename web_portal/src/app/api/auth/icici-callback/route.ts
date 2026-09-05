import { NextRequest, NextResponse } from "next/server";

function sanitizeToken(token: string): string {
  if (!token) return "";
  const cleaned = token.trim();
  // Valid ICICI session tokens are alphanumeric with underscores, hyphens, and dots
  if (!/^[a-zA-Z0-9_\-\.]{4,128}$/.test(cleaned)) {
    return "";
  }
  return cleaned;
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

    <div class="token-box">
      <div class="token-label">Session Token (apisession)</div>
      <div class="token-val" id="tokenText">${displayToken || "No valid apisession detected in URL"}</div>
    </div>

    ${safeToken ? `
    <button class="btn-copy" id="copyBtn" onclick="copyToken()">
      📋 Copy Session Token
    </button>
    <a href="stokvigil://breeze-callback?apisession=${encodeURIComponent(safeToken)}" class="btn-app" id="appBtn" rel="noopener noreferrer">
      🔒 1-Tap Open in StokVigil App
    </a>
    ` : ""}

    <a href="/${safeToken ? `?apisession=${encodeURIComponent(safeToken)}` : ""}" class="btn-portal" rel="noopener noreferrer">
      🌐 Open in StokVigil Web Portal →
    </a>

    <div class="help-card" id="helpMsg">
      📱 <strong>On Mobile App:</strong> Click <em>Copy Session Token</em> above to unlock 1-Tap App launch or paste into your app.
    </div>
  </div>

  <script>
    let hasCopied = false;

    function enableAppButton() {
      if (hasCopied) return;
      hasCopied = true;
      const appBtn = document.getElementById('appBtn');
      const helpMsg = document.getElementById('helpMsg');
      if (appBtn) {
        appBtn.classList.add('enabled');
        appBtn.innerHTML = '📱 1-Tap Open in StokVigil App →';
      }
      if (helpMsg) {
        helpMsg.innerHTML = '✅ <strong>Session Token Copied!</strong> Tap <em>1-Tap Open in StokVigil App</em> to launch your app with the token saved.';
        helpMsg.style.borderColor = 'rgba(16,185,129,0.3)';
        helpMsg.style.color = '#A7F3D0';
      }
    }

    function copyToken() {
      const token = ${JSON.stringify(safeToken)};
      if (!token) return;
      
      const onSuccess = () => {
        const btn = document.getElementById('copyBtn');
        if (btn) {
          btn.innerHTML = '✅ Copied to Clipboard!';
          btn.style.background = '#10B981';
          setTimeout(() => {
            btn.innerHTML = '📋 Copy Session Token Again';
            btn.style.background = 'linear-gradient(90deg, #00B4D8 0%, #0284C7 35%, #6366F1 70%, #8B5CF6 100%)';
          }, 2500);
        }
        enableAppButton();
      };

      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(token).then(onSuccess).catch(() => fallbackCopy(token, onSuccess));
      } else {
        fallbackCopy(token, onSuccess);
      }
    }

    function fallbackCopy(text, cb) {
      try {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.opacity = '0';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        cb();
      } catch (err) {
        cb();
      }
    }

    document.addEventListener('copy', () => {
      enableAppButton();
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
  "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
  "Content-Security-Policy": "default-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; script-src 'self' 'unsafe-inline'; frame-ancestors 'none';",
};

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const apisession = searchParams.get("apisession") || searchParams.get("api_session") || "";

  return new NextResponse(renderCallbackHtml(apisession), {
    status: 200,
    headers: CALLBACK_SECURITY_HEADERS,
  });
}

export async function POST(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  let apisession = searchParams.get("apisession") || searchParams.get("api_session") || "";

  if (!apisession) {
    try {
      const contentType = request.headers.get("content-type") || "";
      if (contentType.includes("form") || contentType.includes("urlencoded")) {
        const formData = await request.formData();
        apisession = (formData.get("apisession") as string) || (formData.get("api_session") as string) || "";
      } else if (contentType.includes("json")) {
        const json = await request.json();
        apisession = json.apisession || json.api_session || "";
      } else {
        const text = await request.text();
        const bodyParams = new URLSearchParams(text);
        apisession = bodyParams.get("apisession") || bodyParams.get("api_session") || "";
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
