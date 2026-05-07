"""
5단계: 랭킹 CSV의 식당 주소를 위경도로 변환 (Kakao Local API)

필요:
  .env 의 KAKAO_REST_API_KEY (Kakao 개발자 > 앱 > REST API 키)

입력:  output/gongsulrang_ranking_seoul_2024.csv
출력:  output/gongsulrang_ranking_seoul_2024_geo.csv (lat, lng 추가)
캐시:  output/.geo_cache.json (동일 주소 재요청 방지)
"""

import os as _os
from pathlib import Path as _Path
_os.chdir(_Path(__file__).resolve().parent.parent)
import argparse
import os
import csv
import json
import time
import sys
import requests
from dotenv import load_dotenv

load_dotenv(".env.local")
KEY = os.getenv("KAKAO_REST_API_KEY")
if not KEY:
    print("KAKAO_REST_API_KEY가 .env에 없습니다. Kakao 개발자 > 앱 > REST API 키 복사해 추가하세요.")
    sys.exit(1)

SRC = "data/output/gongsulrang_ranking_seoul_2024.csv"
DST = "data/output/gongsulrang_ranking_seoul_2024_geo.csv"
CACHE = "data/output/.geo_cache.json"

RATE = 0.12  # 초당 8회 (Kakao 개인 한도 넉넉)

def _empty():
    return {"lat": None, "lng": None, "gu": "", "dong": "", "addr": "", "road": ""}

def load_cache():
    if os.path.exists(CACHE):
        raw = json.load(open(CACHE, encoding="utf-8"))
        # 구 포맷(list: [lat, lng])은 address 없으므로 dict로 감싸 재호출 유도
        c = {}
        for k, v in raw.items():
            if isinstance(v, dict):
                c[k] = v
            elif isinstance(v, list) and len(v) == 2:
                c[k] = {"lat": v[0], "lng": v[1], "gu": "", "dong": "", "addr": "", "road": ""}
        return c
    return {}

def save_cache(c):
    json.dump(c, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)

def _parse_address_doc(d):
    # /v2/local/search/address.json 응답 한 건에서 lat/lng/구/동/주소 추출
    a = d.get("address") or {}
    ra = d.get("road_address") or {}
    gu = a.get("region_2depth_name") or ra.get("region_2depth_name") or ""
    dong = a.get("region_3depth_name") or ra.get("region_3depth_name") or ""
    addr_name = a.get("address_name") or ""
    road_name = (ra or {}).get("address_name") or ""
    return {
        "lat": float(d["y"]),
        "lng": float(d["x"]),
        "gu": gu,
        "dong": dong,
        "addr": addr_name,
        "road": road_name,
    }

def _parse_keyword_doc(d):
    import re as _re
    addr_name = d.get("address_name") or ""
    road_name = d.get("road_address_name") or ""
    m = _re.search(r"([가-힣]+구)\s+([가-힣0-9]+동)", addr_name or road_name)
    gu, dong = (m.group(1), m.group(2)) if m else ("", "")
    return {
        "lat": float(d["y"]),
        "lng": float(d["x"]),
        "gu": gu,
        "dong": dong,
        "addr": addr_name,
        "road": road_name,
    }

def _cache_hit(c):
    """완전 캐시 = 주소까지 채워졌거나, API가 no-match로 확인해 비워둔 엔트리.
    lat/lng만 있고 주소가 비었으면 옛 포맷 변환본이므로 재호출 대상(miss)."""
    if not isinstance(c, dict):
        return False
    if c.get("addr") or c.get("road"):
        return True
    if c.get("lat") is None:  # no-match로 확정된 _empty 엔트리
        return True
    return False  # 옛 포맷에서 변환된 lat/lng만 있는 엔트리 → 재호출 필요

def geocode_addr(addr: str, cache: dict):
    if not addr:
        return None
    cached = cache.get(addr)
    if _cache_hit(cached):
        return cached if cached.get("lat") is not None else None
    try:
        r = requests.get(
            "https://dapi.kakao.com/v2/local/search/address.json",
            headers={"Authorization": f"KakaoAK {KEY}"},
            params={"query": addr},
            timeout=10,
        )
        if r.status_code != 200:
            cache[addr] = _empty(); return None
        docs = r.json().get("documents", [])
        if not docs:
            cache[addr] = _empty(); return None
        info = _parse_address_doc(docs[0])
        cache[addr] = info
        return info
    except Exception as e:
        print(f"  err: {addr[:30]} {e}")
        cache[addr] = _empty(); return None

def geocode_keyword(query: str, cache: dict):
    if not query: return None
    k = f"KW:{query}"
    cached = cache.get(k)
    if _cache_hit(cached):
        return cached if cached.get("lat") is not None else None
    try:
        r = requests.get(
            "https://dapi.kakao.com/v2/local/search/keyword.json",
            headers={"Authorization": f"KakaoAK {KEY}"},
            params={"query": query},
            timeout=10,
        )
        if r.status_code != 200:
            cache[k] = _empty(); return None
        docs = r.json().get("documents", [])
        if not docs:
            cache[k] = _empty(); return None
        info = _parse_keyword_doc(docs[0])
        cache[k] = info
        return info
    except Exception:
        cache[k] = _empty(); return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0,
                    help="상위 N개만 지오코딩 (0=전체). 나머지 행은 lat/lng 없이 CSV에 포함")
    args = ap.parse_args()
    cache = load_cache()
    rows = list(csv.DictReader(open(SRC, encoding="utf-8-sig")))
    fieldnames = list(rows[0].keys()) + ["lat", "lng", "geocode_method", "kakao_gu", "kakao_dong", "kakao_addr", "kakao_road"]
    n_ok, n_fail = 0, 0
    limit = args.limit if args.limit > 0 else len(rows)

    out = []
    for i, row in enumerate(rows, 1):
        if i > limit:
            row["lat"] = ""
            row["lng"] = ""
            row["geocode_method"] = ""
            row["kakao_gu"] = row["kakao_dong"] = row["kakao_addr"] = row["kakao_road"] = ""
            out.append(row)
            continue
        addr = row.get("주소", "").strip()
        name = row.get("식당명", "").strip()
        method = ""
        info = None
        if addr:
            info = geocode_addr(addr, cache)
            method = "addr" if info else ""
            time.sleep(RATE)
        if info is None and name:
            # 키워드 fallback: "지역 식당명"
            region = row.get("지역", "")
            q = f"{region} {name}" if region else name
            info = geocode_keyword(q, cache)
            method = "keyword" if info else ""
            time.sleep(RATE)
        row["lat"] = info["lat"] if info else ""
        row["lng"] = info["lng"] if info else ""
        row["geocode_method"] = method
        row["kakao_gu"] = info.get("gu", "") if info else ""
        row["kakao_dong"] = info.get("dong", "") if info else ""
        row["kakao_addr"] = info.get("addr", "") if info else ""
        row["kakao_road"] = info.get("road", "") if info else ""
        if info:
            n_ok += 1
        else:
            n_fail += 1
        out.append(row)
        if i % 50 == 0 or i == len(rows):
            print(f"  [{i}/{len(rows)}] ok={n_ok} fail={n_fail}")
            save_cache(cache)

    save_cache(cache)
    with open(DST, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(out)
    print(f"\n✅ ok={n_ok} fail={n_fail} / total={len(rows)} → {DST}")

if __name__ == "__main__":
    main()
