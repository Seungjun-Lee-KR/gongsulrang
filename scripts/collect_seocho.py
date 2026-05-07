"""
서초구 업무추진비 수집 (list + fetch + parse)

- 리스트: https://www.seocho.go.kr/site/seocho/ex/bbs/List.do?cbIdx=33&pageIndex={N}&pageUnit=30
- 상세:   .../site/seocho/ex/bbs/View.do?cbIdx=33&bcIdx={bcIdx}
- 첨부:   .../common/board/Download.do?bcIdx={bcIdx}&cbIdx=33&streFileNm={서버저장파일명}  (PDF)

- 출력:
  - output/seocho_posts.json
  - output/seocho_pdfs/{bcIdx}.pdf
  - output/seocho_expense_raw.csv
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
    FIELDS, RateLimiter, extract_records_from_pdf, record_to_csv,
    load_json, save_json, extract_dept_from_title,
)

OUT_DIR = "data/output"
POSTS = f"{OUT_DIR}/seocho_posts.json"
CACHE = f"{OUT_DIR}/.seocho_cache.json"
PDF_DIR = f"{OUT_DIR}/seocho_pdfs"
RAW_OUT = f"{OUT_DIR}/seocho_expense_raw.csv"

BASE = "https://www.seocho.go.kr"
LIST_URL = f"{BASE}/site/seocho/ex/bbs/List.do"
DETAIL_URL = f"{BASE}/site/seocho/ex/bbs/View.do"
DOWNLOAD_URL = f"{BASE}/common/board/Download.do"
LIST_PARAMS = {"cbIdx": "33", "pageUnit": "30"}
HEADERS = {"User-Agent": "Mozilla/5.0 (gongsulrang-collector; edu-research)",
           "Accept-Language": "ko,en;q=0.8"}
SINCE = datetime(2023, 9, 1)
RATE_LIST = 1.0
RATE_DETAIL = 0.8
RATE_DOWNLOAD = 0.5
DISTRICT = "서초구"


def fetch_list_page(session: requests.Session, page: int) -> list[dict]:
    params = dict(LIST_PARAMS, pageIndex=str(page))
    r = session.get(LIST_URL, params=params, headers=HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    rows = []
    for tr in soup.select("table tbody tr"):
        a = tr.find("a", href=re.compile(r"bcIdx=\d+"))
        if not a:
            continue
        m = re.search(r"bcIdx=(\d+)", a["href"])
        if not m:
            continue
        bc_idx = m.group(1)
        title = a.get_text(" ", strip=True)
        tds = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
        dept = ""
        date_str = ""
        for t in tds:
            if re.match(r"\d{4}[-./]\d{1,2}[-./]\d{1,2}", t):
                date_str = t.replace(".", "-")
            elif "과" in t or "동" in t or "실" in t or "담당관" in t or "단" in t:
                if len(t) <= 25 and not dept:
                    dept = t
        if not dept:
            dept = extract_dept_from_title(title, DISTRICT)
        rows.append({"id": bc_idx, "title": title, "dept": dept, "date": date_str})
    return rows


def fetch_detail_info(session: requests.Session, bc_idx: str) -> dict:
    params = dict(LIST_PARAMS, bcIdx=bc_idx)
    r = session.get(DETAIL_URL, params=params, headers=HEADERS, timeout=20)
    r.raise_for_status()
    # streFileNm 추출: /common/board/Download.do?bcIdx=X&cbIdx=33&streFileNm=YYYY
    m = re.search(r"Download\.do\?[^\"'\s]*streFileNm=([^&\"'\s]+)", r.text)
    stre = m.group(1) if m else ""
    # 파일명: 다운로드 링크 텍스트에 ".pdf"
    fname = ""
    mn = re.search(r'>\s*([^<>"\']+?\.pdf)\s*<', r.text, re.IGNORECASE)
    if mn:
        fname = mn.group(1).strip()
    return {"stre_file": stre, "pdf_name": fname}


def parse_date(s: str) -> datetime | None:
    s = (s or "").strip()
    for fmt in ("%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    return None


def stage_list(session: requests.Session, since_dt: datetime, max_pages: int):
    cache = load_json(CACHE, {"detail_done": {}}) or {"detail_done": {}}
    detail_done = cache.get("detail_done", {})
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

    todo = [pid for pid in all_posts if pid not in detail_done]
    print(f"[{DISTRICT}] detail fetch: {len(todo)}건")
    rate = RateLimiter(RATE_DETAIL)
    for i, pid in enumerate(todo, 1):
        try:
            info = fetch_detail_info(session, pid)
        except Exception as e:
            print(f"  [{i}/{len(todo)}] id={pid} err={e}")
            time.sleep(2)
            try:
                info = fetch_detail_info(session, pid)
            except Exception as e2:
                info = {"stre_file": "", "pdf_name": ""}
        all_posts[pid].update(info)
        detail_done[pid] = all_posts[pid]
        if i % 25 == 0 or i == len(todo):
            print(f"  [{i}/{len(todo)}] id={pid} stre={info.get('stre_file','')[:16]}")
            cache["detail_done"] = detail_done
            save_json(CACHE, cache)
        rate.wait()
    cache["detail_done"] = detail_done
    save_json(CACHE, cache)

    posts = sorted(all_posts.values(), key=lambda x: x.get("date", ""), reverse=True)
    save_json(POSTS, posts)
    n = sum(1 for p in posts if p.get("stre_file"))
    print(f"[{DISTRICT}] ✅ posts={len(posts)} (pdf 있음: {n}) → {POSTS}")


def stage_fetch(session: requests.Session):
    os.makedirs(PDF_DIR, exist_ok=True)
    posts = load_json(POSTS, []) or []
    todo = [p for p in posts if p.get("stre_file")]
    print(f"[{DISTRICT}] PDF 다운로드: {len(todo)}건")
    rate = RateLimiter(RATE_DOWNLOAD)
    n_ok = n_skip = n_err = 0
    for i, p in enumerate(todo, 1):
        path = os.path.join(PDF_DIR, f"{p['id']}.pdf")
        if os.path.exists(path) and os.path.getsize(path) > 1000:
            n_skip += 1
            continue
        try:
            params = {"bcIdx": p["id"], "cbIdx": "33", "streFileNm": p["stre_file"]}
            r = session.get(DOWNLOAD_URL, params=params, headers=HEADERS, timeout=30)
            r.raise_for_status()
            if not r.content.startswith(b"%PDF"):
                n_err += 1
                rate.wait()
                continue
            with open(path, "wb") as f:
                f.write(r.content)
            n_ok += 1
        except Exception as e:
            print(f"  [{i}/{len(todo)}] id={p['id']} err={e}")
            n_err += 1
        if i % 50 == 0 or i == len(todo):
            print(f"  [{i}/{len(todo)}] ok+={n_ok} skip={n_skip} err={n_err}")
        rate.wait()
    print(f"[{DISTRICT}] ✅ PDF: ok={n_ok} skip={n_skip} err={n_err} → {PDF_DIR}")


def stage_parse(limit: int = 0):
    posts = load_json(POSTS, []) or []
    targets = [p for p in posts if p.get("stre_file")]
    if limit > 0:
        targets = targets[:limit]
    print(f"[{DISTRICT}] 파싱 대상: {len(targets)}건")
    n_ok = n_err = n_records = 0
    with open(RAW_OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for i, p in enumerate(targets, 1):
            path = os.path.join(PDF_DIR, f"{p['id']}.pdf")
            if not os.path.exists(path):
                n_err += 1
                continue
            try:
                recs = extract_records_from_pdf(path)
            except Exception as e:
                print(f"  [{i}/{len(targets)}] id={p['id']} 파싱실패: {e}")
                n_err += 1
                continue
            dept = p.get("dept") or extract_dept_from_title(p.get("title", ""), DISTRICT)
            kept = 0
            for rec in recs:
                out = record_to_csv(rec, district=DISTRICT, dept=dept,
                                    source_id=f"seocho_{p['id']}")
                if out:
                    w.writerow(out)
                    kept += 1
            n_records += kept
            n_ok += 1
            if i % 50 == 0 or i == len(targets):
                print(f"  [{i}/{len(targets)}] id={p['id']} +{kept}행 누계={n_records}")
    print(f"[{DISTRICT}] ✅ PDFs ok={n_ok} err={n_err} records={n_records} → {RAW_OUT}")


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
