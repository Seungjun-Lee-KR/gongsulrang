"""
6단계: 지오코딩된 CSV → 프론트엔드 restaurants.json 생성

입력: output/gongsulrang_ranking_seoul_2024_geo.csv
출력: ~/Desktop/my-site/src/data/restaurants.json (Restaurant[] 스키마)

Restaurant {
  rank, name, region, visits, totalAmount, avgAmount,
  deptCount, topAgency?, lat?, lng?
}
"""

import os as _os
from pathlib import Path as _Path
_os.chdir(_Path(__file__).resolve().parent.parent)
import csv
import json
import os

SRC = "data/output/gongsulrang_ranking_seoul_2024_geo.csv"
ENRICH = "data/output/places_enrich.json"
DST = "src/data/restaurants.json"
# 상위 N건만 프론트로 (전체는 수만 건일 수 있음)
TOP_N = 3000
# 좌표 없는 건 프론트에서 핀이 안 찍히므로 제외
REQUIRE_LATLNG = True

def main():
    rows = list(csv.DictReader(open(SRC, encoding="utf-8-sig")))
    enrich = {}
    if os.path.exists(ENRICH):
        enrich = json.load(open(ENRICH, encoding="utf-8"))
    out = []
    rank = 0
    for r in rows:
        lat_s = r.get("lat", "").strip()
        lng_s = r.get("lng", "").strip()
        if REQUIRE_LATLNG and (not lat_s or not lng_s):
            continue
        try:
            lat = float(lat_s) if lat_s else None
            lng = float(lng_s) if lng_s else None
        except ValueError:
            continue
        rank += 1
        item = {
            "rank": rank,
            "name": r["식당명"],
            "region": r.get("지역", "") or "서울",
            "visits": int(r["이용횟수"]),
            "totalAmount": int(r["총이용금액"]),
            "avgAmount": int(r["평균금액"]),
            "deptCount": int(r["집행부서수"]),
        }
        top = r.get("주요이용기관")
        if top:
            item["topAgency"] = top
        if lat is not None:
            item["lat"] = lat
        if lng is not None:
            item["lng"] = lng

        gu = (r.get("kakao_gu") or "").strip()
        dong = (r.get("kakao_dong") or "").strip()
        if gu or dong:
            item["guDong"] = f"{gu} {dong}".strip()
        road = (r.get("kakao_road") or "").strip()
        addr_jibun = (r.get("kakao_addr") or "").strip()
        if road:
            item["address"] = road
        elif addr_jibun:
            item["address"] = addr_jibun

        ekey = f"{r['식당명']}|{r.get('지역','')}|{r.get('주소','')}"
        e = enrich.get(ekey, {})
        if e.get("status") == "ok":
            if e.get("place_id"):
                item["placeId"] = e["place_id"]
            if e.get("rating") is not None:
                item["rating"] = e["rating"]
            if e.get("user_rating_count") is not None:
                item["ratingCount"] = e["user_rating_count"]
            if e.get("phone"):
                item["phone"] = e["phone"]
            if e.get("hours"):
                item["hours"] = e["hours"]
            if e.get("photos"):
                item["photos"] = e["photos"]
            if e.get("google_maps_uri"):
                item["googleMapsUri"] = e["google_maps_uri"]
            if e.get("formatted_address"):
                item["formattedAddress"] = e["formatted_address"]

        out.append(item)
        if rank >= TOP_N:
            break

    with open(DST, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"✅ {len(out)}건 → {DST}")

if __name__ == "__main__":
    main()
