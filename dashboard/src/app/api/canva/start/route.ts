import { NextResponse, connection, type NextRequest } from "next/server";
import { COOKIE, COOKIE_OPTIONS, authorizeUrl, canvaConfigured, randomToken } from "@/lib/canva";

export async function GET(request: NextRequest) {
  // Without this, cacheComponents prerenders the build-time "not configured" answer.
  await connection();
  if (!canvaConfigured()) return new NextResponse("Canva import is not configured", { status: 404 });
  const verifier = randomToken();
  const state = randomToken();
  const response = NextResponse.redirect(await authorizeUrl(request.nextUrl.origin, verifier, state));
  response.cookies.set(COOKIE.verifier, verifier, COOKIE_OPTIONS);
  response.cookies.set(COOKIE.state, state, COOKIE_OPTIONS);
  return response;
}
