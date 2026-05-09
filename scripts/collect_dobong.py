"""
도봉구 업무추진비 공개 수집 (ASP 기반)

- 리스트: https://www.dobong.go.kr/bbs.asp?intPage={N}&code=10008860
  - td[0]=번호, td[1]=제목+pcode, td[2]=날짜, td[3]=부서, td[4]=조회
- 상세:   /bbs.asp?bmode=D&pcode=<PCODE>&intPage=1&code=10008860
  - 파일 link: /WDB_common/include/download.asp?fcode=<F>&bcode=387
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
POSTS = f"{OUT_DIR}/dobong_posts.json"
CACHE = f"{OUT_DIR}/.dobong_cache.json"
PDF_DIR = f"{OUT_DIR}/dobong_pdfs"
RAW_OUT = f"{OUT_DIR}/dobong_expense_raw.csv"

BASE = "https://www.dobong.go.kr"
LIST_URL = f"{BASE}/bbs.asp"
DOWNLOAD_URL = f"{BASE}/WDB_common/include/download.asp"
CODE = "10008860"
HEADERS = {"User-Agent": "Mozilla/5.0 (gongsulrang-collector; edu-research)",
           "Accept-Language": "ko,en;q=0.8"}
SINCE = datetime(2023, 9, 1)
RATE_LIST = 1.0
RATE_DETAIL = 0.7
RATE_DOWNLOAD = 0.5
DISTRICT = "도봉구"

_PCODE_RE = re.compile(r"pcode=(\d+)")
_FILE_RE = re.compile(r"download\.asp\?fcode=(\d+)(?:&(?:amp;)?bcode=(\d+))?", re.I)


def parse_list_row(tr) -> dict | None:
    tds = tr.find_all("td", recursive=False)
    if len(tds) < 4:
        return None
    a = tds[1].find("a", href=True)
    if not a:
        return None
    m = _PCODE_RE.search(a["href"])
    if not m:
        return None
    pcode = m.group(1)
    title = a.get_text(" ", strip=True)
    date_str = tds[2].get_text(" ", strip=True).replace(".", "-")
    dept = tds[3].get_text(" ", strip=True)
    return {"id": pcode, "title": title, "dept": dept, "date": date_str}


def fetch_list_page(session: requests.Session, page: int) -> list[dict]:
    params = {"intPage": str(page), "code": CODE}
    r = session.get(LIST_URL, params=params, headers=HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    rows = []
    for tr in soup.select("table tbody tr"):
        row = parse_list_row(tr)
        if row and row["id"]:
            rows.append(row)
    return rows


def fetch_detail_file(session: requests.Session, pcode: str) -> tuple[str, str]:
    params = {"bmode": "D", "pcode": pcode, "intPage": "1", "code": CODE}
    r = session.get(LIST_URL, params=params, headers=HEADERS, timeout=20)
    r.raise_for_status()
    m = _FILE_RE.search(r.text)
    if not m:
        return "", ""
    return m.group(1), m.group(2) or "387"


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
    no_new_streak = 0
    NO_NEW_LIMIT = 2
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
        new_added = 0
        oldest = None
        for row in rows:
            d = parse_date(row["date"])
            oldest = d if (oldest is None or (d and d < oldest)) else oldest
            if d is None or d >= since_dt:
                in_range += 1
                if row["id"] not in all_posts:
                    all_posts[row["id"]] = row
                    new_added += 1
            else:
                out_range += 1
        print(f"  cp={page}: rows={len(rows)} in={in_range} out={out_range} oldest={oldest.date() if oldest else '?'}")
        if rows and out_range == len(rows):
            print("  → 전체 범위 밖, 중단")
            break
        if new_added == 0:
            no_new_streak += 1
            if no_new_streak >= NO_NEW_LIMIT:
                print(f"  → {NO_NEW_LIMIT}페이지 연속 신규 게시물 없음, 중단")
                break
        else:
            no_new_streak = 0
        page += 1
        rate.wait()

    todo = [pid for pid in all_posts if pid not in detail_done]
    print(f"[{DISTRICT}] detail fetch: {len(todo)}건")
    rate = RateLimiter(RATE_DETAIL)
    for i, pid in enumerate(todo, 1):
        try:
            fcode, bcode = fetch_detail_file(session, pid)
        except Exception as e:
            print(f"  [{i}/{len(todo)}] id={pid} err={e}")
            fcode, bcode = "", ""
        all_posts[pid]["fcode"] = fcode
        all_posts[pid]["bcode"] = bcode
        detail_done[pid] = {"fcode": fcode, "bcode": bcode}
        if i % 50 == 0 or i == len(todo):
            print(f"  [{i}/{len(todo)}] id={pid} fcode={fcode}")
            cache["detail_done"] = detail_done
            save_json(CACHE, cache)
        rate.wait()
    cache["detail_done"] = detail_done
    save_json(CACHE, cache)

    posts = sorted(all_posts.values(), key=lambda x: x.get("date", ""), reverse=True)
    save_json(POSTS, posts)
    n = sum(1 for p in posts if p.get("fcode"))
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
    todo = [p for p in posts if p.get("fcode")]
    print(f"[{DISTRICT}] 파일 다운로드: {len(todo)}건")
    rate = RateLimiter(RATE_DOWNLOAD)
    n_ok = n_skip = n_err = 0
    for i, p in enumerate(todo, 1):
        if _existing_path(p["id"]):
            n_skip += 1
            continue
        try:
            referer = f"{LIST_URL}?bmode=D&pcode={p['id']}&intPage=1&code={CODE}"
            r = session.get(DOWNLOAD_URL,
                            params={"fcode": p["fcode"], "bcode": p.get("bcode", "387")},
                            headers=dict(HEADERS, Referer=referer), timeout=30)
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
    targets = [p for p in posts if p.get("fcode")]
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
                                    source_id=f"dobong_{p['id']}")
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
    ap.add_argument("--max-pages", type=int, default=400)
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
