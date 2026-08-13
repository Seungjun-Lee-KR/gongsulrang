#!/usr/bin/env python3
"""
서울시 본청(業推) 데이터 기반 모멘텀 랭킹 프로토타입.

data/output/seoul_expense_raw.csv (2023Q1~) 를 분기별로 집계해
  - 🔥 뜨는 집: 최근 2분기 vs 전년 동분기(계절성 제거) 성장률
  - ⭐ 신규 진입: 전년 동분기 기록이 없는 새 식당
  - 🏛 스테디셀러: 전 분기 연속 등장 + 변동계수 최소
를 산출한다. 결과는 stdout 표 + data/output/momentum_bonchong.json.

핵심 난제는 식당명 정규화다. 같은 가게가 장부에 수십 가지 표기로
등장한다(법인명 접두, 붙은 주소, "나. 장소:" 류 쓰레기, 공백 차이).

정규화는 2단계다.
  v1: 이름 휴리스틱 — 쓰레기 접두/법인 접두/붙은 주소 제거, 공백 접기
  v2: (이름키, 주소키) 쌍 클러스터링 —
      · 같은 주소에서 한 이름이 다른 이름을 포함하면 같은 가게로 병합
        (장부상 개명 "(주)부자되세요 창고43 무교점" ↔ "창고43 무교점")
      · 같은 이름이라도 주소가 다르면 별개 지점으로 유지하고,
        지점명 없는 거래("창고43")는 자기 주소를 따라 지점에 귀속
주소키는 도로명주소의 (구, 도로명, 건물번호)만 취한다. 번호 없는
주소는 신뢰하지 않고 이름 쪽 다수 클러스터에 붙인다.
"""
from __future__ import annotations

import csv
import json
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "output" / "seoul_expense_raw.csv"
OUT = ROOT / "data" / "output" / "momentum_bonchong.json"


# "2026-03-05" 외에 자치구 장부의 "2025.2.", "2025/3/2", "20260219" 변형도 잡는다.
# 연도가 없는 표기("2.21.", "06-05")는 분기를 특정할 수 없어 버린다.
_DATE_HEAD = re.compile(r"^(20\d{2})[.\-/년\s]+(\d{1,2})\b")
_DATE_COMPACT = re.compile(r"^(20\d{2})(\d{2})\d{2}$")


def quarter_of(date: str) -> str | None:
    m = _DATE_HEAD.match(date) or _DATE_COMPACT.match(date)
    if not m:
        return None
    y, mo = int(m.group(1)), int(m.group(2))
    if y >= 2023 and 1 <= mo <= 12:
        return f"{y}-Q{(mo - 1) // 3 + 1}"
    return None


def load_rows(path: Path = RAW) -> list[dict]:
    # 일부 자치구 CSV에 NUL 바이트가 섞여 있어 csv 모듈이 죽는다 — 제거 후 파싱
    import io

    text = path.read_text(encoding="utf-8-sig", errors="replace").replace("\x00", "")
    return list(csv.DictReader(io.StringIO(text)))


def _quarter_seq(last: str) -> list[str]:
    seq = [f"{y}-Q{q}" for y in range(2023, int(last[:4]) + 1) for q in (1, 2, 3, 4)]
    return seq[: seq.index(last) + 1]


def detect_axis() -> tuple:
    """본청 데이터에서 분기 축을 도출 — 분기가 바뀌어도 상수 수정이 필요 없다.

    끝점은 '업로드가 충분히 찬'(분기 행수가 중앙값의 절반 이상) 마지막 분기.
    공개 데이터는 분기 종료 후 1~2달 걸쳐 올라오므로, 달력상 끝난 분기라도
    행수가 덜 찼으면 아직 축에 넣지 않는다.
    """
    fallback = (_quarter_seq("2026-Q1"), ("2025-Q4", "2026-Q1"), ("2024-Q4", "2025-Q1"))
    try:
        rows = load_rows()
    except OSError:
        return fallback
    qc = Counter()
    for r in rows:
        q = quarter_of(r.get("사용일") or "")
        if q:
            qc[q] += 1
    if not qc:
        return fallback
    cutoff = statistics.median(qc.values()) * 0.5
    filled = sorted(q for q, c in qc.items() if c >= cutoff)
    if not filled:
        return fallback
    quarters = _quarter_seq(filled[-1])
    if len(quarters) < 6:  # 전년 동분기 비교가 불가능한 축이면 고정값 유지
        return fallback
    return quarters, (quarters[-2], quarters[-1]), (quarters[-6], quarters[-5])


