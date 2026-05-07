"""
관악구 업무추진비 공개 수집 — 리스트에 각 레코드가 직접 노출되는 타입

- 리스트: https://www.gwanak.go.kr/site/gwanak/estimate/estimateList.do?pageIndex={N}
  - 한 페이지 10개 레코드, 각 레코드는 3개 <tr>로 구성
    tr1: [비목, 집행부서, 집행일시]
    tr2: [집행내역(colspan), 결제방법(colspan)]
    tr3: [사용자, 대상인원수, 집행장소, 집행금액]
  - pageUnit 파라미터 무시됨 → 페이지당 10행 고정
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
from datetime import datetime

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collect_common import FIELDS, RateLimiter, record_to_csv, parse_place_with_addr

OUT_DIR = "data/output"
RAW_OUT = f"{OUT_DIR}/gwanak_expense_raw.csv"

BASE = "https://www.gwanak.go.kr"
LIST_URL = f"{BASE}/site/gwanak/estimate/estimateList.do"
HEADERS = {"User-Agent": "Mozilla/5.0 (gongsulrang-collector; edu-research)",
           "Accept-Language": "ko,en;q=0.8"}
SINCE = datetime(2023, 9, 1)
RATE_LIST = 0.8
DISTRICT = "관악구"


def parse_date(s: str) -> datetime | None:
    s = (s or "").strip()
    m = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", s)
    if not m:
        return None
    try:
        return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def fetch_list_page(session: requests.Session, page: int) -> list[dict]:
    r = session.get(LIST_URL, params={"pageIndex": str(page)}, headers=HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    rows = []
    # 페이지마다 record당 1개의 table, 한 table에 3개 tr
    for t in soup.find_all("table"):
        ths = [x.get_text(" ", strip=True) for x in t.find_all("th")]
        if "집행일시" not in ths or "집행금액(원)" not in ths:
            continue
        tb = t.find("tbody")
        if not tb:
            continue
        trs = tb.find_all("tr")
        if len(trs) < 3:
            continue
        tds1 = [x.get_text(" ", strip=True) for x in trs[0].find_all("td")]
        tds2 = [x.get_text(" ", strip=True) for x in trs[1].find_all("td")]
        tds3 = [x.get_text(" ", strip=True) for x in trs[2].find_all("td")]
        if len(tds1) < 3 or len(tds2) < 2 or len(tds3) < 4:
            continue
        rows.append({
            "bimok": tds1[0],
            "dept": tds1[1],
            "datetime": tds1[2],
            "purpose": tds2[0],
            "pay": tds2[1],
            "user": tds3[0],
            "count": tds3[1],
            "place": tds3[2],
            "amount": tds3[3],
        })
    return rows


def to_record(r: dict) -> tuple[dict, str]:
    name, addr = parse_place_with_addr(r["place"])
    rec = {
        "user": r["user"], "datetime": r["datetime"], "date": "", "time": "",
        "place": name or r["place"], "purpose": r["purpose"],
        "count": r["count"], "amount": r["amount"],
        "pay": r["pay"], "bimok": r["bimok"],
    }
    return rec, addr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default=SINCE.strftime("%Y-%m-%d"))
    ap.add_argument("--max-pages", type=int, default=4000)
    args = ap.parse_args()
    since_dt = datetime.strptime(args.since, "%Y-%m-%d")

    session = requests.Session()
    rate = RateLimiter(RATE_LIST)
    print(f"[{DISTRICT}] crawling since={since_dt.date()} max-pages={args.max_pages}")

    n_rows = 0
    consec_out = 0
    with open(RAW_OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        page = 1
        while page <= args.max_pages:
            try:
                rows = fetch_list_page(session, page)
            except Exception as e:
                print(f"  cp={page} err={e}, retry 2s")
                time.sleep(2)
                try:
                    rows = fetch_list_page(session, page)
                except Exception as e2:
                    print(f"    2nd fail: {e2}")
                    page += 1
                    rate.wait()
                    continue
            if not rows:
                print(f"  cp={page}: 0행, 종료")
                break
            in_range = 0
            out_range = 0
            oldest = None
            for r in rows:
                d = parse_date(r["datetime"])
                oldest = d if (oldest is None or (d and d < oldest)) else oldest
                if d is None or d >= since_dt:
                    rec, addr = to_record(r)
                    out = record_to_csv(rec, district=DISTRICT, dept=r["dept"],
                                        source_id=f"gwanak_p{page}", address=addr)
                    if out:
                        w.writerow(out)
                        n_rows += 1
                        in_range += 1
                else:
                    out_range += 1
            if page % 20 == 0 or page <= 5:
                print(f"  cp={page}: rows={len(rows)} kept={in_range} old={out_range} "
                      f"oldest={oldest.date() if oldest else '?'} 누계={n_rows}")
            if rows and out_range == len(rows):
                consec_out += 1
                if consec_out >= 3:
                    print("  → 3연속 범위밖, 중단")
                    break
            else:
                consec_out = 0
            page += 1
            rate.wait()

    print(f"[{DISTRICT}] ✅ records={n_rows} → {RAW_OUT}")


if __name__ == "__main__":
    main()
