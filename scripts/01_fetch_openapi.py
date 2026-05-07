"""
1단계(신규): 서울 열린데이터광장 odExpense OpenAPI에서 raw 집행 내역 수집

- 엔드포인트: http://openapi.seoul.go.kr:8088/{KEY}/xml/odExpense/{S}/{E}/
- 총 건수: 153,015 (2023-10 ~ 2026-03, 서울시본청 단일 스코프)
- 출력: output/seoul_expense_raw.csv (기존 04_aggregate.py와 호환 스키마)
- 옵션: --limit N (처음 N건만 수집, 파일럿 검증용)
"""

import os as _os
from pathlib import Path as _Path
_os.chdir(_Path(__file__).resolve().parent.parent)
import argparse
import csv
import os
import re
import sys
import time
import xml.etree.ElementTree as ET

import requests
from dotenv import load_dotenv

load_dotenv(".env.local")
KEY = os.getenv("SEOUL_OPENAPI_KEY")
if not KEY:
    print("SEOUL_OPENAPI_KEY가 .env에 없습니다.")
    sys.exit(1)

BASE = f"http://openapi.seoul.go.kr:8088/{KEY}/xml/odExpense"
OUT = "data/output/seoul_expense_raw.csv"
PAGE = 1000
RATE = 0.3
MAX_RETRY = 3

FIELDS = [
    "부서_메타", "부서명", "사용일", "사용시간", "사용장소", "식당명",
    "주소", "사용목적", "사용금액", "사용자", "결제방법", "비목", "source_file",
]

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
    a = re.sub(r"^서울특별시\s*", "서울 ", a)
    if not a.startswith("서울"):
        for gu in GU_PREFIXES[1:]:
            if a.startswith(gu + " "):
                a = "서울 " + a
                break
    return a.strip()


def split_place(raw: str):
    if not raw or not isinstance(raw, str):
        return raw, ""
    s = raw.strip()
    idx = s.rfind("(")
    if idx <= 0:
        return s, ""
    head = s[:idx].strip()
    tail = s[idx + 1:].rstrip(")").rstrip(",").strip()
    is_addr = any(k in tail for k in ADDR_KEYWORDS) or \
              any(tail.startswith(x) for x in GU_PREFIXES)
    if is_addr and head:
        return head, normalize_addr(tail)
    return s, ""


def fetch(start: int, end: int) -> list[dict]:
    url = f"{BASE}/{start}/{end}/"
    for attempt in range(1, MAX_RETRY + 1):
        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            root = ET.fromstring(r.content)
            code = root.findtext("RESULT/CODE") or root.findtext(".//CODE")
            if code and code != "INFO-000":
                msg = root.findtext("RESULT/MESSAGE") or root.findtext(".//MESSAGE")
                if code == "INFO-200":  # no data
                    return []
                raise RuntimeError(f"{code}: {msg}")
            rows = []
            for row in root.findall("row"):
                rows.append({child.tag: (child.text or "") for child in row})
            return rows
        except Exception as e:
            if attempt == MAX_RETRY:
                raise
            wait = 2 ** attempt
            print(f"  retry {attempt} after {wait}s ({e})")
            time.sleep(wait)
    return []


def total_count() -> int:
    url = f"{BASE}/1/1/"
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    root = ET.fromstring(r.content)
    return int(root.findtext("list_total_count") or 0)


def to_csv_row(api: dict, nid: str = "") -> list[str]:
    exec_dt = api.get("EXEC_DT", "") or ""
    if " " in exec_dt:
        date_part, time_part = exec_dt.split(" ", 1)
    else:
        date_part, time_part = exec_dt, ""
    dept_full = api.get("DEPT_NM_FULL", "") or api.get("DEPT_NM", "") or ""
    loc = api.get("EXEC_LOC", "") or ""
    rest_name, addr = split_place(loc)
    return [
        dept_full,                              # 부서_메타
        dept_full,                              # 부서명
        date_part,                              # 사용일
        time_part,                              # 사용시간
        loc,                                    # 사용장소 (원본)
        rest_name,                              # 식당명 (괄호 앞 상호)
        addr,                                   # 주소 (괄호 안, 주소 패턴일 때만)
        api.get("EXEC_PURPOSE", "") or "",      # 사용목적
        api.get("EXEC_AMOUNT", "") or "0",      # 사용금액
        api.get("TARGET_NM", "") or "",         # 사용자
        api.get("PAYMENT_METHOD", "") or "",    # 결제방법
        api.get("BIMOK", "") or "",             # 비목
        f"api_{nid}" if nid else "api",         # source_file
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="0=전체, N>0이면 처음 N건만")
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()

    total = total_count()
    print(f"서버 총 건수: {total:,}")
    target = min(total, args.limit) if args.limit > 0 else total
    print(f"수집 목표: {target:,}")

    written = 0
    page_no = 0
    with open(args.out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(FIELDS)
        start = 1
        while start <= target:
            end = min(start + PAGE - 1, target)
            page_no += 1
            rows = fetch(start, end)
            if not rows:
                print(f"  page {page_no} ({start}~{end}): 0건 — 종료")
                break
            for api in rows:
                w.writerow(to_csv_row(api, api.get("NID", "")))
            written += len(rows)
            if page_no % 5 == 0 or end == target:
                print(f"  page {page_no:3d} ({start:>6}~{end:>6}): {len(rows)}건, 누계 {written:,}")
            start = end + 1
            time.sleep(RATE)

    print(f"\n✅ {written:,}건 저장 → {args.out}")


if __name__ == "__main__":
    main()
