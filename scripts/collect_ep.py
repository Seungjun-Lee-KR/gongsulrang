"""
은평구 업무추진비 공개 수집 (리스트에 이미 거래 레코드가 바로 노출됨)

- 리스트: https://www.ep.go.kr/www/selectJobPrtnCtWebList.do?key=666&pageUnit=50&pageIndex={N}
  - th: 연번/부서명/사용자/대상인원/사용일자(일시)/사용장소(가맹점명)/사용목적(내역)/사용금액/사용방법/비목
  - 각 td가 FIELDS 컬럼에 1:1 매핑 → PDF 파싱 불필요
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
from collect_common import FIELDS, RateLimiter, record_to_csv

OUT_DIR = "data/output"
RAW_OUT = f"{OUT_DIR}/ep_expense_raw.csv"

BASE = "https://www.ep.go.kr"
LIST_URL = f"{BASE}/www/selectJobPrtnCtWebList.do"
LIST_PARAMS = {"key": "666", "pageUnit": "50"}
HEADERS = {"User-Agent": "Mozilla/5.0 (gongsulrang-collector; edu-research)",
           "Accept-Language": "ko,en;q=0.8"}
SINCE = datetime(2023, 9, 1)
RATE_LIST = 0.8
DISTRICT = "은평구"


def parse_date(s: str) -> datetime | None:
    s = (s or "").strip()
    m = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", s)
    if not m:
        return None
    return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))


def fetch_list_page(session: requests.Session, page: int) -> list[dict]:
    params = dict(LIST_PARAMS, pageIndex=str(page))
    r = session.get(LIST_URL, params=params, headers=HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    rows = []
    for tr in soup.select("table tbody tr"):
        tds = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
        if len(tds) < 10:
            continue
        # 번호가 숫자가 아니면 스킵 (빈 행 등)
        try:
            int(tds[0])
        except ValueError:
            continue
        rows.append({
            "no": tds[0], "dept": tds[1], "user": tds[2], "count": tds[3],
            "datetime": tds[4], "place": tds[5], "purpose": tds[6],
            "amount": tds[7], "pay": tds[8], "bimok": tds[9],
        })
    return rows


def to_record(r: dict) -> dict:
    return {
        "user": r["user"], "datetime": r["datetime"], "date": "", "time": "",
        "place": r["place"], "purpose": r["purpose"],
        "count": r["count"], "amount": r["amount"],
        "pay": r["pay"], "bimok": r["bimok"],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default=SINCE.strftime("%Y-%m-%d"))
    ap.add_argument("--max-pages", type=int, default=200)
    args = ap.parse_args()
    since_dt = datetime.strptime(args.since, "%Y-%m-%d")

    session = requests.Session()
    rate = RateLimiter(RATE_LIST)
    print(f"[{DISTRICT}] crawling since={since_dt.date()} max-pages={args.max_pages}")

    n_rows = 0
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
                    rec = to_record(r)
                    out = record_to_csv(rec, district=DISTRICT, dept=r["dept"],
                                        source_id=f"ep_{r['no']}")
                    if out:
                        w.writerow(out)
                        n_rows += 1
                        in_range += 1
                else:
                    out_range += 1
            print(f"  cp={page}: rows={len(rows)} kept={in_range} old={out_range} oldest={oldest.date() if oldest else '?'}")
            if rows and out_range == len(rows):
                print("  → 전체 범위 밖, 중단")
                break
            page += 1
            rate.wait()

    print(f"[{DISTRICT}] ✅ records={n_rows} → {RAW_OUT}")


if __name__ == "__main__":
    main()
