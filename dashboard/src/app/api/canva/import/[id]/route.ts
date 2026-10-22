import { NextResponse, type NextRequest } from "next/server";
import { COOKIE, importStatus } from "@/lib/canva";

export async function GET(request: NextRequest, ctx: RouteContext<"/api/canva/import/[id]">) {
  const token = request.cookies.get(COOKIE.token)?.value;
  if (!token) return NextResponse.json({ status: "failed", error: "Canva sign-in expired" }, { status: 401 });
  const { id } = await ctx.params;
  try {
    return NextResponse.json(await importStatus(id, token));
  } catch (error) {
    console.error(error);
    return NextResponse.json({ status: "failed", error: "Canva did not answer" }, { status: 502 });
  }
}
