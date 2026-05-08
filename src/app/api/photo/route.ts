import type { NextRequest } from "next/server";

const REF_PATTERN = /^places\/[A-Za-z0-9_-]+\/photos\/[A-Za-z0-9_-]+$/;
const ALLOWED_WIDTHS = new Set(["200", "400", "800", "1200", "1600"]);
const DEFAULT_WIDTH = "800";

export async function GET(req: NextRequest) {
  const refRaw = req.nextUrl.searchParams.get("ref")?.trim() ?? "";
  const ref = refRaw.replace(/^\/+/, "");
  if (!ref || !REF_PATTERN.test(ref)) {
    return new Response("invalid ref", { status: 400 });
  }

  const wParam = req.nextUrl.searchParams.get("w") ?? DEFAULT_WIDTH;
  const w = ALLOWED_WIDTHS.has(wParam) ? wParam : DEFAULT_WIDTH;

  const apiKey = process.env.GOOGLE_PLACES_API_KEY;
  if (!apiKey) {
    return new Response("server misconfigured", { status: 500 });
  }

  const upstream = await fetch(
    `https://places.googleapis.com/v1/${ref}/media?key=${apiKey}&maxWidthPx=${w}`,
    { redirect: "follow" },
  );
  if (!upstream.ok || !upstream.body) {
    return new Response("upstream error", { status: 502 });
  }

  return new Response(upstream.body, {
    status: 200,
    headers: {
      "Content-Type": upstream.headers.get("Content-Type") ?? "image/jpeg",
      "Cache-Control":
        "public, max-age=2592000, s-maxage=2592000, stale-while-revalidate=86400",
    },
  });
}