QUARTERS, RECENT, BASE = detect_axis()  # BASE: 전년 동분기 → 회식 시즌 등 계절성 상쇄

# 식당이 아닌 내부 시설/매점류
NONFOOD = (
    "간담회장", "매점", "카페테리아", "구내식당", "행복플러스",
    "편의점", "GS25", "CU", "세븐일레븐", "이마트24",
)

# 장부 쓰레기 접두사: "나 장 소:", "나. 장소:" 등
_JUNK_PREFIX = re.compile(r"^[가-핳]\s*[.)]?\s*장\s*소\s*[:：]\s*")
# 법인 접두: (주), ㈜, 주식회사, 주)
_CORP = re.compile(r"(\(주\)|㈜|주식회사|(?<![가-힣])주\))\s*")
# 이름 뒤에 붙은 주소/부가정보: 구분자 이후 또는 "(서울…" / " 서울 …" 부터 잘라냄
_ADDR_TAIL = re.compile(r"\s*[,/(（]?\s*(서울특별시|서울시|서울)\s*[^,]*.*$")
_SEP_TAIL = re.compile(r"\s*[,/].*$")
_PAREN_TAIL = re.compile(r"\s*[(（][^)）]*[)）]?\s*$")


def normalize(name: str) -> str:
    """장부 표기 변형을 하나의 키로 접는다."""
    s = name.strip()
    s = _JUNK_PREFIX.sub("", s)
    s = _CORP.sub("", s)
    s = _ADDR_TAIL.sub("", s)
    s = _SEP_TAIL.sub("", s)
    s = _PAREN_TAIL.sub("", s)
    s = re.sub(r"\s+", "", s)
    return s


# 인당 지출: 사용자 "문화시설과장 등 6명" / "과장 외 3명"에서 인원을 파싱.
# '외'는 명시된 사람을 제외한 수라 +1. 본청은 85%가 이 형식이다.
_HEADCOUNT = re.compile(r"(외\s*)?(\d{1,3})\s*명")
# 끼니 분류: 사용시간(본청 100%, 자치구 50~75%) 우선, 없으면 목적 키워드
_HOUR = re.compile(r"^(\d{1,2})[:시]")
_LUNCH_KW = ("오찬", "중식", "점심")
_DINNER_KW = ("만찬", "석식", "회식", "저녁")


def headcount_of(user: str) -> int | None:
    m = _HEADCOUNT.search(user)
    if not m:
        return None
    n = int(m.group(2)) + (1 if m.group(1) else 0)
    return n if 1 <= n <= 99 else None


def meal_of(time_str: str, purpose: str) -> str | None:
    m = _HOUR.match(time_str.strip())
    if m:
        h = int(m.group(1))
        if 11 <= h <= 14:
            return "lunch"
        if 17 <= h <= 23:
            return "dinner"
        return "other"
    if any(k in purpose for k in _LUNCH_KW):
        return "lunch"
    if any(k in purpose for k in _DINNER_KW):
        return "dinner"
    return None


# 도로명주소 → (구, 도로명, 건물번호). "서울 중구 무교로 21", "중구 무교로21",
# "서울시 중구 무교로 21 더익스체인지서울 2층" 이 모두 같은 키가 된다.
_ROAD = re.compile(r"([가-힣]+구)\s+([가-힣A-Za-z0-9·]+(?:로|길))\s*(\d+(?:-\d+)?)")


