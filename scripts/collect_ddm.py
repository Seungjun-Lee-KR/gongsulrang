"""
동대문구 업무추진비 공개 수집 (list + fetch + parse)

- 리스트: https://www.ddm.go.kr/www/selectBbsNttList.do?bbsNo=160&key=152&pageUnit=30&pageIndex={N}
  - <table class="p-table"> tbody tr. td[0]=번호, td[1]=제목(a→nttNo), td[2]=부서, td[3]=작성일, td[4]=파일존재표시
- 상세:   /www/selectBbsNttView.do?bbsNo=160&key=152&nttNo=...
  - ./downloadBbsFile.do?atchmnflNo=NNN  형식 (1~2개)
- 파일:   /www/downloadBbsFile.do?atchmnflNo=NNN  (PDF/XLSX)

- 출력:
  - output/ddm_posts.json
  - output/ddm_pdfs/{nttNo}_{sn}.{pdf|xlsx|xls}
  - output/ddm_expense_raw.csv
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
POSTS = f"{OUT_DIR}/ddm_posts.json"
CACHE = f"{OUT_DIR}/.ddm_cache.json"
PDF_DIR = f"{OUT_DIR}/ddm_pdfs"
RAW_OUT = f"{OUT_DIR}/ddm_expense_raw.csv"

BASE = "https://www.ddm.go.kr"
LIST_URL = f"{BASE}/www/selectBbsNttList.do"
VIEW_URL = f"{BASE}/www/selectBbsNttView.do"
DOWNLOAD_URL = f"{BASE}/www/downloadBbsFile.do"
LIST_PARAMS = {"bbsNo": "160", "key": "152"}
HEADERS = {"User-Agent": "Mozilla/5.0 (gongsulrang-collector; edu-research)",
           "Accept-Language": "ko,en;q=0.8"}
SINCE = datetime(2023, 9, 1)
RATE_LIST = 1.0
RATE_DETAIL = 0.7
RATE_DOWNLOAD = 0.5
DISTRICT = "동대문구"


def parse_list_row(tr) -> dict | None:
    tds = tr.find_all("td", recursive=False)
    if len(tds) < 5:
        return None
    a = tds[1].find("a", href=True)
    if not a:
        return None
    m = re.search(r"nttNo=(\d+)", a["href"])
    if not m:
        return None
    ntt_id = m.group(1)
    title = a.get_text(" ", strip=True)
    dept = tds[2].get_text(" ", strip=True)
    date_str = tds[3].get_text(" ", strip=True)
    has_file = "파일" in tds[4].get_text(" ", strip=True)
    return {"id": ntt_id, "title": title, "dept": dept, "date": date_str,
            "has_file": has_file}


def fetch_list_page(session: requests.Session, page: int) -> list[dict]:
    params = dict(LIST_PARAMS, pageUnit="30", pageIndex=str(page))
    r = session.get(LIST_URL, params=params, headers=HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    rows = []
    for tr in soup.select("table.p-table tbody tr"):
        row = parse_list_row(tr)
        if row and row["id"]:
            rows.append(row)
    return rows


def fetch_detail_files(session: requests.Session, ntt_id: str) -> list[str]:
    """상세 페이지에서 downloadBbsFile.do?atchmnflNo=... 추출 (중복 제거)"""
    params = dict(LIST_PARAMS, nttNo=ntt_id, pageIndex="1")
    r = session.get(VIEW_URL, params=params, headers=HEADERS, timeout=20)
    r.raise_for_status()
    seen = []
    seen_set = set()
    for m in re.finditer(r"downloadBbsFile\.do\?atchmnflNo=(\d+)", r.text):
        v = m.group(1)
        if v in seen_set:
            continue
        seen_set.add(v)
        seen.append(v)
    return seen


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

    # 상세 페이지에서 파일 번호 획득 (캐시)
    todo = [p for p in all_posts.values() if p.get("has_file") and p["id"] not in detail_done]
    print(f"[{DISTRICT}] detail fetch: {len(todo)}건")
    rate = RateLimiter(RATE_DETAIL)
    for i, p in enumerate(todo, 1):
        try:
            atchs = fetch_detail_files(session, p["id"])
        except Exception as e:
            print(f"  [{i}/{len(todo)}] id={p['id']} err={e}")
            time.sleep(2)
            try:
                atchs = fetch_detail_files(session, p["id"])
            except Exception as e2:
                atchs = []
        p["atchs"] = atchs
        detail_done[p["id"]] = True
        if i % 50 == 0 or i == len(todo):
            print(f"  [{i}/{len(todo)}] id={p['id']} atchs={len(atchs)}")
            cache["detail_done"] = detail_done
            save_json(CACHE, cache)
        rate.wait()
    cache["detail_done"] = detail_done
    save_json(CACHE, cache)

    posts = sorted(all_posts.values(), key=lambda x: x.get("date", ""), reverse=True)
    save_json(POSTS, posts)
    n = sum(1 for p in posts if p.get("atchs"))
    print(f"[{DISTRICT}] ✅ posts={len(posts)} (파일 있음: {n}) → {POSTS}")


def _detect_ext(content: bytes) -> str | None:
    if content.startswith(b"%PDF"):
        return "pdf"
    if content.startswith(b"PK\x03\x04"):
        return "xlsx"
    if content.startswith(b"\xd0\xcf\x11\xe0"):
        return "xls"
    return None


def _existing_path(base_id: str, sn: int) -> str | None:
    for ext in ("pdf", "xlsx", "xls"):
        p = os.path.join(PDF_DIR, f"{base_id}_{sn}.{ext}")
        if os.path.exists(p) and os.path.getsize(p) > 1000:
            return p
    return None


def stage_fetch(session: requests.Session):
    os.makedirs(PDF_DIR, exist_ok=True)
    posts = load_json(POSTS, []) or []
    todo = [p for p in posts if p.get("atchs")]
    total = sum(len(p["atchs"]) for p in todo)
    print(f"[{DISTRICT}] 파일 다운로드: 게시글 {len(todo)}건 / 파일 {total}개")
    rate = RateLimiter(RATE_DOWNLOAD)
    n_ok = n_skip = n_err = 0
    for i, p in enumerate(todo, 1):
        for sn, atch in enumerate(p["atchs"], 1):
            if _existing_path(p["id"], sn):
                n_skip += 1
                continue
            try:
                r = session.get(DOWNLOAD_URL, params={"atchmnflNo": atch},
                                headers=HEADERS, timeout=30)
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
    print(f"[{DISTRICT}] ✅ 다운로드: ok={n_ok} skip={n_skip} err={n_err} → {PDF_DIR}")


def stage_parse(limit: int = 0):
    posts = load_json(POSTS, []) or []
    targets = [p for p in posts if p.get("atchs")]
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
            for sn, _ in enumerate(p["atchs"], 1):
                path = _existing_path(p["id"], sn)
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
                                        source_id=f"ddm_{p['id']}_{sn}")
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
