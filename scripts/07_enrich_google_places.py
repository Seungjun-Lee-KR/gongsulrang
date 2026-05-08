"""
7단계: TOP 300 식당을 Google Places API (New) 로 enrich

- 입력: output/gongsulrang_ranking_seoul_2024_geo.csv (상위 N개)
- 출력:
    output/places_enrich.json — {식별키: {place_id, rating, userRatingCount, phone, hours[], photos[], googleMapsUri, address}}
    ~/Desktop/my-site/public/places/{place_id}_{i}.jpg — 사진 최대 3장
- 캐시: output/.places_cache.json (재실행 시 동일 식당 스킵)

필드 마스크 주의: 요청한 필드만 과금. SKU tier 별 가격 다름.
- IDs only (id): Essentials ($5/1k)
- displayName, formattedAddress, location, photos (metadata), rating, userRatingCount, openingHours, phoneNumber 등: Enterprise ($32/1k) 일부
- Place Photos media 요청은 per-photo 별도 과금
"""

import os as _os
from pathlib import Path as _Path
_os.chdir(_Path(__file__).resolve().parent.parent)
import argparse
import csv
import json
import os
import sys
import time

import requests
from dotenv import load_dotenv

load_dotenv(".env.local")
KEY = os.getenv("GOOGLE_PLACES_API_KEY")
if not KEY:
    print("GOOGLE_PLACES_API_KEY가 .env에 없습니다.")
    sys.exit(1)

SRC = "data/output/gongsulrang_ranking_seoul_2024_geo.csv"
OUT_JSON = "data/output/places_enrich.json"
CACHE = "data/output/.places_cache.json"
PHOTO_DIR = "public/places"
PHOTO_MAX = 3
PHOTO_WIDTH = 800

TEXT_SEARCH = "https://places.googleapis.com/v1/places:searchText"
FIELD_MASK = ",".join([
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.location",
    "places.rating",
    "places.userRatingCount",
    "places.internationalPhoneNumber",
    "places.nationalPhoneNumber",
    "places.regularOpeningHours.weekdayDescriptions",
    "places.regularOpeningHours.openNow",
    "places.googleMapsUri",
    "places.websiteUri",
    "places.priceLevel",
    "places.photos",
])
RATE = 0.15


def cache_load():
    if os.path.exists(CACHE):
        return json.load(open(CACHE, encoding="utf-8"))
    return {}


def cache_save(c):
    json.dump(c, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)


def text_search(name: str, region: str, addr: str):
    # "식당명 + 지역 + 도로명" 조합이 정확도 최상. 주소가 비었으면 식당명+지역.
    query = f"{name} {region} {addr}".strip() if addr else f"{name} {region or '서울'}".strip()
    r = requests.post(
        TEXT_SEARCH,
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": KEY,
            "X-Goog-FieldMask": FIELD_MASK,
        },
        json={
            "textQuery": query,
            "languageCode": "ko",
            "regionCode": "KR",
            "maxResultCount": 1,
        },
        timeout=15,
    )
    if r.status_code != 200:
        return None, f"http_{r.status_code}"
    data = r.json()
    places = data.get("places") or []
    if not places:
        return None, "no_match"
    return places[0], "ok"


def download_photo(photo_name: str, dst_path: str) -> bool:
    url = f"https://places.googleapis.com/v1/{photo_name}/media"
    r = requests.get(url, params={"key": KEY, "maxWidthPx": PHOTO_WIDTH}, timeout=30, allow_redirects=True)
    if r.status_code != 200 or not r.content:
        return False
    with open(dst_path, "wb") as f:
        f.write(r.content)
    return True


def enrich_row(row: dict, cache: dict, download: bool = False):
    name = row["식당명"].strip()
    region = row.get("지역", "").strip()
    addr = row.get("주소", "").strip()
    key = f"{name}|{region}|{addr}"
    if key in cache:
        return cache[key]

    place, status = text_search(name, region, addr)
    if not place:
        cache[key] = {"status": status}
        return cache[key]

    pid = place.get("id")
    photos = place.get("photos") or []
    photo_refs = [p["name"] for p in photos[:PHOTO_MAX]]
    saved_photos = []
    if download:
        for i, pn in enumerate(photo_refs, 1):
            dst = os.path.join(PHOTO_DIR, f"{pid}_{i}.jpg")
            if os.path.exists(dst):
                saved_photos.append(f"/places/{pid}_{i}.jpg")
                continue
            ok = download_photo(pn, dst)
            if ok:
                saved_photos.append(f"/places/{pid}_{i}.jpg")
            time.sleep(RATE)

    enriched = {
        "status": "ok",
        "place_id": pid,
        "display_name": (place.get("displayName") or {}).get("text", ""),
        "formatted_address": place.get("formattedAddress", ""),
        "rating": place.get("rating"),
        "user_rating_count": place.get("userRatingCount"),
        "phone": place.get("internationalPhoneNumber") or place.get("nationalPhoneNumber") or "",
        "hours": (place.get("regularOpeningHours") or {}).get("weekdayDescriptions") or [],
        "google_maps_uri": place.get("googleMapsUri", ""),
        "website_uri": place.get("websiteUri", ""),
        "price_level": place.get("priceLevel"),
        "photo_refs": photo_refs,
        "photos": saved_photos,
    }
    cache[key] = enriched
    return enriched


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=300, help="상위 N개만 enrich")
    ap.add_argument("--download", action="store_true", help="사진을 public/places/로 다운로드 (기본 off — 옵션 B 동적 프록시 사용)")
    args = ap.parse_args()

    if args.download:
        os.makedirs(PHOTO_DIR, exist_ok=True)
    cache = cache_load()
    # 기존 places_enrich.json — cache hit 시 photo_refs 등 보강 데이터 보존용
    prior = {}
    if os.path.exists(OUT_JSON):
        try:
            prior = json.load(open(OUT_JSON, encoding="utf-8"))
        except Exception:
            prior = {}
    rows = list(csv.DictReader(open(SRC, encoding="utf-8-sig")))
    target = rows[:args.top]
    print(f"대상: {len(target)}건 (TOP {args.top}, download={args.download})")

    result = {}
    n_ok = n_fail = 0
    for i, row in enumerate(target, 1):
        key = f"{row['식당명']}|{row.get('지역','')}|{row.get('주소','')}"
        try:
            e = enrich_row(row, cache, download=args.download)
        except Exception as ex:
            e = {"status": f"err:{type(ex).__name__}: {ex}"}
        # cache hit가 photo_refs 누락이지만 직전 places_enrich.json에 있으면 보존
        if e.get("status") == "ok" and not e.get("photo_refs"):
            prior_refs = (prior.get(key) or {}).get("photo_refs")
            if prior_refs:
                e = {**e, "photo_refs": prior_refs}
        result[key] = {"rank": int(row["순위"]), "name": row["식당명"], "region": row.get("지역",""), **e}
        if e.get("status") == "ok":
            n_ok += 1
        else:
            n_fail += 1
        if i % 20 == 0 or i == len(target):
            cache_save(cache)
            with open(OUT_JSON, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"  [{i}/{len(target)}] ok={n_ok} fail={n_fail}")
        time.sleep(RATE)

    cache_save(cache)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n✅ ok={n_ok} fail={n_fail} / {len(target)} → {OUT_JSON}")


if __name__ == "__main__":
    main()
