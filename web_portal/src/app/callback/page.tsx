"use client";

import React, { useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";

function CallbackForwarder() {
  const searchParams = useSearchParams();

  useEffect(() => {
    const apisession = searchParams.get("apisession") || searchParams.get("api_session") || "";
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
