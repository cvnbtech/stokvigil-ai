import { NextRequest } from "next/server";

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const symbols = searchParams.get("symbols") || "";

  const backendUrl = (
    process.env.STOKVIGIL_BACKEND_URL ||
    process.env.NEXT_PUBLIC_BACKEND_URL ||
    "http://127.0.0.1:8000"
  ).replace(/\/+$/, "");

  const targetUrl = `${backendUrl}/api/stocks/stream${symbols ? `?symbols=${encodeURIComponent(symbols)}` : ""}`;

  try {
    const upstreamRes = await fetch(targetUrl, {
      headers: {
        Accept: "text/event-stream",
        "Cache-Control": "no-cache",
      },
      cache: "no-store",
    });

    if (!upstreamRes.ok || !upstreamRes.body) {
      return new Response("Upstream streaming service unavailable", {
        status: upstreamRes.status || 503,
        headers: { "Content-Type": "text/plain" },
      });
    }

    // Proxy the ReadableStream directly to client with SSE headers
    return new Response(upstreamRes.body, {
      status: 200,
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache, no-transform",
        Connection: "keep-alive",
        "X-Accel-Buffering": "no",
      },
    });
  } catch (error: any) {
    return new Response(`Stream connection error: ${error?.message || "unknown"}`, {
      status: 503,
      headers: { "Content-Type": "text/plain" },
    });
  }
}
