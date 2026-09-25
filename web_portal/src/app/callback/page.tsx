"use client";

import React, { useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";

function CallbackForwarder() {
  const searchParams = useSearchParams();

  useEffect(() => {
    let apisession = "";
    if (searchParams) {
      for (const [k, v] of searchParams.entries()) {
        if (k.toLowerCase() === "apisession" && v.trim()) {
          apisession = v.trim();
          break;
        }
      }
    }

    if (!apisession && typeof window !== "undefined") {
      const windowParams = new URLSearchParams(window.location.search);
      for (const [k, v] of windowParams.entries()) {
        if (k.toLowerCase() === "apisession" && v.trim()) {
          apisession = v.trim();
          break;
        }
      }
      if (!apisession) {
        const hashParams = new URLSearchParams(window.location.hash.replace(/^#/, ""));
        for (const [k, v] of hashParams.entries()) {
          if (k.toLowerCase() === "apisession" && v.trim()) {
            apisession = v.trim();
            break;
          }
        }
      }
    }

    if (apisession) {
      try {
        sessionStorage.setItem("stokvigil_pending_apisession", apisession);
      } catch (_) {}
    }

    const target = apisession
      ? `/api/auth/icici-callback?apisession=${encodeURIComponent(apisession)}`
      : `/api/auth/icici-callback`;
    window.location.replace(target);
  }, [searchParams]);

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#070913",
        color: "#06B6D4",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "'Plus Jakarta Sans', sans-serif",
        fontWeight: 800,
      }}
    >
      Redirecting to StokVigil ICICI Breeze Authentication Handler...
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
          }}
        >
          Loading...
        </div>
      }
    >
      <CallbackForwarder />
    </Suspense>
  );
}
