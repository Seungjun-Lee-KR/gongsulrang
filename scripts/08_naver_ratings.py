"""
8단계: TOP 300 식당에 네이버 평점/리뷰수 비공식 스크래핑 (개선판)

- 입력: output/gongsulrang_ranking_seoul_2024_geo.csv (상위 N개)
- 출력: output/naver_ratings.json — {"{식당명}|{주소}": {...}}
- 캐시: output/.naver_cache.json

검색: https://search.naver.com/search.naver?query={식당명} {지역|주소토큰}
파싱: 별점, 방문자 리뷰, 블로그 리뷰, place_id, 매칭된 name
검증: 매칭된 name이 입력 name과 유사해야 채택 (bare-name fallback 제거)

주의: 비공식 경로. 요청 간 3초 간격. 깨지면 endpoint 재확인 필요.
"""

import os as _os
from pathlib import Path as _Path
_os.chdir(_Path(__file__).resolve().parent.parent)
import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.parse

import requests

SRC = "data/output/gongsulrang_ranking_seoul_2024_geo.csv"
OUT_JSON = "data/output/naver_ratings.json"
CACHE = "data/output/.naver_cache.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
}
SLEEP = 3.0


def cache_load():
    if os.path.exists(CACHE):
        return json.load(open(CACHE, encoding="utf-8"))
    return {}


def cache_save(c):
    json.dump(c, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)


RE_RATING = re.compile(r"별점</span>([\d.]+)")
RE_VISITOR_REVIEW = re.compile(r"방문자\s*리뷰\s*([\d,]+)")
RE_BLOG_REVIEW = re.compile(r"블로그\s*리뷰\s*([\d,]+)")
# 첫 번째 PLACE_POI 블록에서 이름과 place_id 추출 (가장 상단 결과 = 선택된 카드)
RE_PLACE_POI = re.compile(r"/directions/[^\"]*?,([^,/\"]+),(\d+),PLACE_POI")


def normalize_name(s: str) -> str:
    s = s.strip()
    s = re.sub(r"\s+", "", s)
    # 흔한 말단 수식어 제거 (branches)
    s = re.sub(r"(본점|직영점|직영|총본점|신관|구관|\d+호점)$", "", s)
    return s


def names_match(input_name: str, matched_name: str) -> bool:
    a = normalize_name(input_name)
    b = normalize_name(matched_name)
    if not a or not b:
        return False
    if a == b:
        return True
    # 한쪽이 다른 쪽 포함: 삼우정 ⊆ 삼우정본점
    if a in b or b in a:
        return True
    return False


def parse_card(html: str):
    """search.naver.com 결과에서 최상단 place 카드 파싱."""
    m_poi = RE_PLACE_POI.search(html)
    if not m_poi:
        return None
    matched_name = urllib.parse.unquote(m_poi.group(1))
    pid = m_poi.group(2)

    # 별점/리뷰는 본 카드에 해당한다고 가정 (카드 블록 상단-하단 레이아웃)
    m_r = RE_RATING.search(html)
    m_v = RE_VISITOR_REVIEW.search(html)
    m_b = RE_BLOG_REVIEW.search(html)

    return {
        "place_id": pid,
        "matched_name": matched_name,
        "rating": float(m_r.group(1)) if m_r else None,
        "visitor_review_count": int(m_v.group(1).replace(",", "")) if m_v else None,
        "blog_review_count": int(m_b.group(1).replace(",", "")) if m_b else None,
    }


def fetch_search(query: str):
    url = f"https://search.naver.com/search.naver?query={urllib.parse.quote(query)}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
    except requests.RequestException as e:
        return None, f"req_err:{type(e).__name__}"
    if r.status_code != 200:
        return None, f"http_{r.status_code}"
    parsed = parse_card(r.text)
    if not parsed:
        return None, "no_card"
    return parsed, "ok"


def search(name: str, region: str, addr: str):
    """
    쿼리 전략 (bare-name fallback 없음):
    1) {name} {region}     예: '삼우정 중구'
    2) {name} {addr 첫2토큰}  예: '삼우정 중구 태평로2가'

    각 쿼리 결과에서 names_match 통과 + 별점 있으면 즉시 반환.
    """
    queries = []
    if region:
        queries.append(f"{name} {region}")
    if addr:
        addr_token = " ".join(addr.split()[:2])
        if addr_token and addr_token not in queries:
            queries.append(f"{name} {addr_token}")
    if not queries:
        queries.append(name)

    best = None  # names_match 통과했지만 별점 없는 케이스 보관
    for q in queries:
        parsed, status = fetch_search(q)
        if parsed and names_match(name, parsed["matched_name"]):
            parsed["query"] = q
            if parsed["rating"] is not None:
                return parsed, "ok"
            if best is None:
                best = parsed
        time.sleep(1.0)

    if best is not None:
        return best, "no_rating"
    return None, "no_match"


def enrich_row(row: dict, cache: dict):
    name = row["식당명"].strip()
    region = row.get("지역", "").strip()
    addr = row.get("주소", "").strip()
    key = f"{name}|{region}|{addr}"
    if key in cache:
        return cache[key]

    result, status = search(name, region, addr)
    if result is None:
        cache[key] = {"status": status}
    else:
        cache[key] = {"status": status, **result}
    return cache[key]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=300)
    ap.add_argument("--pilot", type=int, default=0)
    ap.add_argument("--reset-cache", action="store_true", help="캐시 무시")
    args = ap.parse_args()

    rows = list(csv.DictReader(open(SRC, encoding="utf-8-sig")))
    target = rows[: args.pilot or args.top]
    mode = "PILOT" if args.pilot else "FULL"
    print(f"[{mode}] 대상 {len(target)}건")

    cache = {} if args.reset_cache else cache_load()
    result = {}
    n_ok = n_nr = n_nm = n_err = 0

    for i, row in enumerate(target, 1):
        name = row["식당명"]
        region = row.get("지역", "")
        addr = row.get("주소", "")
        key = f"{name}|{region}|{addr}"
        try:
            e = enrich_row(row, cache)
        except Exception as ex:
            e = {"status": f"err:{type(ex).__name__}: {ex}"}
        result[key] = {"rank": int(row["순위"]), "name": name, **e}
        s = e.get("status", "")
        if s == "ok":
            n_ok += 1
        elif s == "no_rating":
            n_nr += 1
        elif s == "no_match":
            n_nm += 1
        else:
            n_err += 1
        if args.pilot:
            print(f"  [{i}] {name} [{row.get('지역','')}] → {e}")

        if i % 20 == 0 or i == len(target):
            cache_save(cache)
            if not args.pilot:
                with open(OUT_JSON, "w", encoding="utf-8") as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                print(f"  [{i}/{len(target)}] ok={n_ok} no_rating={n_nr} no_match={n_nm} err={n_err}")
        time.sleep(SLEEP)

    cache_save(cache)
    if not args.pilot:
        with open(OUT_JSON, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n✅ ok={n_ok} no_rating={n_nr} no_match={n_nm} err={n_err} / {len(target)} → {OUT_JSON}")
    else:
        print(f"\n[PILOT] ok={n_ok} no_rating={n_nr} no_match={n_nm} err={n_err} / {len(target)}")


if __name__ == "__main__":
    main()
