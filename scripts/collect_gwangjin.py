"""
광진구 업무추진비 공개 수집 (list + fetch + parse)

- 리스트: https://www.gwangjin.go.kr/portal/bbs/B0000027/list.do?menuNo=201646&pageUnit=30&pageIndex={N}
  - <li> 단위 렌더링. 각 li 안에 num/tit/dept/date + fileDown.do?atchFileId=...&fileSn=... 링크 포함
- 파일:   /portal/cmmn/file/fileDown.do?menuNo=201646&atchFileId=<hex64>&fileSn=1
  - 대부분 XLSX, 일부 PDF — 매직바이트로 판별

- 출력:
  - output/gwangjin_posts.json
  - output/gwangjin_pdfs/{nttId}.{pdf|xlsx|xls}
  - output/gwangjin_expense_raw.csv
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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collect_common import (
    FIELDS, RateLimiter, extract_records_from_pdf, extract_records_from_xlsx,
    record_to_csv, load_json, save_json, extract_dept_from_title,
)

OUT_DIR = "data/output"
POSTS = f"{OUT_DIR}/gwangjin_posts.json"
PDF_DIR = f"{OUT_DIR}/gwangjin_pdfs"
RAW_OUT = f"{OUT_DIR}/gwangjin_expense_raw.csv"

BASE = "https://www.gwangjin.go.kr"
LIST_URL = f"{BASE}/portal/bbs/B0000027/list.do"
DOWNLOAD_URL = f"{BASE}/portal/cmmn/file/fileDown.do"
LIST_PARAMS = {"menuNo": "201646", "pageUnit": "30"}
HEADERS = {"User-Agent": "Mozilla/5.0 (gongsulrang-collector; edu-research)",
           "Accept-Language": "ko,en;q=0.8"}
SINCE = datetime(2023, 9, 1)
RATE_LIST = 1.0
RATE_DOWNLOAD = 0.5
DISTRICT = "광진구"

_LI_RE = re.compile(r"<li>\s*<span class=\"num\">.*?</li>", re.DOTALL)
_NTT_RE = re.compile(r"nttId=(\d+)")
_NUM_RE = re.compile(r"<span class=\"num\">\s*(\d+)")
_TIT_RE = re.compile(r"<span class=\"tit\">([^<]+)</span>")
_DEPT_RE = re.compile(r"<span class=\"dept\">([^<]+)</span>")
_DATE_RE = re.compile(r"<span class=\"date\">\s*(\d{4}-\d{2}-\d{2})")
_FILE_RE = re.compile(r"fileDown\.do\?(?:menuNo=\d+&)?atchFileId=([a-f0-9]+)&(?:amp;)?fileSn=(\d+)")


def parse_list_html(html: str) -> list[dict]:
    rows = []
    for block in _LI_RE.findall(html):
        m_ntt = _NTT_RE.search(block)
        if not m_ntt:
            continue
        ntt_id = m_ntt.group(1)
        m_tit = _TIT_RE.search(block)
        m_dept = _DEPT_RE.search(block)
        m_date = _DATE_RE.search(block)
        title = m_tit.group(1).strip() if m_tit else ""
        dept = m_dept.group(1).strip() if m_dept else extract_dept_from_title(title, DISTRICT)
        date_str = m_date.group(1) if m_date else ""
        # 파일들: (atchFileId, fileSn) unique
        files: list[dict] = []
        seen = set()
        for fm in _FILE_RE.finditer(block):
            key = (fm.group(1), fm.group(2))
            if key in seen:
                continue
            seen.add(key)
            files.append({"atch": fm.group(1), "sn": fm.group(2)})
        rows.append({"id": ntt_id, "title": title, "dept": dept,
                     "date": date_str, "files": files})
    return rows


def fetch_list_page(session: requests.Session, page: int) -> list[dict]:
    params = dict(LIST_PARAMS, pageIndex=str(page))
    r = session.get(LIST_URL, params=params, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return parse_list_html(r.text)


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


def _existing_path(base_id: str, sn: str) -> str | None:
    for ext in ("pdf", "xlsx", "xls"):
        p = os.path.join(PDF_DIR, f"{base_id}_{sn}.{ext}")
        if os.path.exists(p) and os.path.getsize(p) > 1000:
            return p
    return None


def stage_fetch(session: requests.Session):
    os.makedirs(PDF_DIR, exist_ok=True)
    posts = load_json(POSTS, []) or []
    todo = [p for p in posts if p.get("files")]
    total_files = sum(len(p["files"]) for p in todo)
    print(f"[{DISTRICT}] 파일 다운로드: 게시글 {len(todo)}건 / 파일 {total_files}개")
    rate = RateLimiter(RATE_DOWNLOAD)
    n_ok = n_skip = n_err = 0
    for i, p in enumerate(todo, 1):
        for f in p["files"]:
            sn = f["sn"]
            if _existing_path(p["id"], sn):
                n_skip += 1
                continue
            try:
                params = dict(LIST_PARAMS, atchFileId=f["atch"], fileSn=sn)
                r = session.get(DOWNLOAD_URL, params=params, headers=HEADERS, timeout=30)
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
            for f in p["files"]:
                sn = f["sn"]
                path = _existing_path(p["id"], sn)
                if not path:
                    continue
                try:
                    if path.endswith(".pdf"):
                        recs = extract_records_from_pdf(path)
                    elif path.endswith((".xlsx", ".xls")):
                        recs = extract_records_from_xlsx(path)
                    else:
                        continue
                except Exception as e:
                    print(f"  [{i}/{len(targets)}] id={p['id']} sn={sn} 파싱실패: {e}")
                    n_err += 1
                    continue
                for rec in recs:
                    out = record_to_csv(rec, district=DISTRICT, dept=dept,
                                        source_id=f"gwangjin_{p['id']}_{sn}")
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
