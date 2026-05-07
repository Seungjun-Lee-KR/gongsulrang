"""
2단계: 목록 CSV의 게시글들에서 XLSX 파일 다운로드

- 입력: ~/Downloads/files/output/seoul_bonchong_2024_list.csv
- 출력: ~/Downloads/files/raw/seoul/{id}.xlsx
- 이미 다운받은 파일은 skip
"""

import os as _os
from pathlib import Path as _Path
_os.chdir(_Path(__file__).resolve().parent.parent)
import os
import csv
import re
import time
import sys
import requests

LIST_CSV = sys.argv[1] if len(sys.argv) > 1 else "data/output/seoul_bonchong_2024_list.csv"
OUT_DIR = "data/raw/seoul"
HEADERS = {"User-Agent": "Mozilla/5.0 (gongsulrang-poc; edu-research)"}
RATE = 0.6

DL_RE = re.compile(r'href="(/og/com/download\.php\?[^"]*\.xlsx)"')

def fetch_xlsx_url(post_id: str) -> str | None:
    r = requests.get(f"https://opengov.seoul.go.kr/expense/{post_id}", headers=HEADERS, timeout=20)
    r.raise_for_status()
    m = DL_RE.search(r.text)
    if not m:
        return None
    return "https://opengov.seoul.go.kr" + m.group(1).replace("&amp;", "&")

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(LIST_CSV, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    total = len(rows)
    ok, skip, fail = 0, 0, 0
    for idx, row in enumerate(rows, 1):
        pid = row["id"]
        out = os.path.join(OUT_DIR, f"{pid}.xlsx")
        if os.path.exists(out) and os.path.getsize(out) > 2000:
            skip += 1
            continue
        try:
            url = fetch_xlsx_url(pid)
            if not url:
                print(f"  [{idx}/{total}] {pid} XLSX 링크 없음")
                fail += 1
                continue
            time.sleep(RATE)
            r = requests.get(url, headers=HEADERS, timeout=60)
            r.raise_for_status()
            with open(out, "wb") as w:
                w.write(r.content)
            ok += 1
            if idx % 20 == 0 or idx == total:
                print(f"  [{idx}/{total}] ok={ok} skip={skip} fail={fail}")
        except Exception as e:
            print(f"  [{idx}/{total}] {pid} 실패: {e}")
            fail += 1
        time.sleep(RATE)

    print(f"\n✅ 다운 완료: ok={ok} skip={skip} fail={fail} / total={total}")

if __name__ == "__main__":
    main()
