import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export async function middleware(request: NextRequest) {
  const { pathname, searchParams } = request.nextUrl;

  // Intercept POST requests to /callback or / and convert to 303 GET redirect to /api/auth/icici-callback
  if (request.method === "POST" && (pathname === "/callback" || pathname === "/" || pathname === "/api/icici/callback")) {
    let apisession = "";
    for (const [k, v] of searchParams.entries()) {
      if (k.toLowerCase() === "apisession" && v.trim()) {
        apisession = v.trim();
        break;
      }
    }

    if (!apisession) {
      try {
        const contentType = request.headers.get("content-type") || "";
        if (contentType.includes("form") || contentType.includes("urlencoded")) {
          const text = await request.text();
          const bodyParams = new URLSearchParams(text);
          for (const [k, v] of bodyParams.entries()) {
            if (k.toLowerCase() === "apisession" && v.trim()) {
              apisession = v.trim();
              break;
            }
          }
        }
      } catch {
        // Fallback gracefully
      }
    }

    const redirectUrl = new URL("/api/auth/icici-callback", request.url);
    if (apisession) {
      redirectUrl.searchParams.set("apisession", apisession);
    }
    return NextResponse.redirect(redirectUrl, { status: 303 });
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/callback", "/", "/api/icici/callback"],
};
