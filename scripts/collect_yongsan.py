"""
용산구 업무추진비 공개 수집 (list + fetch + parse)

- 리스트: http://market.yongsan.go.kr/portal/bbs/B0000030/list.do?menuNo=200140&pageIndex={N}
- 상세:   /portal/bbs/B0000030/view.do?nttId={nttId}&menuNo=200140
- 첨부:   /portal/cmmn/file/fileDown.do?menuNo=200140&atchFileId=X&fileSn=1  (PDF/XLSX 혼재)

- 출력:
  - output/yongsan_posts.json
  - output/yongsan_pdfs/{nttId}.(pdf|xlsx)
  - output/yongsan_expense_raw.csv
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
POSTS = f"{OUT_DIR}/yongsan_posts.json"
PDF_DIR = f"{OUT_DIR}/yongsan_pdfs"
RAW_OUT = f"{OUT_DIR}/yongsan_expense_raw.csv"

BASE = "http://market.yongsan.go.kr"
LIST_URL = f"{BASE}/portal/bbs/B0000030/list.do"
DOWNLOAD_URL = f"{BASE}/portal/cmmn/file/fileDown.do"
LIST_PARAMS = {"menuNo": "200140"}
HEADERS = {"User-Agent": "Mozilla/5.0 (gongsulrang-collector; edu-research)",
           "Accept-Language": "ko,en;q=0.8"}
SINCE = datetime(2023, 9, 1)
RATE_LIST = 1.0
RATE_DOWNLOAD = 0.5
DISTRICT = "용산구"


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


def fetch_list_page(session: requests.Session, page: int) -> list[dict]:
    params = dict(LIST_PARAMS, pageIndex=str(page))
    r = session.get(LIST_URL, params=params, headers=HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    rows = []
    for tr in soup.select("table tbody tr"):
        a_title = tr.find("a", href=re.compile(r"view\.do\?nttId=\d+"))
        if not a_title:
            continue
        m = re.search(r"nttId=(\d+)", a_title["href"])
        if not m:
            continue
        ntt_id = m.group(1)
        title = a_title.get_text(" ", strip=True)
        tds = tr.find_all("td")

        dept = ""
        date_str = ""
        atch_id = ""
        file_sn = "1"
        for td in tds:
            t = td.get_text(" ", strip=True)
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", t):
                date_str = t
            elif any(sfx in t for sfx in ("과", "실", "단", "담당관", "동")) and 2 <= len(t) <= 25 and not dept:
                if "업무추진비" not in t:
                    dept = t
            a_file = td.find("a", href=re.compile(r"atchFileId="))
            if a_file and not atch_id:
                mx = re.search(r"atchFileId=([a-f0-9]+)", a_file["href"])
                if mx:
                    atch_id = mx.group(1)
                ms = re.search(r"fileSn=(\d+)", a_file["href"])
                if ms:
                    file_sn = ms.group(1)
        if not dept:
            dept = extract_dept_from_title(title, DISTRICT)
        rows.append({"id": ntt_id, "title": title, "dept": dept,
                     "date": date_str, "atch_file_id": atch_id, "file_sn": file_sn})
    return rows


def parse_date(s: str) -> datetime | None:
    s = (s or "").strip()
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
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
        print(f"  cp={page}: rows={len(rows)} in={in_range} out={out_range} oldest={oldest.date() if oldest else '?'}")
        if rows and out_range == len(rows):
            print("  → 전체 범위 밖, 중단")
            break
        page += 1
        rate.wait()

    posts = sorted(all_posts.values(), key=lambda x: x.get("date", ""), reverse=True)
    save_json(POSTS, posts)
    n = sum(1 for p in posts if p.get("atch_file_id"))
    print(f"[{DISTRICT}] ✅ posts={len(posts)} (pdf/xlsx 있음: {n}) → {POSTS}")


def stage_fetch(session: requests.Session):
    os.makedirs(PDF_DIR, exist_ok=True)
    posts = load_json(POSTS, []) or []
    todo = [p for p in posts if p.get("atch_file_id")]
    print(f"[{DISTRICT}] 파일 다운로드: {len(todo)}건")
    rate = RateLimiter(RATE_DOWNLOAD)
    n_ok = n_skip = n_err = 0
    for i, p in enumerate(todo, 1):
        if _existing_path(p["id"]):
            n_skip += 1
            continue
        try:
            params = {"menuNo": "200140", "atchFileId": p["atch_file_id"],
                      "fileSn": p.get("file_sn", "1")}
            r = session.get(DOWNLOAD_URL, params=params, headers=HEADERS, timeout=30)
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
    print(f"[{DISTRICT}] ✅ 다운로드: ok={n_ok} skip={n_skip} err={n_err} → {PDF_DIR}")


def stage_parse(limit: int = 0):
    posts = load_json(POSTS, []) or []
    targets = [p for p in posts if p.get("atch_file_id")]
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
            dept = p.get("dept") or extract_dept_from_title(p.get("title", ""), DISTRICT)
            kept = 0
            for rec in recs:
                out = record_to_csv(rec, district=DISTRICT, dept=dept,
                                    source_id=f"yongsan_{p['id']}")
                if out:
                    w.writerow(out)
                    kept += 1
            n_records += kept
            n_ok += 1
            if i % 100 == 0 or i == len(targets):
                print(f"  [{i}/{len(targets)}] id={p['id']} +{kept}행 누계={n_records}")
    print(f"[{DISTRICT}] ✅ 파싱 ok={n_ok} err={n_err} records={n_records} → {RAW_OUT}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["list", "fetch", "parse", "all"], default="all")
    ap.add_argument("--since", default=SINCE.strftime("%Y-%m-%d"))
    ap.add_argument("--max-pages", type=int, default=300)
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