def addr_key(addr: str) -> str | None:
    m = _ROAD.search(addr)
    return f"{m.group(1)} {m.group(2)} {m.group(3)}" if m else None


class _UF:
    """경량 union-find."""

    def __init__(self):
        self.p: dict = {}

    def find(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[ra] = rb


def _contained(short: str, long: str) -> bool:
    """가게명 포함관계: 접두("창고43"+무교점) 또는 접미(법인수식어+"창고43 무교점").
    임의 부분문자열은 쓰지 않는다 — 건물명("프레스센터")이 무관한 가게들을 잇는다."""
    return len(short) >= 3 and (long.startswith(short) or long.endswith(short))


def cluster_pairs(pair_counts: Counter) -> dict:
    """(이름키, 주소키) 쌍을 가게 단위로 접는다. 반환: pair → 클러스터 대표 pair.

    1) 같은 주소키에서 이름 포함관계(접두/접미)면 병합.
       단, 긴 이름은 자기 대표 주소에서만 — 오입력 주소 몇 건이
       지점 사이에 다리를 놓는 것을 막는다("창고43 시청점"@무교로 1건).
    2) 하나의 짧은 이름이 서로 포함관계가 아닌 여러 긴 이름과 매칭되면
       그 짧은 이름의 병합은 전부 포기한다 — 같은 건물의 무관한 가게들을
       잇는 다리가 되기 때문. 과병합보다 미병합이 안전하다.
    3) 주소 없는 쌍은 같은 이름키의 최다 주소 쌍에 귀속.
    """
    uf = _UF()
    by_addr: dict[str, list[str]] = defaultdict(list)
    name_addr_counts: dict[str, Counter] = defaultdict(Counter)
    for (name, addr), cnt in pair_counts.items():
        if addr:
            by_addr[addr].append(name)
            name_addr_counts[name][addr] += cnt

    dominant = {n: c.most_common(1)[0][0] for n, c in name_addr_counts.items()}

    for addr, names in by_addr.items():
        names = sorted(set(names), key=len)
        # short → 이 주소에서 short를 포함하는 긴 이름들 (긴 쪽은 대표 주소일 때만)
        matches: dict[str, list[str]] = defaultdict(list)
        for i, short in enumerate(names):
            for long in names[i + 1 :]:
                if _contained(short, long) and dominant[long] == addr:
                    matches[short].append(long)
        # 짧은 이름은 매칭된 긴 이름들이 전부 한 클러스터일 때만 흡수한다
        # (1:1 매칭은 자명하게 만족). 클러스터가 갈리면 무관한 가게들의
        # 다리이므로 포기 — 과병합보다 미병합이 안전하다.
        # 단 3건 미만의 초저빈도 변형(오타류)은 판정에서 제외한다 —
        # 1건짜리 오타가 수백 건짜리 병합에 거부권을 행사하면 안 된다.
        # 병합이 연쇄로 수렴하도록 변화가 없을 때까지 반복한다.
        changed = True
        while changed:
            changed = False
            for short, longs in matches.items():
                deciders = [l for l in longs if pair_counts[(l, addr)] >= 3] or longs
                roots = {uf.find((long, addr)) for long in deciders}
                if len(roots) == 1 and uf.find((short, addr)) not in roots:
                    uf.union((short, addr), (deciders[0], addr))
                    changed = True

    for (name, addr), _ in pair_counts.items():
        if addr is None and name in dominant:
            uf.union((name, None), (name, dominant[name]))

    return {pair: uf.find(pair) for pair in pair_counts}


def build_clusters(rows: list[dict], recent: tuple = RECENT) -> dict:
    """원장 → 가게 클러스터 집계. 14_kakao_place_match.py가 재사용한다."""
    # ── 1차: (이름키, 주소키) 쌍 수집 ──
    parsed = []  # (pair, raw_name, quarter, 부서, 금액)
    pair_counts: Counter = Counter()
    for r in rows:
        raw_name = r["식당명"].strip()
        q = quarter_of(r["사용일"])
        if not raw_name or not q:
            continue
        name = normalize(raw_name)
        if not name or any(k in name for k in NONFOOD):
            continue
        pair = (name, addr_key(r["주소"]))
        pair_counts[pair] += 1
        meal = meal_of(r.get("사용시간") or "", r.get("사용목적") or "")
        hc = headcount_of(r.get("사용자") or "")
        parsed.append((pair, raw_name, q, r["부서명"], r["사용금액"], meal, hc))

    root_of = cluster_pairs(pair_counts)

    # ── 2차: 클러스터 단위 집계 ──
    C = {
        "qv": defaultdict(Counter),  # 분기별 방문수
        "display": defaultdict(Counter),  # 원표기 빈도
        "name_keys": defaultdict(Counter),  # 클러스터 내 이름키 분포
        "recent_depts": defaultdict(set),
        "amounts": defaultdict(list),
        "addrs": defaultdict(Counter),  # 클러스터 내 주소키 분포
        "name_cluster": defaultdict(Counter),  # 이름키 → 클러스터별 행수
        "meal": defaultdict(Counter),  # lunch/dinner/other 행수
        "pp": defaultdict(list),  # 인당 지출 표본 (금액/인원)
    }
    for pair, raw_name, q, dept, amount, meal, hc in parsed:
        root = root_of[pair]
        C["qv"][root][q] += 1
        C["display"][root][raw_name] += 1
        C["name_keys"][root][pair[0]] += 1
        C["name_cluster"][pair[0]][root] += 1
        if pair[1]:
            C["addrs"][root][pair[1]] += 1
        if q in recent:
            C["recent_depts"][root].add(dept)
        if meal:
            C["meal"][root][meal] += 1
        try:
            amt = int(amount)
        except ValueError:
            amt = None
        if amt is not None:
            C["amounts"][root].append(amt)
        if amt and hc and hc >= 2:
            pp = amt / hc
            if 3000 <= pp <= 300000:  # 인원 오파싱·비식사 결제 가드
                C["pp"][root].append(pp)
    return C


def display_name(C: dict, root) -> str:
    # "창고43"처럼 여러 지점에 걸친 이름은 라벨로 부적합 →
    # 행의 80% 이상이 이 클러스터에 속하는(=클러스터를 특정하는)
    # 이름키 중 최다 표기를 쓴다. 오입력 몇 건이 지점명을
    # "모호"로 만들지 않도록 완전 단독 소속은 요구하지 않는다.
    for nk, _ in C["name_keys"][root].most_common():
        if C["name_cluster"][nk][root] / sum(C["name_cluster"][nk].values()) >= 0.8:
            best = Counter(
                {raw: c for raw, c in C["display"][root].items() if normalize(raw) == nk}
            )
            if best:
                return best.most_common(1)[0][0]
    return C["display"][root].most_common(1)[0][0]


def entry(C: dict, key, quarters=QUARTERS, recent=RECENT, base=BASE) -> dict:
    series = [C["qv"][key][q] for q in quarters]
    meal = C["meal"][key]
    pp = C["pp"][key]
    return {
        "name": display_name(C, key),
        "series": series,
        "recent": sum(C["qv"][key][q] for q in recent),
        "base": sum(C["qv"][key][q] for q in base),
        "depts": len(C["recent_depts"][key]),
        "avgAmount": int(statistics.mean(C["amounts"][key])) if C["amounts"][key] else 0,
        "variants": len(C["display"][key]),
        # 인당 지출: 결제액/인원 중앙값. 표본 5건 미만이면 신뢰 불가 → null
        "perPerson": int(round(statistics.median(pp), -2)) if len(pp) >= 5 else None,
        "perPersonN": len(pp),
        # 끼니 분류 행수 (timed = 시간·목적으로 분류된 전체)
        "lunch": meal["lunch"],
        "dinner": meal["dinner"],
        "timed": sum(meal.values()),
    }


def make_result(
    C: dict,
    n_transactions: int,
    decorate=None,
    extra_stats=None,
    *,
    quarters=QUARTERS,
    recent=RECENT,
    base=BASE,
    source="서울시 본청 업무추진비",
    min_recent=15,
    min_depts=3,
    steady_min=5,
) -> dict:
    """클러스터 집계 → 랭킹 JSON. decorate(key, entry)로 항목을 보강할 수 있다.

    임계값 기본은 본청(분기 ~1.2만 건) 기준 — 자치구는 규모에 맞춰 내려 쓴다.
    """

    def make(key) -> dict:
        e = entry(C, key, quarters, recent, base)
        if decorate:
            decorate(key, e)
        return e

    # 최소 표본/부서 다양성 필터를 통과한 후보
    candidates = [
        make(k)
        for k in C["qv"]
        if sum(C["qv"][k][q] for q in recent) >= min_recent
        and len(C["recent_depts"][k]) >= min_depts
    ]

    rising = sorted(
        (e for e in candidates if e["base"] > 0),
        key=lambda e: (e["recent"] + 1) / (e["base"] + 1),
        reverse=True,
    )
    for e in rising:
        e["growth"] = round((e["recent"] + 1) / (e["base"] + 1), 2)

    newcomers = sorted(
        (e for e in candidates if e["base"] == 0),
        key=lambda e: e["recent"],
        reverse=True,
    )

    steady = []
    for k in C["qv"]:
        series = [C["qv"][k][q] for q in quarters]
        if all(v >= steady_min for v in series):
            e = make(k)
            e["cv"] = round(statistics.stdev(series) / statistics.mean(series), 3)
            steady.append(e)
    steady.sort(key=lambda e: e["cv"])

    # 상황별: 시간·목적으로 분류된 행이 10건 이상인 후보 중 끼니 쏠림이
    # 뚜렷한 곳. 저녁 기저율(~20%)이 낮아 임계도 낮다(70% vs 50%).
    def meal_spots(kind: str, min_share: float) -> list[dict]:
        spots = []
        for e in candidates:
            if e["timed"] >= 10 and e[kind] / e["timed"] >= min_share:
                e[f"{kind}Share"] = round(e[kind] / e["timed"], 2)
                spots.append(e)
        spots.sort(key=lambda e: -e["recent"])
        return spots[:20]

    return {
        "source": source,
        "quarters": list(quarters),
        "recentQuarters": list(recent),
        "baseQuarters": list(base),
        "rising": rising[:20],
        "newcomers": newcomers[:20],
        "steady": steady[:20],
        "lunchSpots": meal_spots("lunch", 0.7),
        "dinnerSpots": meal_spots("dinner", 0.5),
        "stats": {
            "transactions": n_transactions,
            "restaurants": len(C["qv"]),
            "candidates": len(candidates),
            **(extra_stats or {}),
        },
    }


def show_result(result: dict, out_path=None) -> None:
    def show(title: str, items: list[dict], extra) -> None:
        print(f"\n=== {title} ===")
        for e in items:
            print(
                f"{extra(e):>7} 최근{e['recent']:4d} 부서{e['depts']:3d} "
                f"{' '.join(f'{v:3d}' for v in e['series'])}  "
                f"{e['name']} (평균 {e['avgAmount']:,}원, 표기 {e['variants']}종)"
            )

    show("🔥 뜨는 집 TOP 10 (기존 식당, 전년 동기 대비)", result["rising"][:10], lambda e: f"{e['growth']}x")
    show("⭐ 신규 진입 TOP 10", result["newcomers"][:10], lambda e: "신규")
    show("🏛 스테디셀러 TOP 10", result["steady"][:10], lambda e: f"cv{e['cv']}")
    s = result["stats"]
    tail = f" → {out_path}" if out_path else ""
    print(f"\n거래 {s['transactions']:,}건 / 식당 {s['restaurants']:,}곳 / 후보 {s['candidates']}곳{tail}")


def main() -> None:
    rows = load_rows()
    C = build_clusters(rows)
    result = make_result(C, len(rows))
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    show_result(result, OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
