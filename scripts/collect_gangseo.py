"""
강서구 업무추진비 공개 수집

- 리스트: https://www.gangseo.seoul.kr/gs030325?curPage={N}
  - td[0]=번호, td[1]=제목+post link, td[3]=부서, td[4]=날짜
  - 상세 URL: /gs030325/<postNo>
- 파일:   /comm/getFile?srvcId=BBSTY1&upperNo=<hash>&fileTy=ATTACH&fileNo=<hash>
  (상세 페이지 진입 후 추출, 한 게시물에 여러 개 가능)
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
POSTS = f"{OUT_DIR}/gangseo_posts.json"
CACHE = f"{OUT_DIR}/.gangseo_cache.json"
PDF_DIR = f"{OUT_DIR}/gangseo_pdfs"
RAW_OUT = f"{OUT_DIR}/gangseo_expense_raw.csv"

BASE = "https://www.gangseo.seoul.kr"
LIST_URL = f"{BASE}/gs030325"
HEADERS = {"User-Agent": "Mozilla/5.0 (gongsulrang-collector; edu-research)",
           "Accept-Language": "ko,en;q=0.8"}
SINCE = datetime(2023, 9, 1)
RATE_LIST = 1.0
RATE_DETAIL = 0.7
RATE_DOWNLOAD = 0.5
DISTRICT = "강서구"

_POSTID_RE = re.compile(r"/gs030325/(\d+)")
_FILE_RE = re.compile(r"/comm/getFile\?srvcId=BBSTY1&upperNo=([^&\"\'\s]+)&fileTy=ATTACH&fileNo=([^&\"\'\s<>]+)")


def parse_list_row(tr) -> dict | None:
    tds = tr.find_all("td", recursive=False)
    if len(tds) < 5:
        return None
    a = tds[1].find("a", href=True)
    if not a:
        return None
    m = _POSTID_RE.search(a["href"])
    if not m:
        return None
    post_id = m.group(1)
    title = a.get_text(" ", strip=True)
    dept = tds[3].get_text(" ", strip=True)
    date_str = tds[4].get_text(" ", strip=True).replace(".", "-")
    return {"id": post_id, "title": title, "dept": dept, "date": date_str}


def fetch_list_page(session: requests.Session, page: int) -> list[dict]:
    r = session.get(LIST_URL, params={"curPage": str(page)}, headers=HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    rows = []
    for tr in soup.select("table tbody tr"):
        row = parse_list_row(tr)
        if row and row["id"]:
            rows.append(row)
    return rows


def fetch_detail_files(session: requests.Session, post_id: str) -> list[tuple[str, str]]:
    r = session.get(f"{LIST_URL}/{post_id}", headers=HEADERS, timeout=20)
    r.raise_for_status()
    files = []
    seen = set()
    for m in _FILE_RE.finditer(r.text):
        key = (m.group(1), m.group(2))
        if key in seen:
            continue
        seen.add(key)
        files.append(key)
    return files


def parse_date(s: str) -> datetime | None:
    s = (s or "").strip()
    for fmt in ("%Y-%m-%d", "%Y.%m.%d"):
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
            files = fetch_detail_files(session, pid)
        except Exception as e:
            print(f"  [{i}/{len(todo)}] id={pid} err={e}")
            files = []
        all_posts[pid]["files"] = [{"upperNo": u, "fileNo": f} for u, f in files]
        detail_done[pid] = {"files": all_posts[pid]["files"]}
        if i % 50 == 0 or i == len(todo):
            print(f"  [{i}/{len(todo)}] id={pid} files={len(files)}")
            cache["detail_done"] = detail_done
            save_json(CACHE, cache)
        rate.wait()
    cache["detail_done"] = detail_done
    save_json(CACHE, cache)

    posts = sorted(all_posts.values(), key=lambda x: x.get("date", ""), reverse=True)
    save_json(POSTS, posts)
    n = sum(1 for p in posts if p.get("files"))
    print(f"[{DISTRICT}] ✅ posts={len(posts)} (파일 있음: {n}) → {POSTS}")


def _detect_ext(content: bytes) -> str | None:
    if content.startswith(b"%PDF"):
        return "pdf"
    if content.startswith(b"PK\x03\x04"):
        return "xlsx"
    if content.startswith(b"\xd0\xcf\x11\xe0"):
        return "xls"
    return None


def _has_file(base_id: str, sn: int) -> bool:
    for ext in ("pdf", "xlsx", "xls"):
        p = os.path.join(PDF_DIR, f"{base_id}_{sn}.{ext}")
        if os.path.exists(p) and os.path.getsize(p) > 1000:
            return True
    return False


def stage_fetch(session: requests.Session):
    os.makedirs(PDF_DIR, exist_ok=True)
    posts = load_json(POSTS, []) or []
    todo = [p for p in posts if p.get("files")]
    print(f"[{DISTRICT}] 파일 다운로드: {len(todo)}건")
    rate = RateLimiter(RATE_DOWNLOAD)
    n_ok = n_skip = n_err = 0
    for i, p in enumerate(todo, 1):
        referer = f"{LIST_URL}/{p['id']}"
        for sn, f in enumerate(p["files"], 1):
            if _has_file(p["id"], sn):
                n_skip += 1
                continue
            try:
                url = (f"{BASE}/comm/getFile?srvcId=BBSTY1&upperNo={f['upperNo']}"
                       f"&fileTy=ATTACH&fileNo={f['fileNo']}")
                r = session.get(url, headers=dict(HEADERS, Referer=referer), timeout=30)
                r.raise_for_status()
                ext = _detect_ext(r.content)
                if not ext:
                    n_err += 1
                    rate.wait()
                    continue
                path = os.path.join(PDF_DIR, f"{p['id']}_{sn}.{ext}")
                with open(path, "wb") as fh:
                    fh.write(r.content)
                n_ok += 1
            except Exception as e:
                print(f"  [{i}/{len(todo)}] id={p['id']} sn={sn} err={e}")
                n_err += 1
            rate.wait()
        if i % 100 == 0 or i == len(todo):
            print(f"  [{i}/{len(todo)}] ok+={n_ok} skip={n_skip} err={n_err}")
    print(f"[{DISTRICT}] ✅ 파일 ok={n_ok} skip={n_skip} err={n_err} → {PDF_DIR}")


def stage_parse(limit: int = 0):
    posts = load_json(POSTS, []) or []
    targets = [p for p in posts if p.get("files")]
    if limit > 0:
        targets = targets[:limit]
    print(f"[{DISTRICT}] 파싱 대상: {len(targets)}건")
    n_ok = n_err = n_records = 0
    with open(RAW_OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for i, p in enumerate(targets, 1):
            dept = p.get("dept") or extract_dept_from_title(p.get("title", ""), DISTRICT)
            kept = 0
            for sn in range(1, len(p["files"]) + 1):
                path = None
                for ext in ("pdf", "xlsx", "xls"):
                    px = os.path.join(PDF_DIR, f"{p['id']}_{sn}.{ext}")
                    if os.path.exists(px):
                        path = px
                        break
                if not path:
                    continue
                try:
                    if path.endswith(".pdf"):
                        recs = extract_records_from_pdf(path)
                    else:
                        recs = extract_records_from_xlsx(path)
                except Exception as e:
                    print(f"  [{i}/{len(targets)}] id={p['id']} sn={sn} 파싱실패: {e}")
                    n_err += 1
                    continue
                for rec in recs:
                    out = record_to_csv(rec, district=DISTRICT, dept=dept,
                                        source_id=f"gangseo_{p['id']}_{sn}")
                    if out:
                        w.writerow(out)
                        kept += 1
            if kept > 0:
                n_ok += 1
            n_records += kept
            if i % 50 == 0 or i == len(targets):
                print(f"  [{i}/{len(targets)}] id={p['id']} 누계={n_records}")
    print(f"[{DISTRICT}] ✅ 파싱 ok={n_ok} err={n_err} records={n_records} → {RAW_OUT}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["list", "fetch", "parse", "all"], default="all")
    ap.add_argument("--since", default=SINCE.strftime("%Y-%m-%d"))
    ap.add_argument("--max-pages", type=int, default=600)
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
