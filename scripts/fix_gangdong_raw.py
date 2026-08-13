"""기존 gangdong_expense_raw.csv의 컬럼 밀림 행을 재크롤 없이 복구.

일부 강동 PDF는 표가 [연번, 사용자, 사용일자, 사용시간, 장소, 집행목적,
인원, 집행액, 결제방법]으로 한 칸 더 넓은데, 11_gangdong_parse.py가 본청
레이아웃으로 읽어 전체 행의 65%가 이렇게 저장됐다:

  사용일 ← "3.5.(목)"(연도 없음)  식당명/사용장소 ← 시간("12:12")
  사용목적 ← 실제 식당명          사용금액 ← 인원수("4")
  결제방법 ← 금액("49,500")       비목 ← 결제방법("신용카드")

복구: 식당명 시간 패턴 + 사용목적 비어있지 않음으로 밀림을 감지해 컬럼을
제자리로 돌리고, 연도는 gangdong_posts.json 게시물 제목("2026년 3월 …
공개")에서 가져온다(12월↔1월 경계는 월 차이로 보정). 원본은 .bak에 보존.
"""

from __future__ import annotations

import os as _os
from pathlib import Path as _Path

_os.chdir(_Path(__file__).resolve().parent.parent)
import csv
import io
import json
import re
import shutil

RAW = "data/output/gangdong_expense_raw.csv"
BAK = RAW + ".bak"
POSTS = "data/output/gangdong_posts.json"

_TIME = re.compile(r"^\d{1,2}[:시]\d{0,2}$")
_DAY_ONLY = re.compile(r"^(\d{1,2})\s*[./]\s*(\d{1,2})")
_TITLE_YM = re.compile(r"(20\d{2})\s*년\s*(\d{1,2})\s*월")
_AMOUNT = re.compile(r"^[\d,]+$")


def title_ym(posts: list[dict]) -> dict:
    out = {}
    for p in posts:
        m = _TITLE_YM.search(p.get("title") or "")
        if m:
            out[f"gangdong_{p['id']}"] = (int(m.group(1)), int(m.group(2)))
    return out


def restore_date(day_only: str, ym: tuple[int, int] | None) -> str:
    m = _DAY_ONLY.match(day_only)
    if not m or not ym:
        return day_only  # 복구 불가 — 원본 유지(quarter_of가 버린다)
    mo, day = int(m.group(1)), int(m.group(2))
    year, title_mo = ym
    if not (1 <= mo <= 12 and 1 <= day <= 31):
        return day_only
    # 보고서 월과 행의 월이 연말연시로 어긋난 경우 보정
    if mo == 12 and title_mo == 1:
        year -= 1
    elif mo == 1 and title_mo == 12:
        year += 1
    return f"{year}-{mo:02d}-{day:02d}"


def main():
    if not _os.path.exists(BAK):
        shutil.copy2(RAW, BAK)
        print(f"백업: {BAK}")

    ym_of = title_ym(json.load(open(POSTS, encoding="utf-8")))
    text = open(BAK, encoding="utf-8-sig", errors="replace").read().replace("\x00", "")
    rows = list(csv.DictReader(io.StringIO(text)))

    fixed = dated = 0
    for r in rows:
        name = (r.get("식당명") or "").strip()
        purpose = (r.get("사용목적") or "").strip()
        if not (_TIME.match(name) and purpose):
            continue
        pay_col = (r.get("결제방법") or "").strip()
        r["사용시간"] = name
        r["식당명"] = purpose
        r["사용장소"] = purpose
        r["사용목적"] = ""
        r["사용금액"] = pay_col.replace(",", "") if _AMOUNT.match(pay_col) else ""
        r["결제방법"] = (r.get("비목") or "").strip()
        r["비목"] = ""
        fixed += 1
        date = (r.get("사용일") or "").strip()
        if not re.match(r"^20\d{2}", date):
            restored = restore_date(date, ym_of.get(r.get("source_file") or ""))
            if restored != date:
                r["사용일"] = restored
                dated += 1

    fields = rows[0].keys()
    with open(RAW, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"총 {len(rows):,}행 중 밀림 복구 {fixed:,}행 (연도 복원 {dated:,}행) → {RAW}")


if __name__ == "__main__":
    main()
