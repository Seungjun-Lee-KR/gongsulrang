"""
서대문구 업무추진비 공개 수집 — 리스트에 레코드가 직접 노출되는 타입

- 리스트: https://www.sdm.go.kr/admininfo/budget/openmoney.do
  - POST 방식, cp 파라미터로 페이지네이션 (mode=list)
  - 한 페이지 4 레코드, 각 레코드는 별도 <table>에 4 <tr>로 구성
    tr0: [구분, 집행부서, 집행일]
    tr1: [집행유형, 집행구분]
    tr2: [집행대상, 집행액(천원)]
    tr3: [집행인원, 결제방법, 장소]

- 금액 단위: 천원 → 원으로 변환 (× 1000)
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
RAW_OUT = f"{OUT_DIR}/sdm_expense_raw.csv"

BASE = "https://www.sdm.go.kr"
LIST_URL = f"{BASE}/admininfo/budget/openmoney.do"
HEADERS = {"User-Agent": "Mozilla/5.0 (gongsulrang-collector; edu-research)",
           "Accept-Language": "ko,en;q=0.8"}
SINCE = datetime(2023, 9, 1)
RATE_LIST = 0.8
DISTRICT = "서대문구"


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
    data = {"mode": "list", "cp": str(page)}
    r = session.post(LIST_URL, data=data, headers=HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    rows = []
    for t in soup.find_all("table"):
        ths = [x.get_text(" ", strip=True) for x in t.find_all("th")]
        if "집행일" not in ths or "집행액(천원)" not in ths:
            continue
        tb = t.find("tbody")
        if not tb:
            continue
        trs = tb.find_all("tr")
        if len(trs) < 4:
            continue
        tds0 = [x.get_text(" ", strip=True) for x in trs[0].find_all("td")]
        tds1 = [x.get_text(" ", strip=True) for x in trs[1].find_all("td")]
        tds2 = [x.get_text(" ", strip=True) for x in trs[2].find_all("td")]
        tds3 = [x.get_text(" ", strip=True) for x in trs[3].find_all("td")]
        if len(tds0) < 3 or len(tds1) < 2 or len(tds2) < 2 or len(tds3) < 3:
            continue
        # 금액 천원 → 원
        raw_amt = (tds2[1] or "").replace(",", "").strip()
        try:
            amount_won = int(float(raw_amt) * 1000)
        except (ValueError, TypeError):
            amount_won = 0
        rows.append({
            "bimok": tds0[0],          # 구분
            "dept": tds0[1],           # 집행부서
            "datetime": tds0[2],       # 집행일
            "purpose": tds1[0] or tds1[1],  # 집행유형 또는 집행구분
            "user": tds2[0],           # 집행대상
            "amount": str(amount_won),
            "count": tds3[0],          # 집행인원
            "pay": tds3[1],            # 결제방법
            "place": tds3[2] if len(tds3) > 2 else "",
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
    ap.add_argument("--max-pages", type=int, default=1000)
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
                    rec = to_record(r)
                    out = record_to_csv(rec, district=DISTRICT, dept=r["dept"],
                                        source_id=f"sdm_p{page}")
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
