"""
3단계: 다운받은 XLSX들을 파싱 → raw.csv 한 파일로 통합

엑셀 구조:
  행 1: 제목 "YYYY년 M월분 업무추진비 사용 내역"
  행 2: 빈
  행 3: '부서 :', 부서명, ..., '사용금액 합계', 금액
  행 4: 빈
  행 5: 헤더 (No./구분/부서명/사용일/사용시간/사용장소/사용목적/사용금액(원)/사용자 및 인원/결제방법/비목)
  행 6~: 데이터
  끝에 요약 행이 붙는 경우가 있음 → 사용일이 날짜 형식이 아니면 drop
"""

import os as _os
from pathlib import Path as _Path
_os.chdir(_Path(__file__).resolve().parent.parent)
import os
import csv
import re
import sys
import glob
from datetime import datetime
import openpyxl

RAW_DIR = "data/raw/seoul"
OUT_CSV = "data/output/seoul_expense_raw.csv"
COLUMNS = ["부서_메타", "부서명", "사용일", "사용시간", "사용장소", "식당명", "주소",
           "사용목적", "사용금액", "사용자", "결제방법", "비목", "source_file"]

# 사용장소에서 주소 분리: 마지막 '(' 이후가 주소 후보 (공백 유무 무관).
# 주소 판별 휴리스틱: '구', '동', '로', '길' 중 하나 포함
ADDR_KEYWORDS = ("구 ", "동 ", "로 ", "길 ", "군 ", "읍 ", "면 ", "대로 ")
GU_PREFIXES = ("서울", "중구", "종로", "강남", "마포", "용산",
               "성동", "광진", "동대문", "중랑", "성북", "강북",
               "도봉", "노원", "은평", "서대문", "양천", "강서",
               "구로", "금천", "영등포", "동작", "관악", "서초",
               "송파", "강동")

def normalize_addr(addr: str) -> str:
    if not addr:
        return ""
    a = re.sub(r"\s+", " ", addr.strip())
    a = a.rstrip(",").rstrip().strip()
    # "서울특별시" → "서울"
    a = re.sub(r"^서울특별시\s*", "서울 ", a)
    # 주소 맨앞이 "구"이름으로 시작하면 "서울 " 접두사 붙여서 정규화
    if not a.startswith("서울"):
        for gu in GU_PREFIXES[1:]:  # 서울 제외한 구 이름들
            if a.startswith(gu + " "):
                a = "서울 " + a
                break
    return a.strip()

def split_place(raw: str):
    if not raw or not isinstance(raw, str):
        return raw, ""
    s = raw.strip()
    # 마지막 '(' 위치 찾기 — 공백 유무 무관
    idx = s.rfind("(")
    if idx <= 0:
        return s, ""
    head = s[:idx].strip()
    tail = s[idx+1:].rstrip(")").rstrip(",").strip()
    # tail에 주소 키워드 하나 이상 있거나 지역 접두사로 시작해야 주소로 간주
    is_addr = any(k in tail for k in ADDR_KEYWORDS) or \
              any(tail.startswith(x) for x in GU_PREFIXES)
    if is_addr and head:
        return head, normalize_addr(tail)
    # 주소로 안 보이면 전체를 식당명으로 (지점명 괄호 등)
    return s, ""

def parse_one(path: str):
    try:
        wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    except Exception as e:
        return [], f"load_fail:{e}"
    ws = wb.worksheets[0]
    rows = list(ws.iter_rows(values_only=True))
    if len(rows) < 6:
        return [], "too_short"

    # 부서 메타 (행 3)
    dept_meta = ""
    if len(rows) >= 3 and rows[2]:
        for cell in rows[2]:
            if isinstance(cell, str) and cell.strip() and cell.strip() != "부서 :":
                dept_meta = cell.strip()
                break

    # 헤더 위치: "No." 포함하는 행 찾기 (대개 행 5)
    header_idx = -1
    for i, r in enumerate(rows[:10]):
        if r and any(isinstance(c, str) and c.strip() in ("No.", "No", "연번") for c in r):
            header_idx = i
            break
    if header_idx < 0:
        return [], "no_header"

    data_rows = rows[header_idx+1:]
    out = []
    for r in data_rows:
        if r is None or all(c is None for c in r):
            continue
        # 예상 순서: No, 구분, 부서명, 사용일, 사용시간, 사용장소, 사용목적, 금액, 사용자, 결제, 비목
        if len(r) < 11:
            continue
        no, _gubun, dept, use_date, use_time, place, purpose, amount, users, pay, bimok = r[:11]
        # 요약/합계 행 제거: 사용일이 유효 날짜가 아니면 skip
        if use_date is None:
            continue
        if isinstance(use_date, datetime):
            date_str = use_date.strftime("%Y-%m-%d")
        else:
            s = str(use_date).strip()
            if not re.match(r"^\d{4}-\d{2}-\d{2}", s):
                continue
            date_str = s[:10]
        # 금액 숫자화
        try:
            amt = int(float(str(amount).replace(",", "").strip())) if amount not in (None, "") else 0
        except Exception:
            continue
        if amt <= 0 or not place:
            continue
        rest_name, addr = split_place(str(place))
        time_str = ""
        if use_time is not None:
            if hasattr(use_time, "strftime"):
                time_str = use_time.strftime("%H:%M:%S")
            else:
                time_str = str(use_time).strip()
        out.append([
            dept_meta, str(dept or "").strip(), date_str, time_str,
            str(place).strip(), rest_name, addr,
            str(purpose or "").strip(), amt,
            str(users or "").strip(), str(pay or "").strip(), str(bimok or "").strip(),
            os.path.basename(path),
        ])
    return out, "ok"

def main():
    files = sorted(glob.glob(os.path.join(RAW_DIR, "*.xlsx")))
    print(f"파일 수: {len(files)}")
    all_rows = []
    stats = {}
    for i, p in enumerate(files, 1):
        rows, status = parse_one(p)
        stats[status] = stats.get(status, 0) + 1
        all_rows.extend(rows)
        if i % 50 == 0 or i == len(files):
            print(f"  [{i}/{len(files)}] rows={len(all_rows)} stats={stats}")

    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    with open(OUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        w.writerows(all_rows)
    print(f"\n✅ {len(all_rows)}건 → {OUT_CSV}")
    print(f"   파일 처리 통계: {stats}")

if __name__ == "__main__":
    main()
