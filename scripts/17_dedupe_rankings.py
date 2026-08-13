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
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESTAURANTS = ROOT / "src" / "data" / "restaurants.json"

# 명백한 비식당 지출처 — 랭킹에서 제외. 카페테리아·구내식당은 공무원이
# 실제 식사하는 곳이라 유지한다. (name과 ledgerName 양쪽 검사)
# 주의: '문구'는 동대문구청점에, 부분문자열 '마트'는 마트 입점 식당
# (치즈앤도우 롯데마트점)에 오발동해서 넣지 않는다. 마트는 아래
# _is_mart의 첫 토큰 규칙으로만 거른다.
NONFOOD = re.compile(
    r"쇼핑|사무실|주유소|다이소|쿠팡|약국|세븐일레븐|이마트24|미니스톱|GS25"
)


def _is_mart(name: str) -> bool:
    """가게 자체가 마트인 경우만: 첫 토큰이 '○○마트'로 끝난다.
    '치즈앤도우 롯데마트 금천점'(마트 안 식당)은 첫 토큰이 식당명이라 통과."""
    tokens = (name or "").split()
    return bool(tokens) and tokens[0].endswith("마트")


def _is_nonfood(r: dict) -> bool:
    # 표시명 기준만 검사한다 — 장부명이 "하나로마트창동점"이어도
    # 카카오가 식당으로 교정한 이름(채선당…)이면 식당이 맞다.
    name = r["name"]
    return bool(NONFOOD.search(name)) or _is_mart(name)


def _norm(s: str) -> str:
    s = re.sub(r"\(주\)|㈜|주식회사|\(유\)", "", s or "")
    s = re.sub(r"\s*[(（][^)）]*[)）]?\s*$", "", s)
    return re.sub(r"\s+", "", s)


def _name_similar(a: str, b: str) -> bool:
    na, nb = _norm(a), _norm(b)
    if not na or not nb:
        return False
    if na in nb or nb in na:
        return True
    A = {na[i : i + 2] for i in range(len(na) - 1)} or {na}
    B = {nb[i : i + 2] for i in range(len(nb) - 1)} or {nb}
    return len(A & B) / len(A | B) >= 0.5


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

    # ── 2차: 같은 구글 placeId + 이름 유사 병합 ──
    # 카카오 앵커가 없어 1차에서 못 합친 중복(삼우정×2 등)을 잡는다.
    # placeId는 건물 단위로 오염될 수 있어("강가"+"늘솜"이 같은 id)
    # 이름 유사를 함께 요구하고, 서로 다른 kakaoId가 섞이면 다른
    # 가게이므로 병합하지 않는다.
    by_pid: dict[str, list[dict]] = defaultdict(list)
    for r in out:
        if r.get("placeId"):
            by_pid[r["placeId"]].append(r)
    absorbed_ids = set()
    n_pid_groups = 0
    for pid, group in by_pid.items():
        if len(group) < 2:
            continue
        group = sorted(group, key=lambda r: -r["visits"])
        used = set()
        for i, base in enumerate(group):
            if id(base) in used or id(base) in absorbed_ids:
                continue
            cluster = [base]
            for other in group[i + 1 :]:
                if id(other) in used:
                    continue
                if not _name_similar(base["name"], other["name"]):
                    continue
                kakaos = {
                    r["kakaoId"] for r in cluster + [other] if r.get("kakaoId")
                }
                if len(kakaos) > 1:
                    continue  # 카카오 앵커 충돌 — 같은 건물의 다른 가게
                cluster.append(other)
                used.add(id(other))
            if len(cluster) > 1:
                n_pid_groups += 1
                n_absorbed += len(cluster) - 1
                m = merge_group(cluster)
                out[out.index(base)] = m
                for other in cluster[1:]:
                    absorbed_ids.add(id(other))
                names = " + ".join(
                    f"{r.get('ledgerName') or r['name']}({r['visits']})" for r in cluster
                )
                print(f"  [pid] {m['name']} ← {names}")
    out = [r for r in out if id(r) not in absorbed_ids]
    n_groups += n_pid_groups

    # ── 3차: 명백한 비식당 제외 ──
    dropped = [r for r in out if _is_nonfood(r)]
    out = [r for r in out if r not in dropped]
    for r in sorted(dropped, key=lambda r: r["rank"])[:20]:
        print(f"  [제외] #{r['rank']} {r['name']} ({r['visits']}회)")
    if len(dropped) > 20:
        print(f"  [제외] … 외 {len(dropped) - 20}건")
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
