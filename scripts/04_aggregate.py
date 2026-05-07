"""
4단계: raw CSV들 → 가맹점(식당) 단위 집계 → 공슐랭 랭킹 CSV

집계 키: (정규화 식당명, 구) — 같은 이름이어도 소속 구가 다르면 별개 식당으로 취급.
자치구 raw는 주소가 대부분 비어있으므로 raw 파일의 출처 구를 region으로 사용.
본청(seoul) raw는 주소에서 구 추출 → 없으면 "본청".

체인점 축약·띄어쓰기·지점 접미사 변종을 같은 구 안에서 합치기 위한 이름 정규화 포함
(괄호 제거, 공백 제거, 후행 자치구명/구청점 패턴 제거).
"""

import os as _os
from pathlib import Path as _Path
_os.chdir(_Path(__file__).resolve().parent.parent)
import csv
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collect_common import parse_place_with_addr

OUT_DIR = "data/output"

FILE_TO_REGION = {
    "seoul_expense_raw.csv":     None,  # 본청 — 주소 기반
    "ddm_expense_raw.csv":       "동대문구",
    "dobong_expense_raw.csv":    "도봉구",
    "dongjak_expense_raw.csv":   "동작구",
    "ep_expense_raw.csv":        "은평구",
    "gangbuk_expense_raw.csv":   "강북구",
    "gangdong_expense_raw.csv":  "강동구",
    "gangnam_expense_raw.csv":   "강남구",
    "gangseo_expense_raw.csv":   "강서구",
    "geumcheon_expense_raw.csv": "금천구",
    "guro_expense_raw.csv":      "구로구",
    "gwanak_expense_raw.csv":    "관악구",
    "gwangjin_expense_raw.csv":  "광진구",
    "jongno_expense_raw.csv":    "종로구",
    "junggu_expense_raw.csv":    "중구",
    "jungnang_expense_raw.csv":  "중랑구",
    "mapo_expense_raw.csv":      "마포구",
    "nowon_expense_raw.csv":     "노원구",
    "sb_expense_raw.csv":        "성북구",
    "sdm_expense_raw.csv":       "서대문구",
    "seocho_expense_raw.csv":    "서초구",
    "seongdong_expense_raw.csv": "성동구",
    "songpa_expense_raw.csv":    "송파구",
    "yangcheon_expense_raw.csv": "양천구",
    "ydp_expense_raw.csv":       "영등포구",
    "yongsan_expense_raw.csv":   "용산구",
}

SRCS = [f"{OUT_DIR}/{fn}" for fn in FILE_TO_REGION.keys()]
OUT = f"{OUT_DIR}/gongsulrang_ranking_seoul_2024.csv"

GUS = [
    "강남구","강동구","강북구","강서구","관악구","광진구","구로구","금천구",
    "노원구","도봉구","동대문구","동작구","마포구","서대문구","서초구","성동구",
    "성북구","송파구","양천구","영등포구","용산구","은평구","종로구","중구","중랑구",
]
GU_SHORT_RE = "|".join(g[:-1] for g in GUS)  # 강남|강동|...|중랑|중
GU_FULL_RE = re.compile(r"(" + "|".join(GUS) + r")")
_SUFFIX_RE = re.compile(rf"({GU_SHORT_RE})(구청역점|구청점|구청역|구청|구|점)?$")

def extract_gu(s: str) -> str:
    if not s:
        return ""
    m = GU_FULL_RE.search(s)
    return m.group(1) if m else ""

BRAND_ALIASES: list[tuple[re.Pattern, str]] = [
    # 법인명 → 실 브랜드명. 매칭되면 식당명을 통째로 교체.
    (re.compile(r"(?:주식회사\s*|\(주\)\s*|（주）\s*|㈜\s*)?에스씨케이\s*컴퍼니"), "스타벅스"),
]


def apply_brand_aliases(name: str) -> str:
    for pattern, brand in BRAND_ALIASES:
        if pattern.search(name):
            return brand
    return name


def clean_base(raw: str) -> str:
    """체인 지점 변종을 한 이름으로 합치기 위한 정규화:
    - 괄호 안 내용 제거 (주소/지점 표기)
    - 모든 공백 제거
    - 후행 자치구명 + (구청점/구청역점/구청/점 등) 제거
    - 남는 콤마/따옴표 등 후처리
    예:
      "지호한방 삼계탕"           → "지호한방삼계탕"
      "지호한방삼계탕도봉구청점"    → "지호한방삼계탕"
      "지호한방삼계탕 (수유점)"    → "지호한방삼계탕"
      "지호한방삼계탕(동작)"       → "지호한방삼계탕"
    """
    s = raw.strip()
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"（[^）]*）", "", s)
    s = re.sub(r"\s+", "", s)
    s = s.strip(",.·-_'\"`~")
    prev = None
    # 여러 번 매칭될 수 있어 루프 (예: "XX도봉구청점" 후행 제거)
    while prev != s:
        prev = s
        s = _SUFFIX_RE.sub("", s)
        s = s.strip(",.·-_'\"`~")
    return s

def display_from_raw(raw: str) -> str:
    """출력용 이름: 공백 정리만."""
    s = re.sub(r"\s+", " ", raw.strip())
    return s.rstrip(",").strip()

