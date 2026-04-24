import type { NextRequest } from "next/server";

type KakaoKeywordDoc = {
  place_name: string;
  address_name: string;
  road_address_name: string;
  x: string;
  y: string;
};

export async function GET(req: NextRequest) {
  const q = req.nextUrl.searchParams.get("q")?.trim() ?? "";
  if (!q) return Response.json({ error: "query required" }, { status: 400 });

  const key = process.env.KAKAO_REST_API_KEY;
  if (!key) {
    return Response.json(
      { error: "KAKAO_REST_API_KEY가 서버에 설정되지 않았습니다." },
      { status: 501 },
    );
  }

  const kwUrl = `https://dapi.kakao.com/v2/local/search/keyword.json?query=${encodeURIComponent(q)}&size=1`;
  const kwRes = await fetch(kwUrl, {
    headers: { Authorization: `KakaoAK ${key}` },
    cache: "no-store",
  });
  if (!kwRes.ok) {
    return Response.json({ error: `Kakao keyword ${kwRes.status}` }, { status: 502 });
  }
  const kwJson = (await kwRes.json()) as { documents?: KakaoKeywordDoc[] };
  const top = kwJson.documents?.[0];
  if (top) {
    return Response.json({
      name: top.place_name,
      address: top.road_address_name || top.address_name,
      lat: Number(top.y),
      lng: Number(top.x),
    });
  }

  const addrUrl = `https://dapi.kakao.com/v2/local/search/address.json?query=${encodeURIComponent(q)}&size=1`;
  const addrRes = await fetch(addrUrl, {
    headers: { Authorization: `KakaoAK ${key}` },
    cache: "no-store",
  });
  if (!addrRes.ok) {
    return Response.json({ error: `Kakao address ${addrRes.status}` }, { status: 502 });
  }
  const addrJson = (await addrRes.json()) as {
    documents?: Array<{ address_name: string; x: string; y: string }>;
  };
  const hit = addrJson.documents?.[0];
  if (hit) {
    return Response.json({
      name: q,
      address: hit.address_name,
      lat: Number(hit.y),
      lng: Number(hit.x),
    });
  }

  return Response.json({ error: "검색 결과가 없습니다." }, { status: 404 });
}
