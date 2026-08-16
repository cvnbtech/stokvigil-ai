import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const apisession = searchParams.get("apisession") || searchParams.get("api_session") || "";

  const redirectUrl = new URL("/callback", request.url);
  if (apisession) {
    redirectUrl.searchParams.set("apisession", apisession);
  }

  return NextResponse.redirect(redirectUrl);
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

  const redirectUrl = new URL("/callback", request.url);
  if (apisession) {
    redirectUrl.searchParams.set("apisession", apisession);
  }

  return NextResponse.redirect(redirectUrl, { status: 303 });
}
