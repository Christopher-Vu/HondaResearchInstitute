import { NextResponse, connection, type NextRequest } from "next/server";
import { COOKIE, COOKIE_OPTIONS, canvaConfigured, exchangeCode, startPosterImport } from "@/lib/canva";

function backToPoster(request: NextRequest, params: Record<string, string>) {
  const url = new URL("/poster", request.nextUrl.origin);
  for (const [key, value] of Object.entries(params)) url.searchParams.set(key, value);
  const response = NextResponse.redirect(url);
  response.cookies.delete({ name: COOKIE.verifier, path: COOKIE_OPTIONS.path });
  response.cookies.delete({ name: COOKIE.state, path: COOKIE_OPTIONS.path });
  return response;
}

// Canva returns here after the user approves; the import starts now and /poster polls it.
export async function GET(request: NextRequest) {
  // Without this, cacheComponents prerenders the build-time "not configured" answer.
  await connection();
  if (!canvaConfigured()) return new NextResponse("Canva import is not configured", { status: 404 });
  const query = request.nextUrl.searchParams;
  const code = query.get("code");
  const verifier = request.cookies.get(COOKIE.verifier)?.value;
  const stateMatches = query.get("state") !== null && query.get("state") === request.cookies.get(COOKIE.state)?.value;
  if (!code || !verifier || !stateMatches) return backToPoster(request, { canva_error: query.get("error") ?? "denied" });
  try {
    const token = await exchangeCode(request.nextUrl.origin, code, verifier);
    const jobId = await startPosterImport(request.nextUrl.origin, token);
    const response = backToPoster(request, { canva_job: jobId });
    response.cookies.set(COOKIE.token, token, COOKIE_OPTIONS);
    return response;
  } catch (error) {
    console.error(error);
    return backToPoster(request, { canva_error: "import_failed" });
  }
}
