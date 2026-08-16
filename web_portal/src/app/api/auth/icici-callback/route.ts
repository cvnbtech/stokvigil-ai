import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const apisession = searchParams.get("apisession") || "";

  // Redirect to the dedicated client-side callback page with token preserved
  const redirectUrl = new URL("/callback", request.url);
  if (apisession) {
    redirectUrl.searchParams.set("apisession", apisession);
  }

  return NextResponse.redirect(redirectUrl);
}

export async function POST(request: NextRequest) {
  return GET(request);
}
