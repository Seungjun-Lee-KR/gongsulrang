#!/usr/bin/env python3
"""
정규화 v3: 카카오 장소 매칭으로 클러스터를 실제 가게(place id)에 앵커링.

13_momentum_bonchong.py의 v2 클러스터(이름+주소 휴리스틱)가 입력이다.
총 방문 10회 이상 클러스터마다:
  1. 대표 주소를 지오코딩해 좌표를 얻고 (Kakao 주소 검색)
  2. 좌표 반경 300m에서 대표 이름으로 키워드 검색 (Kakao 키워드 검색)
     — 실패하면 지점 접미("○○점")를 뗀 핵심 이름으로 재시도
  3. 후보 중 도로명주소 일치 또는 근거리+이름 유사를 채택

같은 place id로 앵커링된 클러스터는 병합된다. 이것이 이름 휴리스틱이
못 푸는 세 가지를 푼다: 약어("SFC"↔"서울파이낸스센터"), 운영사
리브랜딩(한화푸드테크→더테이스터블), 서로 포함관계가 아닌 표기 변형.
장부상 법인명("주식회사 에스씨케이컴퍼니"=스타벅스)은 카카오 검색으로도
안 잡히므로 미해결로 남기고 unmatched로 표시한다 — 조용히 틀린 이름을
보여주느니 정직하게 장부명을 보여준다.

필요: .env.local의 KAKAO_REST_API_KEY, .venv (requests, python-dotenv)
캐시: data/output/.kakao_place_cache.json (재실행 시 API 호출 없음)
출력: data/output/momentum_bonchong.json (13의 출력을 kakao 필드로 보강)
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env.local")
KEY = os.getenv("KAKAO_REST_API_KEY")
if not KEY:
    sys.exit("KAKAO_REST_API_KEY가 .env.local에 없습니다.")

_spec = importlib.util.spec_from_file_location(
    "momentum", ROOT / "scripts" / "13_momentum_bonchong.py"
)
momentum = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(momentum)

CACHE_PATH = ROOT / "data" / "output" / ".kakao_place_cache.json"
OUT = ROOT / "data" / "output" / "momentum_bonchong.json"
FRONTEND_OUT = ROOT / "src" / "data" / "momentum.json"  # /trending 페이지가 임포트

MIN_TOTAL_VISITS = 10  # 이 미만 클러스터는 랭킹에 못 들므로 매칭 생략
RATE = 0.12  # 초당 ~8회
RADIUS = 300  # m

_HEADERS = {"Authorization": f"KakaoAK {KEY}"}
_cache: dict = json.loads(CACHE_PATH.read_text()) if CACHE_PATH.exists() else {}
_calls = 0


def _get(url: str, params: dict, cache_key: str) -> list[dict]:
    global _calls
    if cache_key in _cache:
        return _cache[cache_key]
    time.sleep(RATE)
    _calls += 1
    try:
        r = requests.get(url, headers=_HEADERS, params=params, timeout=10)
        r.raise_for_status()
        docs = r.json().get("documents", [])
    except requests.RequestException as e:
        print(f"  ! API 실패({cache_key[:40]}…): {e}", file=sys.stderr)
        return []  # 실패는 캐시하지 않음 — 재실행 때 재시도
    _cache[cache_key] = docs
    if _calls % 200 == 0:
        CACHE_PATH.write_text(json.dumps(_cache, ensure_ascii=False))
        print(f"  … API {_calls}회, 캐시 저장", file=sys.stderr)
    return docs


def geocode(addr: str) -> tuple[str, str] | None:
    docs = _get(
        "https://dapi.kakao.com/v2/local/search/address.json",
        {"query": f"서울 {addr}"},
        f"addr:{addr}",
    )
    return (docs[0]["x"], docs[0]["y"]) if docs else None


def keyword_near(query: str, x: str, y: str) -> list[dict]:
    return _get(
        "https://dapi.kakao.com/v2/local/search/keyword.json",
        {"query": query, "x": x, "y": y, "radius": RADIUS, "size": 10},
        f"kw:{query}|{x[:9]}|{y[:9]}",
    )


_CORP_TOKENS = re.compile(r"(\(주\)|㈜|주식회사)\s*")


def query_names(display: str) -> list[str]:
    """검색 쿼리 후보: 법인 접두 제거본 → 지점 접미('○○점') 제거본."""
    base = _CORP_TOKENS.sub("", display).strip()
    out = [base]
    tokens = base.split()
    if len(tokens) > 1 and tokens[-1].endswith(("점", "지점")):
        out.append(" ".join(tokens[:-1]))
    return out


def _bigrams(s: str) -> set:
    s = momentum.normalize(s)
    return {s[i : i + 2] for i in range(len(s) - 1)} if len(s) > 1 else {s}


def similarity(a: str, b: str) -> float:
    na, nb = momentum.normalize(a), momentum.normalize(b)
    if na and nb and (na in nb or nb in na):
        return 1.0
    A, B = _bigrams(a), _bigrams(b)
    return len(A & B) / len(A | B) if A | B else 0.0


def pick_place(display: str, addr: str, x: str, y: str) -> dict | None:
    """검색 결과에서 이 클러스터의 가게를 고른다. 확신 없으면 None."""
    for q in query_names(display):
        docs = keyword_near(q, x, y)
        # 음식점/카페 우선 — 같은 이름의 사무실/학원 오매칭 방지
        food = [d for d in docs if d.get("category_group_code") in ("FD6", "CE7")]
        for d in food or docs:
            sim = similarity(display, d["place_name"])
            addr_hit = addr and addr in d.get("road_address_name", "")
            near = d.get("distance") and int(d["distance"]) <= 150
            # 같은 건물이면 이름 유사가 조금만 있어도, 아니면 근거리+강한 유사
            if (addr_hit and sim >= 0.25) or (near and sim >= 0.5):
                return d
    return None


def main() -> None:
    rows = momentum.load_rows()
    C = momentum.build_clusters(rows)

    totals = {k: sum(c.values()) for k, c in C["qv"].items()}
    targets = [k for k, t in totals.items() if t >= MIN_TOTAL_VISITS]
    targets.sort(key=lambda k: -totals[k])
    print(f"클러스터 {len(totals):,}곳 중 매칭 대상(방문≥{MIN_TOTAL_VISITS}) {len(targets):,}곳")

    place_of: dict = {}  # root → kakao doc
    unmatched = 0
    for i, root in enumerate(targets, 1):
        name = momentum.display_name(C, root)
        addr_counter = C["addrs"][root]
        addr = addr_counter.most_common(1)[0][0] if addr_counter else None
        doc = None
        if addr:
            xy = geocode(addr)
            if xy:
                doc = pick_place(name, addr, *xy)
        if doc:
            place_of[root] = doc
        else:
            unmatched += 1
        if i % 200 == 0:
            print(f"  {i}/{len(targets)} … 매칭 {len(place_of)} / 실패 {unmatched}")

    CACHE_PATH.write_text(json.dumps(_cache, ensure_ascii=False))

    # ── place id가 같은 클러스터 병합 ──
    by_place: dict[str, list] = defaultdict(list)
    for root, doc in place_of.items():
        by_place[doc["id"]].append(root)
    merges = {pid: roots for pid, roots in by_place.items() if len(roots) > 1}

    canon: dict = {}  # root → 병합 후 대표 root
    for roots in by_place.values():
        rep = max(roots, key=lambda r: totals[r])
        for r in roots:
            canon[r] = rep

    M = {
        "qv": defaultdict(Counter),
        "display": defaultdict(Counter),
        "name_keys": defaultdict(Counter),
        "recent_depts": defaultdict(set),
        "amounts": defaultdict(list),
        "addrs": defaultdict(Counter),
        "name_cluster": defaultdict(Counter),
    }
    for root in C["qv"]:
        dst = canon.get(root, root)
        M["qv"][dst].update(C["qv"][root])
        M["display"][dst].update(C["display"][root])
        M["name_keys"][dst].update(C["name_keys"][root])
        M["recent_depts"][dst] |= C["recent_depts"][root]
        M["amounts"][dst].extend(C["amounts"][root])
        M["addrs"][dst].update(C["addrs"][root])
    for nk, roots in C["name_cluster"].items():
        for root, cnt in roots.items():
            M["name_cluster"][nk][canon.get(root, root)] += cnt

    def decorate(key, e: dict) -> None:
        doc = place_of.get(key)
        if doc:
            e["name"] = doc["place_name"]  # 소비자용 상호로 교체
            e["kakao"] = {
                "id": doc["id"],
                "category": doc.get("category_name", "").split(" > ")[-1],
                "address": doc.get("road_address_name") or doc.get("address_name", ""),
                "url": doc.get("place_url", ""),
                "lat": float(doc["y"]),
                "lng": float(doc["x"]),
            }
        else:
            e["kakao"] = None  # 장부명 그대로 — 조용한 오매칭보다 낫다

    result = momentum.make_result(
        M,
        len(rows),
        decorate=decorate,
        extra_stats={
            "kakaoMatched": len(place_of),
            "kakaoUnmatched": unmatched,
            "kakaoMerged": sum(len(r) - 1 for r in merges.values()),
        },
    )
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    FRONTEND_OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n매칭 {len(place_of)}/{len(targets)} ({len(place_of)/len(targets):.0%})"
          f" · API {_calls}회 · place 병합 {len(merges)}묶음")
    if merges:
        print("\n=== place id 병합 내역 (상위 15) ===")
        shown = sorted(merges.values(), key=lambda rs: -sum(totals[r] for r in rs))[:15]
        for roots in shown:
            doc = place_of[roots[0]]
            members = " + ".join(f"{momentum.display_name(C, r)}({totals[r]})" for r in roots)
            print(f"  {doc['place_name']} ← {members}")
    momentum.show_result(result, OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
