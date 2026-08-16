"use client";

import React, { useEffect, useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";

function CallbackContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [token, setToken] = useState<string>("");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const apisession = searchParams.get("apisession") || "";
    if (apisession) {
      setToken(apisession);
    }
  }, [searchParams]);

  const handleCopy = () => {
    if (!token) return;
    navigator.clipboard.writeText(token);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#070913",
        color: "#F8FAFC",
        fontFamily: "'Plus Jakarta Sans', system-ui, -apple-system, sans-serif",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 20,
      }}
    >
      {/* Glow Effect */}
      <div
        style={{
          position: "fixed",
          top: "20%",
          left: "50%",
          transform: "translateX(-50%)",
          width: 450,
          height: 350,
          background: "radial-gradient(circle, rgba(6,182,212,0.15) 0%, rgba(139,92,246,0.1) 50%, transparent 70%)",
          pointerEvents: "none",
          zIndex: 0,
        }}
      />

      <div
        style={{
          position: "relative",
          zIndex: 1,
          width: "100%",
          maxWidth: 460,
          background: "#0D111E",
          border: "1px solid rgba(6,182,212,0.35)",
          borderRadius: 24,
          padding: 30,
          boxShadow: "0 25px 60px rgba(0,0,0,0.8), 0 0 30px rgba(6,182,212,0.15)",
        }}
      >
        {/* Brand Header */}
        <div style={{ textAlign: "center", marginBottom: 24 }}>
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              padding: "6px 14px",
              borderRadius: 20,
              background: "rgba(16,185,129,0.12)",
              border: "1px solid rgba(16,185,129,0.4)",
              color: "#10B981",
              fontSize: 12,
              fontWeight: 900,
              marginBottom: 14,
            }}
          >
            ✅ ICICI Direct Authenticated
          </div>
          <h1 style={{ fontSize: 22, fontWeight: 900, color: "#FFFFFF", margin: "0 0 8px" }}>
            Session Token Captured!
          </h1>
          <p style={{ fontSize: 13, color: "#94A3B8", margin: 0, lineHeight: 1.5 }}>
            Your daily ICICI Breeze trading token has been generated successfully.
          </p>
        </div>

        {/* Token Card */}
        <div
          style={{
            background: "#060812",
            border: "1px solid rgba(255,255,255,0.08)",
            borderRadius: 16,
            padding: 16,
            marginBottom: 20,
          }}
        >
          <div
            style={{
              fontSize: 10.5,
              fontWeight: 900,
              color: "#06B6D4",
              letterSpacing: 0.8,
              textTransform: "uppercase",
              marginBottom: 8,
            }}
          >
            Today's Session Token (apisession)
          </div>
          <div
            style={{
              fontFamily: "monospace",
              fontSize: 16,
              fontWeight: 800,
              color: token ? "#FFFFFF" : "#64748B",
              wordBreak: "break-all",
              background: "rgba(255,255,255,0.03)",
              padding: "10px 12px",
              borderRadius: 10,
              border: "1px solid rgba(6,182,212,0.2)",
            }}
          >
            {token || "No apisession detected in URL"}
          </div>
        </div>

        {/* Action Buttons */}
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {token && (
            <button
              onClick={handleCopy}
              style={{
                width: "100%",
                padding: "14px 20px",
                borderRadius: 14,
                border: "none",
                background: copied
                  ? "#10B981"
                  : "linear-gradient(90deg, #00B4D8 0%, #0284C7 35%, #6366F1 70%, #8B5CF6 100%)",
                color: "#FFFFFF",
                fontSize: 14,
                fontWeight: 900,
                cursor: "pointer",
                boxShadow: "0 6px 20px rgba(6,182,212,0.3)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 8,
                transition: "all 0.2s ease",
              }}
            >
              {copied ? "✅ Copied to Clipboard!" : "📋 Copy Session Token"}
            </button>
          )}

          {token && (
            <a
              href={`stokvigil://breeze-callback?apisession=${encodeURIComponent(token)}`}
              style={{
                width: "100%",
                padding: "13px 18px",
                borderRadius: 14,
                border: "1.5px solid rgba(139,92,246,0.6)",
                background: "rgba(139,92,246,0.14)",
                color: "#C4B5FD",
                fontSize: 13.5,
                fontWeight: 900,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 8,
                textDecoration: "none",
                textAlign: "center",
                boxShadow: "0 4px 14px rgba(139,92,246,0.2)",
              }}
            >
              📱 1-Tap Open in StokVigil App →
            </a>
          )}

          <button
            onClick={() => router.push(`/?apisession=${encodeURIComponent(token)}`)}
            style={{
              width: "100%",
              padding: "12px 18px",
              borderRadius: 14,
              border: "1px solid rgba(6,182,212,0.35)",
              background: "rgba(6,182,212,0.08)",
              color: "#06B6D4",
              fontSize: 13,
              fontWeight: 800,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 6,
            }}
          >
            ← Return to StokVigil Web Portal
          </button>
        </div>

        {/* Mobile App Helper */}
        <div
          style={{
            marginTop: 20,
            padding: 12,
            borderRadius: 12,
            background: "rgba(255,255,255,0.02)",
            border: "1px solid rgba(255,255,255,0.06)",
            textAlign: "center",
            fontSize: 11.5,
            color: "#94A3B8",
            lineHeight: 1.4,
          }}
        >
          📱 <strong>Using the Android Mobile App?</strong>
          <br />
          Copy the token above and paste it into the <strong>SESSION TOKEN</strong> field in your StokVigil app.
        </div>
      </div>
    </div>
  );
}

export default function CallbackPage() {
  return (
    <Suspense
      fallback={
        <div
          style={{
            minHeight: "100vh",
            background: "#070913",
            color: "#06B6D4",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontFamily: "sans-serif",
            fontWeight: 800,
          }}
        >
          Processing ICICI Breeze Authentication...
        </div>
      }
    >
      <CallbackContent />
    </Suspense>
  );
}
