#!/usr/bin/env python3
"""
누적 랭킹의 중복 등재 병합 + 안정 식별자 부여.

같은 가게가 장부 표기 변형("무교소호정"/"소호정"/"(주)소호정")으로
랭킹에 여러 번 오른다. 16이 붙인 카카오 place id(kakaoId)가 같으면
같은 가게이므로 병합한다 — 이름 우연 일치는 병합하지 않는다
(카카오 앵커 없는 항목은 그대로 둔다).

병합 규칙: 방문·금액은 합산(정확), 부서수는 최댓값(원장 없이 합집합
불가 — 보수적 하한), 표시 필드는 방문 많은 쪽 기준. 병합 후
이용횟수순으로 재랭킹한다.

안정 식별자 id: kakaoId → 구글 placeId → 이름|지역|주소 해시 순.
댓글이 이 id에 묶이므로 주간 갱신으로 순위가 바뀌어도 안 떠내려간다.

입출력: src/data/restaurants.json (in-place, 06→16 다음에 실행)
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESTAURANTS = ROOT / "src" / "data" / "restaurants.json"


def stable_id(r: dict, used: set) -> str:
    for cand in (r.get("kakaoId"), r.get("placeId")):
        if cand and cand not in used:
            return cand
    basis = f"{r.get('ledgerName') or r['name']}|{r.get('region','')}|{r.get('address','')}"
    h = hashlib.sha1(basis.encode()).hexdigest()[:12]
    while h in used:
        h = hashlib.sha1(h.encode()).hexdigest()[:12]
    return h


def merge_group(group: list[dict]) -> dict:
    group.sort(key=lambda r: (-r["visits"], r["rank"]))
    base = dict(group[0])
    base["visits"] = sum(r["visits"] for r in group)
    base["totalAmount"] = sum(r["totalAmount"] for r in group)
    base["avgAmount"] = round(base["totalAmount"] / base["visits"])
    base["deptCount"] = max(r["deptCount"] for r in group)
    return base


def main() -> None:
    restaurants = json.loads(RESTAURANTS.read_text(encoding="utf-8"))

    by_kakao: dict[str, list[dict]] = defaultdict(list)
    rest = []
    for r in restaurants:
        if r.get("kakaoId"):
            by_kakao[r["kakaoId"]].append(r)
        else:
            rest.append(r)

    merged = []
    n_groups = n_absorbed = 0
    for kid, group in by_kakao.items():
        if len(group) == 1:
            merged.append(group[0])
            continue
        n_groups += 1
        n_absorbed += len(group) - 1
        m = merge_group(group)
        merged.append(m)
        names = " + ".join(f"{r.get('ledgerName') or r['name']}({r['visits']})" for r in group)
        if n_groups <= 30:
            print(f"  {m['name']} ← {names}")

    out = merged + rest
    out.sort(key=lambda r: (-r["visits"], -r["totalAmount"], r["name"]))
    used: set = set()
    for i, r in enumerate(out, 1):
        r["rank"] = i
        r["id"] = stable_id(r, used)
        used.add(r["id"])

    RESTAURANTS.write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"\n{len(restaurants)} → {len(out)}곳 "
        f"(병합 {n_groups}묶음, 흡수 {n_absorbed}건) → {RESTAURANTS.relative_to(ROOT)}"
    )


if __name__ == "__main__":
    main()
