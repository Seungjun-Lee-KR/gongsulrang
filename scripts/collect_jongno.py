"""
종로구 업무추진비 공개 수집 (list + fetch + parse)

- 리스트: https://www.jongno.go.kr/portal/bbs/selectBoardList.do?bbsId=BBSMSTR_000000001167&menuId=110210&menuNo=110210&pageIndex={N}
  - 각 게시글이 <ul class="respon-td">로 렌더링, 첨부파일 링크가 리스트에 바로 노출됨
- 첨부: /cmm/fms/FileDown.do?atchFileId=FILE_X&fileSn=1 (PDF)

- 출력:
  - output/jongno_posts.json
  - output/jongno_pdfs/{nttId}.pdf
  - output/jongno_expense_raw.csv
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
POSTS = f"{OUT_DIR}/jongno_posts.json"
PDF_DIR = f"{OUT_DIR}/jongno_pdfs"
RAW_OUT = f"{OUT_DIR}/jongno_expense_raw.csv"

BASE = "https://www.jongno.go.kr"
LIST_URL = f"{BASE}/portal/bbs/selectBoardList.do"
DOWNLOAD_URL = f"{BASE}/cmm/fms/FileDown.do"
LIST_PARAMS = {"bbsId": "BBSMSTR_000000001167", "menuId": "110210", "menuNo": "110210"}
HEADERS = {"User-Agent": "Mozilla/5.0 (gongsulrang-collector; edu-research)",
           "Accept-Language": "ko,en;q=0.8"}
SINCE = datetime(2023, 9, 1)
RATE_LIST = 1.0
RATE_DOWNLOAD = 0.5
DISTRICT = "종로구"

_DATE_RE = re.compile(r"(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일")


def parse_list_row(ul) -> dict | None:
    """
    <ul class="respon-td"> 안에서 필드 뽑기.
    순서: 번호, 년도, 해당월, 작성부서, 구분, 담당자, 파일(atchFileId), 작성일
    """
    ems = ul.find_all("em")
    if len(ems) < 7:
        return None

    def text_of(em):
        return em.get_text(" ", strip=True)

    number = text_of(ems[0])
    year = text_of(ems[1])
    month = text_of(ems[2])
    dept = text_of(ems[3])
    kind = text_of(ems[4])  # 기관운영/시책추진
    _staff = text_of(ems[5])

    # 파일 em 안의 a href
    file_em = ems[6]
    a = file_em.find("a", href=re.compile(r"atchFileId="))
    atch_id = ""
    file_sn = "1"
    if a:
        m = re.search(r"atchFileId=([A-Z0-9_]+)", a["href"])
        if m:
            atch_id = m.group(1)
        m2 = re.search(r"fileSn=(\d+)", a["href"])
        if m2:
            file_sn = m2.group(1)

    # 작성일
    created = text_of(ems[7]) if len(ems) > 7 else ""
    date_str = ""
    m = _DATE_RE.search(created)
    if m:
        date_str = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"

    # nttId = viewMove('xxx')에서 뽑되 없으면 번호 사용
    ntt_id = ""
    for link in ul.find_all("a", href=re.compile(r"viewMove")):
        mx = re.search(r"viewMove\('(\d+)'\)", link["href"])
        if mx:
            ntt_id = mx.group(1)
            break
    if not ntt_id:
        ntt_id = number

    title = f"{year}년 {month}월 {dept} {kind}"
    return {
        "id": ntt_id,
        "title": title,
        "dept": dept,
        "date": date_str,
        "atch_file_id": atch_id,
        "file_sn": file_sn,
        "kind": kind,
    }


def fetch_list_page(session: requests.Session, page: int) -> list[dict]:
    params = dict(LIST_PARAMS, pageIndex=str(page))
    r = session.get(LIST_URL, params=params, headers=HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    rows = []
    for ul in soup.select("ul.respon-td"):
        row = parse_list_row(ul)
        if row and row["id"]:
            rows.append(row)
    return rows


def parse_date(s: str) -> datetime | None:
    s = (s or "").strip()
    for fmt in ("%Y-%m-%d",):
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

    posts = sorted(all_posts.values(), key=lambda x: x.get("date", ""), reverse=True)
    save_json(POSTS, posts)
    n = sum(1 for p in posts if p.get("atch_file_id"))
    print(f"[{DISTRICT}] ✅ posts={len(posts)} (pdf 있음: {n}) → {POSTS}")


def stage_fetch(session: requests.Session):
    os.makedirs(PDF_DIR, exist_ok=True)
    posts = load_json(POSTS, []) or []
    todo = [p for p in posts if p.get("atch_file_id")]
    print(f"[{DISTRICT}] PDF 다운로드: {len(todo)}건")
    rate = RateLimiter(RATE_DOWNLOAD)
    n_ok = n_skip = n_err = 0
    for i, p in enumerate(todo, 1):
        path = os.path.join(PDF_DIR, f"{p['id']}.pdf")
        if os.path.exists(path) and os.path.getsize(path) > 1000:
            n_skip += 1
            continue
        try:
            params = {"atchFileId": p["atch_file_id"], "fileSn": p.get("file_sn", "1")}
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
    targets = [p for p in posts if p.get("atch_file_id")]
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
                                    source_id=f"jongno_{p['id']}")
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
