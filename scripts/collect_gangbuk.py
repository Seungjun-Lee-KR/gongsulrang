"""
강북구 업무추진비 공개 수집

- 리스트: https://www.gangbuk.go.kr/portal/intgty/deptJobPrtnCt/list.do?menuNo=200155&pageIndex={N}
  - 10 rows/page
  - td[0]=번호, td[1]=년도, td[2]=월, td[3]=작성부서, td[4]=구분, td[5]=파일, td[6]=작성일
  - 파일 다운로드 링크는 리스트에 직접 노출
- 파일:   /portal/intgty/deptJobPrtnCt/fileDownLoad.do?streFileNm=<file>&menuNo=200155
- 쿠키:   sabFingerPrint + sabSignature 필요 (WAF)
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
from collect_common import (
    FIELDS, RateLimiter, extract_records_from_pdf, extract_records_from_xlsx,
    record_to_csv, load_json, save_json, extract_dept_from_title,
)

OUT_DIR = "data/output"
POSTS = f"{OUT_DIR}/gangbuk_posts.json"
PDF_DIR = f"{OUT_DIR}/gangbuk_pdfs"
RAW_OUT = f"{OUT_DIR}/gangbuk_expense_raw.csv"

BASE = "https://www.gangbuk.go.kr"
LIST_URL = f"{BASE}/portal/intgty/deptJobPrtnCt/list.do"
DOWNLOAD_URL = f"{BASE}/portal/intgty/deptJobPrtnCt/fileDownLoad.do"
MENU_NO = "200155"
HEADERS = {"User-Agent": "Mozilla/5.0 (gongsulrang-collector; edu-research)",
           "Accept-Language": "ko,en;q=0.8"}
COOKIES = {
    "sabFingerPrint": "1920,1080,www.gangbuk.go.kr",
    "sabSignature": "lpBfserr4waUU17FJIQ/cg==",
}
SINCE = datetime(2023, 9, 1)
RATE_LIST = 1.0
RATE_DOWNLOAD = 0.5
DISTRICT = "강북구"

_FILE_RE = re.compile(r"fileDownLoad\.do\?streFileNm=([^&\"'\s<>]+)")


def parse_list_row(tr) -> dict | None:
    tds = tr.find_all("td", recursive=False)
    if len(tds) < 7:
        return None
    num = tds[0].get_text(" ", strip=True)
    if not num.isdigit():
        return None
    year = tds[1].get_text(" ", strip=True)
    month = tds[2].get_text(" ", strip=True)
    dept = tds[3].get_text(" ", strip=True)
    bimok = tds[4].get_text(" ", strip=True)
    m = _FILE_RE.search(str(tds[5]))
    ste = m.group(1) if m else ""
    date_str = tds[6].get_text(" ", strip=True).replace(".", "-")
    return {"id": num, "year": year, "month": month, "dept": dept,
            "bimok": bimok, "streFileNm": ste, "date": date_str}


def fetch_list_page(session: requests.Session, page: int) -> list[dict]:
    params = {"menuNo": MENU_NO, "pageIndex": str(page)}
    r = session.get(LIST_URL, params=params, headers=HEADERS,
                    cookies=COOKIES, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    rows = []
    for tr in soup.select("table tbody tr"):
        row = parse_list_row(tr)
        if row and row["id"]:
            rows.append(row)
    return rows


def parse_date(s: str) -> datetime | None:
    s = (s or "").strip()
    for fmt in ("%Y-%m-%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    return None


def stage_list(session: requests.Session, since_dt: datetime, max_pages: int):
    all_posts: dict[str, dict] = {p["id"]: p for p in load_json(POSTS, []) or []}
    rate = RateLimiter(RATE_LIST)
    print(f"[{DISTRICT}] list crawling since={since_dt.date()} max-pages={max_pages}")
    page = 1
    while page <= max_pages:
        try:
            rows = fetch_list_page(session, page)
        except Exception as e:
            print(f"  list cp={page} err={e}, retry 2s")
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
        in_range = out_range = 0
        oldest = None
        for row in rows:
            d = parse_date(row["date"])
            oldest = d if (oldest is None or (d and d < oldest)) else oldest
            if d is None or d >= since_dt:
                in_range += 1
                if row["id"] not in all_posts:
                    all_posts[row["id"]] = row
            else:
                out_range += 1
        if page % 20 == 0 or page <= 5:
            print(f"  cp={page}: rows={len(rows)} in={in_range} out={out_range} "
                  f"oldest={oldest.date() if oldest else '?'}")
        if rows and out_range == len(rows):
            print("  → 전체 범위 밖, 중단")
            break
        page += 1
        rate.wait()

    posts = sorted(all_posts.values(), key=lambda x: x.get("date", ""), reverse=True)
    save_json(POSTS, posts)
    n = sum(1 for p in posts if p.get("streFileNm"))
    print(f"[{DISTRICT}] ✅ posts={len(posts)} (파일: {n}) → {POSTS}")


def _detect_ext(content: bytes) -> str | None:
    if content.startswith(b"%PDF"):
        return "pdf"
    if content.startswith(b"PK\x03\x04"):
        return "xlsx"
    if content.startswith(b"\xd0\xcf\x11\xe0"):
        return "xls"
    return None


def _existing_path(base_id: str) -> str | None:
    for ext in ("pdf", "xlsx", "xls"):
        p = os.path.join(PDF_DIR, f"{base_id}.{ext}")
        if os.path.exists(p) and os.path.getsize(p) > 1000:
            return p
    return None


def stage_fetch(session: requests.Session):
    os.makedirs(PDF_DIR, exist_ok=True)
    posts = load_json(POSTS, []) or []
    todo = [p for p in posts if p.get("streFileNm")]
    print(f"[{DISTRICT}] 파일 다운로드: {len(todo)}건")
    rate = RateLimiter(RATE_DOWNLOAD)
    n_ok = n_skip = n_err = 0
    for i, p in enumerate(todo, 1):
        if _existing_path(p["id"]):
            n_skip += 1
            continue
        try:
            referer = f"{LIST_URL}?menuNo={MENU_NO}"
            r = session.get(DOWNLOAD_URL,
                            params={"streFileNm": p["streFileNm"], "menuNo": MENU_NO},
                            headers=dict(HEADERS, Referer=referer),
                            cookies=COOKIES, timeout=30)
            r.raise_for_status()
            ext = _detect_ext(r.content)
            if not ext:
                n_err += 1
                rate.wait()
                continue
            path = os.path.join(PDF_DIR, f"{p['id']}.{ext}")
            with open(path, "wb") as f:
                f.write(r.content)
            n_ok += 1
        except Exception as e:
            print(f"  [{i}/{len(todo)}] id={p['id']} err={e}")
            n_err += 1
        if i % 100 == 0 or i == len(todo):
            print(f"  [{i}/{len(todo)}] ok+={n_ok} skip={n_skip} err={n_err}")
        rate.wait()
    print(f"[{DISTRICT}] ✅ 다운로드 ok={n_ok} skip={n_skip} err={n_err} → {PDF_DIR}")


def stage_parse(limit: int = 0):
    posts = load_json(POSTS, []) or []
    targets = [p for p in posts if p.get("streFileNm")]
    if limit > 0:
        targets = targets[:limit]
    print(f"[{DISTRICT}] 파싱 대상: {len(targets)}건")
    n_ok = n_err = n_records = 0
    with open(RAW_OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for i, p in enumerate(targets, 1):
            path = _existing_path(p["id"])
            if not path:
                n_err += 1
                continue
            try:
                if path.endswith(".pdf"):
                    recs = extract_records_from_pdf(path)
                else:
                    recs = extract_records_from_xlsx(path)
            except Exception as e:
                print(f"  [{i}/{len(targets)}] id={p['id']} 파싱실패: {e}")
                n_err += 1
                continue
            dept = p.get("dept", "") or ""
            kept = 0
            for rec in recs:
                out = record_to_csv(rec, district=DISTRICT, dept=dept,
                                    source_id=f"gangbuk_{p['id']}")
                if out:
                    w.writerow(out)
                    kept += 1
            n_records += kept
            n_ok += 1
            if i % 50 == 0 or i == len(targets):
                print(f"  [{i}/{len(targets)}] id={p['id']} +{kept} 누계={n_records}")
    print(f"[{DISTRICT}] ✅ 파싱 ok={n_ok} err={n_err} records={n_records} → {RAW_OUT}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["list", "fetch", "parse", "all"], default="all")
    ap.add_argument("--since", default=SINCE.strftime("%Y-%m-%d"))
    ap.add_argument("--max-pages", type=int, default=1500)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    since_dt = datetime.strptime(args.since, "%Y-%m-%d")

    session = requests.Session()
    if args.stage in ("list", "all"):
        stage_list(session, since_dt, args.max_pages)
    if args.stage in ("fetch", "all"):
        stage_fetch(session)
    if args.stage in ("parse", "all"):
        stage_parse(args.limit)


if __name__ == "__main__":
    main()
