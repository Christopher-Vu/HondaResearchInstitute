// Canva Connect: OAuth with PKCE, then a URL import of the poster PDF, which Canva fetches itself.
// Needs a Canva developer app with the design:content:write scope and
// <origin>/api/canva/callback as a redirect URL; its credentials live in CANVA_CLIENT_ID and CANVA_CLIENT_SECRET.
const API = "https://api.canva.com/rest/v1";
const AUTHORIZE = "https://www.canva.com/api/oauth/authorize";
const SCOPE = "design:content:write";

export const POSTER_PDF_PATH = "/poster/exports/poster.pdf";
export const CALLBACK_PATH = "/api/canva/callback";
export const COOKIE = { verifier: "canva_verifier", state: "canva_state", token: "canva_token" } as const;
export const COOKIE_OPTIONS = {
  httpOnly: true,
  secure: process.env.NODE_ENV === "production",
  sameSite: "lax",
  path: "/api/canva",
  maxAge: 600,
} as const;

export interface ImportJob {
  status: "in_progress" | "success" | "failed";
  editUrl?: string;
  error?: string;
}

interface CanvaJob {
  id: string;
  status: ImportJob["status"];
  result?: { designs: { urls: { edit_url: string } }[] };
  error?: { code: string; message: string };
}

export function canvaConfigured() {
  return Boolean(process.env.CANVA_CLIENT_ID && process.env.CANVA_CLIENT_SECRET);
}

function base64url(bytes: Uint8Array) {
  return Buffer.from(bytes).toString("base64url");
}

export function randomToken() {
  return base64url(crypto.getRandomValues(new Uint8Array(48)));
}

export async function authorizeUrl(origin: string, verifier: string, state: string) {
  const challenge = base64url(new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier))));
  const params = new URLSearchParams({
    response_type: "code",
    client_id: process.env.CANVA_CLIENT_ID ?? "",
    redirect_uri: origin + CALLBACK_PATH,
    scope: SCOPE,
    state,
    code_challenge: challenge,
    code_challenge_method: "S256",
  });
  return `${AUTHORIZE}?${params}`;
}

async function canva<T>(path: string, init: RequestInit): Promise<T> {
  const response = await fetch(API + path, { ...init, cache: "no-store" });
  if (!response.ok) throw new Error(`Canva ${path} answered ${response.status}`);
  return (await response.json()) as T;
}

export async function exchangeCode(origin: string, code: string, verifier: string) {
  const credentials = Buffer.from(`${process.env.CANVA_CLIENT_ID}:${process.env.CANVA_CLIENT_SECRET}`).toString("base64");
  const token = await canva<{ access_token: string }>("/oauth/token", {
    method: "POST",
    headers: { Authorization: `Basic ${credentials}`, "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "authorization_code",
      code,
      code_verifier: verifier,
      redirect_uri: origin + CALLBACK_PATH,
    }),
  });
  return token.access_token;
}

export async function startPosterImport(origin: string, accessToken: string) {
  const { job } = await canva<{ job: CanvaJob }>("/url-imports", {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken}`, "Content-Type": "application/json" },
    body: JSON.stringify({ title: "Failure-axis research poster", url: origin + POSTER_PDF_PATH, mime_type: "application/pdf" }),
  });
  return job.id;
}

export async function importStatus(jobId: string, accessToken: string): Promise<ImportJob> {
  const { job } = await canva<{ job: CanvaJob }>(`/url-imports/${encodeURIComponent(jobId)}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  return { status: job.status, editUrl: job.result?.designs[0]?.urls.edit_url, error: job.error?.message };
}
