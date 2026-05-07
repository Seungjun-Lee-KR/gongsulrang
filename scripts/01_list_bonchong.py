"""
1단계: 서울시본청 업무추진비 게시글 ID 목록 수집

- 대상: 2024년 (월별 페이지네이션 순회)
- 필터: 제목에 "서울시본청" 포함
- 결과: ~/Downloads/files/output/seoul_bonchong_2024_list.csv
       (id, title, year, month)
"""

import os as _os
from pathlib import Path as _Path
_os.chdir(_Path(__file__).resolve().parent.parent)
import re
import csv
import time
import sys
import requests

BASE = "https://opengov.seoul.go.kr/expense/list"
HEADERS = {"User-Agent": "Mozilla/5.0 (gongsulrang-poc; edu-research)"}
YEAR = int(sys.argv[1]) if len(sys.argv) > 1 else 2024
OUT = f"data/output/seoul_bonchong_{YEAR}_list.csv"
RATE = 0.8  # 초당 요청 제한

LINK_RE = re.compile(r'<a[^>]*href="/expense/(\d+)"[^>]*>([^<]+)</a>')

def fetch_page(year: int, month: int, page: int) -> str:
    params = {
        "ym[year]": year,
        "ym[month]": month,
        "items_per_page": 50,
        "page": page,
    }
    r = requests.get(BASE, params=params, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r.text

def parse(html: str):
    return LINK_RE.findall(html)

def main():
    rows = []
    for month in range(1, 13):
        print(f"\n[{YEAR}-{month:02d}] 목록 수집 시작")
        page = 0
        empty_streak = 0
        while True:
            html = fetch_page(YEAR, month, page)
            items = parse(html)
            if not items:
                empty_streak += 1
                if empty_streak >= 2:
                    break
                page += 1
                time.sleep(RATE)
                continue
            empty_streak = 0
            bonchong = [(i, t) for (i, t) in items if "서울시본청" in t]
            print(f"  page {page:02d}: total {len(items):2d}, 본청 {len(bonchong):2d}")
            for i, t in bonchong:
                rows.append((i, t.strip(), YEAR, month))
            if len(items) < 50:
                break
            page += 1
            time.sleep(RATE)

    # 중복 제거 (같은 id 여러 번 잡힐 수 있음)
    seen = set()
    dedup = []
    for r in rows:
        if r[0] in seen: continue
        seen.add(r[0])
        dedup.append(r)

    with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "title", "year", "month"])
        w.writerows(dedup)

    print(f"\n✅ 총 {len(dedup)}건 저장 → {OUT}")

if __name__ == "__main__":
    main()
