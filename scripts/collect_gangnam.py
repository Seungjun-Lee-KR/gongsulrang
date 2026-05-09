"""
강남구 업무추진비 수집 — 리스트 페이지에 XLS 직접 노출

- 리스트: https://www.gangnam.go.kr/board/B_000673/list.do?mid=ID05_04200502&pageIndex={N}
- 각 tr에 파일 URL /file/1/get/{uuid}/download.do 노출 → 상세 페이지 불필요
- 출력:
  - output/gangnam_posts.json
  - output/gangnam_xlss/{uuid}.xls
  - output/gangnam_expense_raw.csv
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
    FIELDS, RateLimiter, extract_records_from_xls, record_to_csv,
    load_json, save_json, extract_dept_from_title, clean_cell,
)

OUT_DIR = "data/output"
POSTS = f"{OUT_DIR}/gangnam_posts.json"
CACHE = f"{OUT_DIR}/.gangnam_cache.json"
XLS_DIR = f"{OUT_DIR}/gangnam_xlss"
RAW_OUT = f"{OUT_DIR}/gangnam_expense_raw.csv"

BASE = "https://www.gangnam.go.kr"
LIST_URL = f"{BASE}/board/B_000673/list.do"
LIST_PARAMS = {"mid": "ID05_04200502"}
HEADERS = {"User-Agent": "Mozilla/5.0 (gongsulrang-collector; edu-research)",
           "Accept-Language": "ko,en;q=0.8"}
SINCE = datetime(2023, 9, 1)
RATE_LIST = 1.0
RATE_DOWNLOAD = 0.5
DISTRICT = "강남구"


def fetch_list_page(session: requests.Session, page: int) -> list[dict]:
    params = dict(LIST_PARAMS, pgno=str(page))
    r = session.get(LIST_URL, params=params, headers=HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    rows = []
    for tr in soup.select("table tbody tr"):
        tds = tr.find_all("td")
        if len(tds) < 3:
            continue
        num_td = clean_cell(tds[0].get_text(" ", strip=True))
        # 공지(NEW) 등 비숫자 건너뛰기
        if not re.match(r"^\d+$", num_td):
            continue
        post_id = num_td
        title_a = tr.find("a")
        title = clean_cell(title_a.get_text(" ", strip=True)) if title_a else ""
        # 파일 다운로드 a
        file_a = tr.find("a", href=re.compile(r"/file/\d+/get/[^/]+/download\.do"))
        file_url = file_a["href"] if file_a else ""
        m = re.search(r"/file/\d+/get/([^/]+)/download\.do", file_url)
        uuid = m.group(1) if m else ""
        # 파일명 (alt)
        img = file_a.find("img") if file_a else None
        file_name = (img.get("alt") or "").replace(" 다운로드", "").strip() if img else ""
        # 부서: td 4번째 또는 파일명에서 괄호 안
        dept = ""
        for t in tds[2:]:
            txt = clean_cell(t.get_text(" ", strip=True))
            if not txt:
                continue
            if re.match(r"^\d{4}[-./]\d{1,2}[-./]\d{1,2}$", txt):
                date_str = txt.replace(".", "-")
                continue
            if "과" in txt or "동" in txt or "실" in txt or "담당관" in txt or "단" in txt:
                if len(txt) <= 25:
                    dept = txt
                    break
        date_str = ""
        for t in tds:
            txt = clean_cell(t.get_text(" ", strip=True))
            if re.match(r"\d{4}[-./]\d{1,2}[-./]\d{1,2}", txt):
                date_str = txt.replace(".", "-")
        if not dept and file_name:
            mm = re.search(r"\(([^)]+)\)\.xls", file_name)
            if mm:
                dept = mm.group(1).strip()
        if not dept:
            dept = extract_dept_from_title(title, DISTRICT)
        rows.append({
            "id": post_id,
            "title": title,
            "dept": dept,
            "date": date_str,
            "uuid": uuid,
            "file_url": file_url,
            "file_name": file_name,
        })
    return rows


def parse_date(s: str) -> datetime | None:
    s = (s or "").strip()
    for fmt in ("%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    return None


def stage_list(session: requests.Session, since_dt: datetime, max_pages: int):
    all_posts: dict[str, dict] = {p["id"]: p for p in (load_json(POSTS, []) or [])}
    rate = RateLimiter(RATE_LIST)
    print(f"[{DISTRICT}] list crawling since={since_dt.date()} max-pages={max_pages}")
    page = 1
    no_new_streak = 0
    NO_NEW_LIMIT = 2
    while page <= max_pages:
        try:
            rows = fetch_list_page(session, page)
        except Exception as e:
            print(f"  cp={page} err={e}, 2s 재시도")
            time.sleep(2)
            try:
                rows = fetch_list_page(session, page)
            except Exception as e2:
                print(f"    실패: {e2}")
                break
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
            print("  → 범위 밖, 중단")
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

    posts = sorted(all_posts.values(), key=lambda x: x.get("date",""), reverse=True)
    save_json(POSTS, posts)
    n = sum(1 for p in posts if p.get("uuid"))
    print(f"[{DISTRICT}] ✅ posts={len(posts)} (xls 있음: {n}) → {POSTS}")


def stage_fetch(session: requests.Session):
    os.makedirs(XLS_DIR, exist_ok=True)
    posts = load_json(POSTS, []) or []
    todo = [p for p in posts if p.get("uuid")]
    print(f"[{DISTRICT}] XLS 다운로드: {len(todo)}건")
    rate = RateLimiter(RATE_DOWNLOAD)
    n_ok = n_skip = n_err = 0
    for i, p in enumerate(todo, 1):
        path = os.path.join(XLS_DIR, f"{p['uuid']}.xls")
        if os.path.exists(path) and os.path.getsize(path) > 500:
            n_skip += 1
            continue
        try:
            url = BASE + p["file_url"] if p["file_url"].startswith("/") else p["file_url"]
            r = session.get(url, headers=HEADERS, timeout=30)
            r.raise_for_status()
            if len(r.content) < 500:
                n_err += 1
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
    print(f"[{DISTRICT}] ✅ XLS: ok={n_ok} skip={n_skip} err={n_err} → {XLS_DIR}")


def stage_parse(limit: int = 0):
    posts = load_json(POSTS, []) or []
    targets = [p for p in posts if p.get("uuid")]
    if limit > 0:
        targets = targets[:limit]
    print(f"[{DISTRICT}] 파싱 대상: {len(targets)}건")
    n_ok = n_err = n_records = 0
    with open(RAW_OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for i, p in enumerate(targets, 1):
            path = os.path.join(XLS_DIR, f"{p['uuid']}.xls")
            if not os.path.exists(path):
                n_err += 1
                continue
            # 파일 포맷 감지 (확장자 .xls 여도 실제 xlsx일 수 있음)
            with open(path, "rb") as fh:
                head = fh.read(8)
            is_xlsx = head.startswith(b"PK\x03\x04")
            try:
                if is_xlsx:
                    from collect_common import extract_records_from_xlsx
                    recs = extract_records_from_xlsx(path)
                    excel_flag = False  # xlsx는 openpyxl이 datetime 객체로 반환
                else:
                    recs = extract_records_from_xls(path, excel_serial_date=True)
                    excel_flag = True
            except Exception as e:
                print(f"  [{i}/{len(targets)}] id={p['id']} 파싱실패: {e}")
                n_err += 1
                continue
            dept = p.get("dept") or extract_dept_from_title(p.get("title",""), DISTRICT)
            kept = 0
            for rec in recs:
                out = record_to_csv(rec, district=DISTRICT, dept=dept,
                                    source_id=f"gangnam_{p['id']}",
                                    datetime_is_excel=excel_flag)
                if out:
                    w.writerow(out)
                    kept += 1
            n_records += kept
            n_ok += 1
            if i % 50 == 0 or i == len(targets):
                print(f"  [{i}/{len(targets)}] id={p['id']} +{kept}행 누계={n_records}")
    print(f"[{DISTRICT}] ✅ XLS ok={n_ok} err={n_err} records={n_records} → {RAW_OUT}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["list","fetch","parse","all"], default="all")
    ap.add_argument("--since", default=SINCE.strftime("%Y-%m-%d"))
    ap.add_argument("--max-pages", type=int, default=300)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    since_dt = datetime.strptime(args.since, "%Y-%m-%d")
    session = requests.Session()
    if args.stage in ("list","all"):
        stage_list(session, since_dt, args.max_pages)
    if args.stage in ("fetch","all"):
        stage_fetch(session)
    if args.stage in ("parse","all"):
        stage_parse(args.limit)


if __name__ == "__main__":
    main()
