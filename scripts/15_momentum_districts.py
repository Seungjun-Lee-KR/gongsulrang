#!/usr/bin/env python3
"""
자치구 업무추진비 기반 모멘텀 랭킹 — 13/14의 파이프라인을 25개 구에 적용.

구별 차이 때문에 본청 파이프라인을 그대로 못 쓴다:
  · 주소 컬럼이 대부분 비어 있다(금천·관악만 예외) → 주소 지오코딩 대신
    구 중심좌표 + 반경 10km 키워드 검색으로 카카오 장소를 찾고,
    결과 주소가 "서울 + 해당 구"인지로 검증한다. 동명 다지점이 모호하면
    정직하게 미매칭으로 남긴다(장부명 배지).
  · 데이터 규모가 본청의 1/4~1/10 → 후보 필터를 최근 8회·2개 부서,
    스테디셀러를 전 분기 3회 이상으로 낮춘다.
  · 수집 시작 시점이 구마다 다르다 → 분기별 50건 이상이 시작되는
    지점부터를 그 구의 분기 축으로 쓴다. 전년 동분기(base) 표본이
    500건 미만인 구(은평·서대문)는 모멘텀 산출이 무의미해 제외한다.

필요: .env.local의 KAKAO_REST_API_KEY, .venv
캐시: data/output/.kakao_place_cache.json (14와 공유)
출력: data/output/momentum_districts.json + src/data/momentum-districts.json
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


m13 = _load("13_momentum_bonchong")
m14 = _load("14_kakao_place_match")  # KAKAO_REST_API_KEY 필요

OUT = ROOT / "data" / "output" / "momentum_districts.json"
FRONTEND_OUT = ROOT / "src" / "data" / "momentum-districts.json"

DISTRICTS = [  # (csv 접두, 한글 구명)
    ("ddm", "동대문구"), ("dobong", "도봉구"), ("dongjak", "동작구"),
    ("ep", "은평구"), ("gangbuk", "강북구"), ("gangdong", "강동구"),
    ("gangnam", "강남구"), ("gangseo", "강서구"), ("geumcheon", "금천구"),
    ("guro", "구로구"), ("gwanak", "관악구"), ("gwangjin", "광진구"),
    ("jongno", "종로구"), ("junggu", "중구"), ("jungnang", "중랑구"),
    ("mapo", "마포구"), ("nowon", "노원구"), ("sb", "성북구"),
    ("sdm", "서대문구"), ("seocho", "서초구"), ("seongdong", "성동구"),
    ("songpa", "송파구"), ("yangcheon", "양천구"), ("ydp", "영등포구"),
    ("yongsan", "용산구"),
]

# 자치구 장부에 흔한 비식당 지출처 — 13의 NONFOOD에 얹는다
# (본청 결과를 안 바꾸려고 13 원본 대신 여기서 행을 걸러낸다)
DISTRICT_NONFOOD = (
    "마트", "쿠팡", "다이소", "문구", "화원", "꽃집", "약국", "주유소",
    # 결제대행·배달 플랫폼 — 방문할 수 있는 "집"이 아니다
    "네이버파이낸셜", "네이버페이", "카카오페이", "배달의민족", "우아한형제들", "요기요",
)

# 수집기 컬럼 밀림으로 식당명 자리에 들어온 쓰레기: 시간("12:14", "12시"),
# 순수 숫자, "해당없음", 대시. 강동구는 이런 행이 전체의 65%다.
_JUNK_NAME = re.compile(r"^\d{1,2}[:시]\d{0,2}$|^\d+$|^해당\s*없|^-+$|^\d{4}[-./]")

# 식당명 꼬리 괄호에 든 도로명주소(동대문구 패턴: "미래회관 ( 고산자로32길 78)")
_PAREN = re.compile(r"[(（]([^)）]+)[)）]")
_ROADISH = re.compile(r"[가-힣A-Za-z0-9·]+(?:로|길)\s*\d+(?:-\d+)?")
# 표시명 꼬리의 생주소(" 서울 동대문구 …") — 앞뒤 공백을 요구해
# "서울식당"·"미스터서울" 같은 진짜 상호는 건드리지 않는다
_RAW_ADDR_TAIL = re.compile(r"\s+(서울특별시|서울시|서울)\s.*$")

MIN_TOTAL_VISITS = 10  # 이 미만 클러스터는 랭킹에 못 들므로 매칭 생략
MIN_BASE_ROWS = 500  # 전년 동분기 표본이 이보다 적으면 구 자체를 제외
MIN_QUARTER_ROWS = 500  # 분기 축 시작점: 수집이 본궤도에 오른 첫 분기부터
GU_RADIUS = 10000  # m — 구 중심에서 구 전역을 덮는 반경


def addr_from_name(raw_name: str, gu: str) -> str:
    """식당명 괄호 속 도로명주소를 주소 컬럼으로 승격 — 13의 (이름, 주소)
    클러스터링과 14의 지오코딩+반경 300m 정밀 매칭 경로가 살아난다."""
    for grp in _PAREN.findall(raw_name):
        m = _ROADISH.search(grp)
        if m:
            return grp.strip() if gu in grp else f"{gu} {m.group(0)}"
    return ""


def keyword_in_gu(query: str, x: str, y: str, gu: str) -> list[dict]:
    return m14._get(
        "https://dapi.kakao.com/v2/local/search/keyword.json",
        {"query": query, "x": x, "y": y, "radius": GU_RADIUS, "size": 15},
        f"kwg:{query}|{gu}",
    )


def pick_place_in_gu(display: str, gu: str, x: str, y: str) -> dict | None:
    """구 전역 검색에서 가게를 고른다. 주소가 없으니 이름 유사가 유일한
    근거 — 임계를 0.5로 올리고, 동명 후보가 여럿이면(다지점 프랜차이즈)
    지점을 특정할 수 없으므로 포기한다."""
    for q in m14.query_names(display):
        docs = keyword_in_gu(q, x, y, gu)
        food = [d for d in docs if d.get("category_group_code") in ("FD6", "CE7")]
        cands = []
        for d in food or docs:
            addr = d.get("road_address_name") or d.get("address_name", "")
            if "서울" not in addr or gu not in addr:
                continue
            sim = m14.similarity(display, d["place_name"])
            if sim >= 0.5:
                cands.append((sim, d))
        if not cands:
            continue
        cands.sort(key=lambda t: -t[0])
        if len(cands) == 1:
            return cands[0][1]
        exact = [d for s, d in cands if s >= 1.0]
        return exact[0] if len(exact) == 1 else None
    return None


def district_quarters(rows: list[dict]) -> tuple[list[str], int]:
    """이 구의 분기 축(수집이 안정된 시점부터)과 base 표본 수."""
    qc = Counter()
    for r in rows:
        q = m13.quarter_of((r.get("사용일") or "").strip())
        if q:
            qc[q] += 1
    base_rows = sum(qc[q] for q in m13.BASE)
    start = next((i for i, q in enumerate(m13.QUARTERS) if qc[q] >= MIN_QUARTER_ROWS), None)
    return (m13.QUARTERS[start:] if start is not None else [], base_rows)


def run_district(slug: str, gu: str) -> dict | None:
    csv_path = ROOT / "data" / "output" / f"{slug}_expense_raw.csv"
    rows = []
    for r in m13.load_rows(csv_path):
        name = (r.get("식당명") or "").strip()
        if _JUNK_NAME.match(name):
            continue
        if any(k in m13.normalize(name) for k in DISTRICT_NONFOOD):
            continue
        if not (r.get("주소") or "").strip():
            r["주소"] = addr_from_name(name, gu)
        rows.append(r)
    quarters, base_rows = district_quarters(rows)
    if base_rows < MIN_BASE_ROWS:
        print(f"— {gu}: 전년 동분기 표본 {base_rows}건 < {MIN_BASE_ROWS} → 제외")
        return None

    C = m13.build_clusters(rows)
    totals = {k: sum(c.values()) for k, c in C["qv"].items()}
    targets = sorted(
        (k for k, t in totals.items() if t >= MIN_TOTAL_VISITS),
        key=lambda k: -totals[k],
    )

    center = m14.geocode(gu)
    if not center:
        sys.exit(f"{gu}: 구 중심 지오코딩 실패")

    place_of: dict = {}
    for root in targets:
        # 표시명의 꼬리 괄호(주소·층수)는 검색 쿼리를 망치므로 뗀다
        display = m13._PAREN_TAIL.sub("", m13.display_name(C, root)).strip()
        doc = None
        addrs = C["addrs"][root]
        if addrs:  # 금천·관악만 주소가 있다 — 본청과 같은 정밀 매칭 경로
            addr = addrs.most_common(1)[0][0]
            xy = m14.geocode(addr)
            if xy:
                doc = m14.pick_place(display, addr, *xy)
        if not doc:
            doc = pick_place_in_gu(display, gu, *center)
        if doc:
            place_of[root] = doc

    M, _, merges = m14.merge_by_place(C, place_of, totals)

    base_decorate = m14.kakao_decorate(place_of)

    def decorate(key, e: dict) -> None:
        base_decorate(key, e)
        if not e["kakao"]:  # 미매칭 장부명에서도 꼬리 괄호·생주소는 지운다
            cleaned = m13._PAREN_TAIL.sub("", e["name"]).strip()
            cleaned = _RAW_ADDR_TAIL.sub("", cleaned).strip()
            e["name"] = cleaned or e["name"]

    result = m13.make_result(
        M,
        len(rows),
        decorate=decorate,
        extra_stats={
            "kakaoMatched": len(place_of),
            "kakaoUnmatched": len(targets) - len(place_of),
            "kakaoMerged": sum(len(r) - 1 for r in merges.values()),
        },
        quarters=quarters,
        source=f"{gu} 업무추진비",
        min_recent=8,
        min_depts=2,
        steady_min=3,
    )
    result["slug"] = slug
    result["name"] = gu
    print(
        f"✓ {gu}: 거래 {len(rows):,} / 분기 {len(quarters)} / "
        f"매칭 {len(place_of)}/{len(targets)} ({len(place_of) / max(len(targets), 1):.0%}) / "
        f"뜨는 집 {len(result['rising'])} · 신규 {len(result['newcomers'])} · "
        f"스테디 {len(result['steady'])}"
    )
    return result


def main() -> None:
    districts = []
    for slug, gu in DISTRICTS:
        r = run_district(slug, gu)
        if r:
            districts.append(r)
    m14.CACHE_PATH.write_text(json.dumps(m14._cache, ensure_ascii=False))

    districts.sort(key=lambda d: d["name"])
    payload = {"districts": districts}
    for path in (OUT, FRONTEND_OUT):
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{len(districts)}개 구 → {OUT.relative_to(ROOT)}, {FRONTEND_OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
