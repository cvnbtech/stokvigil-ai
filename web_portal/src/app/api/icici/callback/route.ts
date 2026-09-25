import { NextRequest, NextResponse } from "next/server";

function findApiSession(entries: Iterable<[string, string | File]>): string {
  for (const [key, value] of entries) {
    if (key.toLowerCase() === "apisession" && typeof value === "string" && value.trim()) {
      return value.trim();
    }
  }
  return "";
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const apisession = findApiSession(searchParams.entries());

  const redirectUrl = new URL("/api/auth/icici-callback", request.url);
  if (apisession) {
    redirectUrl.searchParams.set("apisession", apisession);
  }

  return NextResponse.redirect(redirectUrl);
}

export async function POST(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  let apisession = findApiSession(searchParams.entries());

  if (!apisession) {
    try {
      const contentType = request.headers.get("content-type") || "";
      if (contentType.includes("form") || contentType.includes("urlencoded")) {
        const formData = await request.formData();
        apisession = findApiSession(formData.entries());
      } else if (contentType.includes("json")) {
        const json = await request.json();
        if (json && typeof json === "object") {
          for (const [key, value] of Object.entries(json)) {
            if (key.toLowerCase() === "apisession" && typeof value === "string" && value.trim()) {
              apisession = value.trim();
              break;
            }
          }
        }
      } else {
        const text = await request.text();
        const bodyParams = new URLSearchParams(text);
        apisession = findApiSession(bodyParams.entries());
      }
    } catch {
      // Fallback
    }
  }

  const redirectUrl = new URL("/api/auth/icici-callback", request.url);
  if (apisession) {
    redirectUrl.searchParams.set("apisession", apisession);
  }

  return NextResponse.redirect(redirectUrl, { status: 303 });
}

