import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export async function middleware(request: NextRequest) {
  const { pathname, searchParams } = request.nextUrl;

  // Intercept POST requests to /callback or root and convert to 303 GET redirect
  if (request.method === "POST" && (pathname === "/callback" || pathname === "/" || pathname === "/api/auth/icici-callback" || pathname === "/api/icici/callback")) {
    let apisession = searchParams.get("apisession") || "";

    if (!apisession) {
      try {
        const contentType = request.headers.get("content-type") || "";
        if (contentType.includes("form") || contentType.includes("urlencoded")) {
          const text = await request.text();
          const bodyParams = new URLSearchParams(text);
          apisession = bodyParams.get("apisession") || bodyParams.get("api_session") || "";
        }
      } catch {
        // Fallback gracefully
      }
    }

    const redirectUrl = new URL("/callback", request.url);
    if (apisession) {
      redirectUrl.searchParams.set("apisession", apisession);
    }
    return NextResponse.redirect(redirectUrl, { status: 303 });
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/callback", "/", "/api/auth/icici-callback", "/api/icici/callback"],
};
