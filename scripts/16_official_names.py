#!/usr/bin/env python3
"""
카드 명세서상 상호 → 실제 간판 상호 보정.

장부의 가맹점명은 사업자 등록명이라 간판과 다른 경우가 있다
("(주)뚜리삼" = 산채향, "우아한형제들" = 옥수동 묵은지 김치찜).
구글 display_name도 같은 등록명을 따라가는 경우가 많아 못 믿는다
(게다가 '작약'→'14', '(주)강가'→'서울파이낸스센터' 같은 오염도 있다).

두 단계로 실제 상호를 찾는다:
  1. 전화번호 조인(최강 신호): 구글 enrich의 전화와 좌표 반경 100m
     카카오 음식점(FD6)·카페(CE7)의 전화가 정확히 일치하면 그 가게다.
     이름이 완전히 달라도 잡는다 — 뚜리삼 옆집(02-779-2959)처럼
     한 자리 차이가 있으므로 정확 일치만 인정.
  2. 이름 검색: 장부명(법인 접두 제거)·구글 display_name을 쿼리로
     좌표 반경 검색 → 음식점/카페 + 150m 이내 + 유사도 0.5 이상.

채택된 카카오 place_name이 기존 이름과 다르면 name을 교체하고
원래 장부명을 ledgerName에 보존한다. 확신 없으면 건드리지 않는다.

필요: .env.local의 KAKAO_REST_API_KEY (캐시는 14와 공유)
입출력: src/data/restaurants.json (in-place), data/output/places_enrich.json
"""
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


m14 = _load("14_kakao_place_match")  # _get/similarity/query_names + 캐시 재사용

RESTAURANTS = ROOT / "src" / "data" / "restaurants.json"
ENRICH = ROOT / "data" / "output" / "places_enrich.json"

PHONE_RADIUS = 100  # m — 전화 조인용 반경 카테고리 검색
NAME_RADIUS = 300  # m — 이름 검색 반경
NAME_MAX_DIST = 150  # m — 이름 매칭 채택 거리


def norm_phone(s: str | None) -> str | None:
    d = re.sub(r"\D", "", s or "")
    if d.startswith("82"):
        d = "0" + d[2:]
    return d if len(d) >= 9 else None


def category_near(code: str, x: float, y: float) -> list[dict]:
    return m14._get(
        "https://dapi.kakao.com/v2/local/search/category.json",
        {
            "category_group_code": code,
            "x": x,
            "y": y,
            "radius": PHONE_RADIUS,
            "size": 15,
            "sort": "distance",
        },
        f"cat:{code}|{x:.6f}|{y:.6f}|{PHONE_RADIUS}",
    )


def keyword_near(q: str, x: float, y: float) -> list[dict]:
    return m14._get(
        "https://dapi.kakao.com/v2/local/search/keyword.json",
        {"query": q, "x": x, "y": y, "radius": NAME_RADIUS, "size": 10},
        f"kw:{q}|{str(x)[:9]}|{str(y)[:9]}",
    )


def by_phone(phone: str, x: float, y: float) -> dict | None:
    for code in ("FD6", "CE7"):
        for p in category_near(code, x, y):
            if norm_phone(p.get("phone")) == phone:
                return p
    return None


def by_name(queries: list[str], x: float, y: float) -> dict | None:
    for q in queries:
        if not q:
            continue
        for p in keyword_near(q, x, y):
            if p.get("category_group_code") not in ("FD6", "CE7"):
                continue
            if not p.get("distance") or int(p["distance"]) > NAME_MAX_DIST:
                continue
            if m14.similarity(q, p["place_name"]) >= 0.5:
                return p
    return None


def main() -> None:
    restaurants = json.loads(RESTAURANTS.read_text(encoding="utf-8"))
    enrich = json.loads(ENRICH.read_text(encoding="utf-8"))
    phone_by_pid = {}
    gname_by_pid = {}
    for v in enrich.values():
        if v.get("place_id"):
            phone_by_pid[v["place_id"]] = norm_phone(v.get("phone"))
            gname_by_pid[v["place_id"]] = (v.get("display_name") or "").strip()

    changed = phone_hits = name_hits = 0
    for i, r in enumerate(restaurants, 1):
        if r.get("lat") is None or r.get("lng") is None:
            continue
        x, y = r["lng"], r["lat"]
        pid = r.get("placeId")
        ledger = r.get("ledgerName") or r["name"]

        doc = None
        phone = phone_by_pid.get(pid)
        if phone:
            doc = by_phone(phone, x, y)
            if doc:
                phone_hits += 1
        if not doc:
            queries = list(m14.query_names(ledger))
            gname = gname_by_pid.get(pid, "")
            # 구글 이름은 한글 2자 이상 + 장부명과 다를 때만 보조 쿼리로
            if re.search(r"[가-힣]{2}", gname) and gname not in queries:
                queries.append(gname)
            doc = by_name(queries, x, y)
            if doc:
                name_hits += 1
        if not doc:
            continue

        # 카카오 place id는 중복 병합(17)과 모멘텀 연결의 안정 키
        r["kakaoId"] = doc["id"]
        official = doc["place_name"].strip()
        if official and official != r["name"]:
            if "ledgerName" not in r:
                r["ledgerName"] = r["name"]
            r["name"] = official
            changed += 1
            if changed <= 100:
                print(f"  {r['rank']:4d} {r['ledgerName']!r} → {official!r}")
        if i % 300 == 0:
            print(f"  … {i}/{len(restaurants)} (변경 {changed})")

    m14.CACHE_PATH.write_text(json.dumps(m14._cache, ensure_ascii=False))
    RESTAURANTS.write_text(
        json.dumps(restaurants, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"\n{len(restaurants)}곳 중 이름 교체 {changed}곳 "
        f"(전화 조인 {phone_hits}, 이름 검색 {name_hits}) → {RESTAURANTS.relative_to(ROOT)}"
    )


if __name__ == "__main__":
    main()
