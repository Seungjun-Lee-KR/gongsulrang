import type { NextRequest } from "next/server";

const REF_PATTERN = /^places\/[A-Za-z0-9_-]+\/photos\/[A-Za-z0-9_-]+$/;
const ALLOWED_WIDTHS = new Set(["200", "400", "800", "1200", "1600"]);
const DEFAULT_WIDTH = "800";

function fetchMedia(ref: string, apiKey: string, w: string) {
  return fetch(
    `https://places.googleapis.com/v1/${ref}/media?key=${apiKey}&maxWidthPx=${w}`,
    { redirect: "follow" },
  );
}

/**
 * 저장된 photo 참조는 구글이 주기적으로 회전시켜 만료된다(400 INVALID).
 * 그 경우 place id로 Place Details(photos)를 다시 불러 같은 슬롯(i)의
 * 새 참조로 재시도한다 — 응답이 CDN에 30일 캐시되므로 치유 비용은
 * 실제 조회된 이미지당 한 번이다.
 */
async function freshRef(
  pid: string,
  slot: number,
  apiKey: string,
): Promise<string | null> {
  const res = await fetch(`https://places.googleapis.com/v1/places/${pid}`, {
    headers: { "X-Goog-Api-Key": apiKey, "X-Goog-FieldMask": "photos" },
  });
  if (!res.ok) return null;
  const data = (await res.json()) as { photos?: { name?: string }[] };
  const photos = data.photos ?? [];
  if (photos.length === 0) return null;
  const name = photos[Math.min(slot, photos.length - 1)]?.name;
  return name && REF_PATTERN.test(name) ? name : null;
}

export async function GET(req: NextRequest) {
  const refRaw = req.nextUrl.searchParams.get("ref")?.trim() ?? "";
  const ref = refRaw.replace(/^\/+/, "");
  if (!ref || !REF_PATTERN.test(ref)) {
    return new Response("invalid ref", { status: 400 });
  }

  const wParam = req.nextUrl.searchParams.get("w") ?? DEFAULT_WIDTH;
  const w = ALLOWED_WIDTHS.has(wParam) ? wParam : DEFAULT_WIDTH;
  const iParam = Number(req.nextUrl.searchParams.get("i") ?? "0");
  const slot = Number.isInteger(iParam) && iParam >= 0 && iParam < 10 ? iParam : 0;

  const apiKey = process.env.GOOGLE_PLACES_API_KEY;
  if (!apiKey) {
    return new Response("server misconfigured", { status: 500 });
  }

  let upstream = await fetchMedia(ref, apiKey, w);
  if (upstream.status === 400 || upstream.status === 404) {
    const pid = ref.split("/")[1];
    const renewed = await freshRef(pid, slot, apiKey);
    if (renewed) {
      upstream = await fetchMedia(renewed, apiKey, w);
    }
  }
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