# 식당이 아닐 가능성이 높은 업종 필터 (간식/행사/택시/꽃집 등은 공슐랭 컨셉 밖)
EXCLUDE_PATTERNS = [
    "택시", "다이소", "꽃집", "화훼", "카카오", "쿠팡", "네이버", "GS25", "세븐일레븐",
    "CU ", "이마트", "홈플러스", "상품권", "주유", "GS칼텍스", "SK에너지",
    "매점", "간담회장", "구내식당",
]
_NOISE_RE = re.compile(
    r"^(?:[-.\s·_~/]+"
    r"|\d+"
    r"|\d{1,2}[:시]\d{0,2}"
    r"|\d{1,2}시\s*\d{0,2}분?"
    r"|오[전후]\s*\d{1,2}(?::\d{2})?"
    r")$"
)
def is_restaurant_like(name: str) -> bool:
    if not name or len(name) < 2: return False
    if _NOISE_RE.match(name): return False
    n = name.lower()
    for p in EXCLUDE_PATTERNS:
        if p.lower() in n:
            return False
    return True

def main():
    # 키 = (clean_base, region) — 이름 정규화 + 구 단위 분리
    agg = defaultdict(lambda: {
        "count": 0, "sum": 0, "depts": set(),
        "dept_counter": defaultdict(int),
        "name_counter": defaultdict(int),
        "addr_counter": defaultdict(int),
    })
    total_rows = 0
    skipped_non_restaurant = 0
    skipped_outlier_amount = 0
    skipped_no_region = 0
    AMOUNT_MAX = 10_000_000

    for src in SRCS:
        if not os.path.exists(src):
            print(f"  (skip) {src} 없음")
            continue
        fname = os.path.basename(src)
        file_region = FILE_TO_REGION.get(fname)
        n_file = 0
        with open(src, encoding="utf-8-sig") as f:
            r = csv.DictReader(f)
            for row in r:
                total_rows += 1
                n_file += 1
                raw_name = (row.get("식당명") or "").strip()
                if not raw_name:
                    skipped_non_restaurant += 1
                    continue
                # 식당명에 (주소) 패턴이 섞여 들어온 경우 분리
                addr_from_name = ""
                if "(" in raw_name:
                    parsed_name, parsed_addr = parse_place_with_addr(raw_name)
                    if not parsed_name:
                        skipped_non_restaurant += 1
                        continue
                    raw_name = parsed_name
                    addr_from_name = parsed_addr
                # 법인명 → 실 브랜드 alias (예: 주식회사 에스씨케이컴퍼니 → 스타벅스)
                raw_name = apply_brand_aliases(raw_name)
                disp = display_from_raw(raw_name)
                if not is_restaurant_like(disp):
                    skipped_non_restaurant += 1
                    continue
                try:
                    amount = int(row["사용금액"])
                except (ValueError, KeyError, TypeError):
                    continue
                if amount <= 0 or amount > AMOUNT_MAX:
                    skipped_outlier_amount += 1
                    continue

                addr = (row.get("주소") or "").strip()
                if not addr and addr_from_name:
                    addr = addr_from_name
                dept = (row.get("부서명") or row.get("부서_메타") or "").replace("\n", " ").replace("\r", " ")
                dept = re.sub(r"\s+", " ", dept).strip()

                # region 결정
                if file_region:  # 자치구 raw: 고정
                    region = file_region
                else:            # 본청 raw: 주소에서 추출, 없으면 "본청"
                    region = extract_gu(addr) or "본청"

                base = clean_base(raw_name)
                if not base:
                    skipped_non_restaurant += 1
                    continue

                key = (base, region)
                a = agg[key]
                a["count"] += 1
                a["sum"] += amount
                a["depts"].add(dept)
                a["dept_counter"][dept] += 1
                a["name_counter"][disp] += 1
                if addr:
                    a["addr_counter"][addr] += 1
        print(f"  {fname}: {n_file}행 (region={file_region or '본청(주소)'})")

    items = []
    for (base, region), v in agg.items():
        # 출력 이름: 그 키 안에서 가장 많이 쓰인 원본 표기
        best_name = max(v["name_counter"].items(), key=lambda x: (x[1], -len(x[0])))[0]
        top_agency = max(v["dept_counter"].items(), key=lambda x: x[1])[0] if v["dept_counter"] else ""
        if v["addr_counter"]:
            best_addr = max(v["addr_counter"].items(), key=lambda x: (x[1], len(x[0])))[0]
        else:
            best_addr = ""
        items.append({
            "식당명": best_name,
            "주소": best_addr,
            "지역": region,
            "이용횟수": v["count"],
            "총이용금액": v["sum"],
            "평균금액": round(v["sum"] / v["count"]) if v["count"] else 0,
            "집행부서수": len(v["depts"]),
            "주요이용기관": top_agency,
        })
    items.sort(key=lambda x: (-x["이용횟수"], -x["총이용금액"]))
    for i, it in enumerate(items, 1):
        it["순위"] = i

    with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["순위", "식당명", "주소", "지역", "이용횟수", "총이용금액", "평균금액", "집행부서수", "주요이용기관"])
        for it in items:
            w.writerow([it["순위"], it["식당명"], it["주소"], it["지역"],
                        it["이용횟수"], it["총이용금액"], it["평균금액"], it["집행부서수"], it["주요이용기관"]])
    print(f"\nraw 행: {total_rows:,}, 비식당 제외: {skipped_non_restaurant:,}, 금액이상치 제외: {skipped_outlier_amount:,}")
    print(f"고유 식당 수: {len(items):,} → {OUT}")
    print("\n🏆 TOP 30:")
    for it in items[:30]:
        print(f"  {it['순위']:3d}. {it['식당명'][:28]:28s}  {it['지역']:6s}  "
              f"이용 {it['이용횟수']:>4}회  총 {it['총이용금액']:>12,}원  "
              f"부서 {it['집행부서수']:>3}  · {it['주요이용기관']}")

if __name__ == "__main__":
    main()
