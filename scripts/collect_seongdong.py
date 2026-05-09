"""
성동구 업무추진비 공개 수집 (list + fetch + parse)

- 리스트: https://www.sd.go.kr/main/selectBbsNttList.do?bbsNo=172&key=1330&pageUnit=50&pageIndex={N}
  - <table class="p-table simple"> 안의 <tbody> <tr> ... 각 행이 게시글
  - td[0] 번호, td[1] 제목(a href로 nttNo), td[2] <time datetime="YYYY-MM-DD">,
    td[4] 첨부 (단일 PDF: a href="downloadBbsFileStr.do?atchmnflStr=..."
                다중: <span>다중파일</span> → 상세페이지 가서 downloadBbsFile.do?atchmnflNo= 여러개)
- 단일: /main/downloadBbsFileStr.do?atchmnflStr=...
- 다중: /main/downloadBbsFile.do?key=1330&atchmnflNo=...&bbsNo=172&nttNo=...

- 출력:
  - output/seongdong_posts.json
  - output/seongdong_pdfs/{post_id}_{seq}.pdf
  - output/seongdong_expense_raw.csv
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
POSTS = f"{OUT_DIR}/seongdong_posts.json"
PDF_DIR = f"{OUT_DIR}/seongdong_pdfs"
RAW_OUT = f"{OUT_DIR}/seongdong_expense_raw.csv"

BASE = "https://www.sd.go.kr"
LIST_URL = f"{BASE}/main/selectBbsNttList.do"
VIEW_URL = f"{BASE}/main/selectBbsNttView.do"
DOWNLOAD_SINGLE = f"{BASE}/main/downloadBbsFileStr.do"
DOWNLOAD_MULTI = f"{BASE}/main/downloadBbsFile.do"
LIST_PARAMS = {"bbsNo": "172", "key": "1330"}
HEADERS = {"User-Agent": "Mozilla/5.0 (gongsulrang-collector; edu-research)",
           "Accept-Language": "ko,en;q=0.8"}
SINCE = datetime(2023, 9, 1)
RATE_LIST = 1.0
RATE_DOWNLOAD = 0.5
DISTRICT = "성동구"


def parse_list_row(tr) -> dict | None:
    tds = tr.find_all("td", recursive=False)
    if len(tds) < 5:
        return None
    number = tds[0].get_text(" ", strip=True)
    a_title = tds[1].find("a", href=True)
    if not a_title:
        return None
    m = re.search(r"nttNo=(\d+)", a_title["href"])
    if not m:
        return None
    ntt_id = m.group(1)
    title = a_title.get_text(" ", strip=True)

    t = tds[2].find("time")
    date_str = t["datetime"] if (t and t.has_attr("datetime")) else ""

    files: list[dict] = []
    multi = False
    for a in tds[4].find_all("a", href=True):
        href = a["href"]
        if "downloadBbsFileStr.do" in href:
            ms = re.search(r"atchmnflStr=([A-Za-z0-9_]+)", href)
            if ms:
                files.append({"mode": "single", "str": ms.group(1)})
    if not files and "다중파일" in tds[4].get_text(" ", strip=True):
        multi = True

    return {
        "id": ntt_id,
        "number": number,
        "title": title,
        "date": date_str,
        "files": files,  # 단일 케이스만 채움
        "multi": multi,  # True면 stage_fetch에서 상세 진입
    }


def fetch_list_page(session: requests.Session, page: int) -> list[dict]:
    params = dict(LIST_PARAMS, pageUnit="50", pageIndex=str(page))
    r = session.get(LIST_URL, params=params, headers=HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    rows = []
    for tr in soup.select("table.p-table tbody tr"):
        row = parse_list_row(tr)
        if row and row["id"]:
            rows.append(row)
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
    n = sum(1 for p in posts if p.get("files") or p.get("multi"))
    print(f"[{DISTRICT}] ✅ posts={len(posts)} (파일있음: {n}) → {POSTS}")


def fetch_multi_files(session: requests.Session, ntt_id: str) -> list[dict]:
    """다중파일 게시글 상세 페이지에서 downloadBbsFile.do 링크들 추출"""
    params = dict(LIST_PARAMS, nttNo=ntt_id, pageUnit="10", pageIndex="1", nttShowPd="60")
    r = session.get(VIEW_URL, params=params, headers=HEADERS, timeout=20)
    r.raise_for_status()
    files = []
    # downloadBbsFile.do?key=1330&atchmnflNo=313403&bbsNo=172&nttNo=357786
    seen = set()
    for m in re.finditer(r'downloadBbsFile\.do\?([^"\'<> ]+)', r.text):
        qs = m.group(1).replace("&amp;", "&")
        mn = re.search(r"atchmnflNo=(\d+)", qs)
        if not mn:
            continue
        atch_no = mn.group(1)
        if atch_no in seen:
            continue
        seen.add(atch_no)
        files.append({"mode": "multi", "no": atch_no})
    return files


def _guess_ext(content: bytes) -> str | None:
    if content.startswith(b"%PDF"):
        return "pdf"
    if content.startswith(b"PK\x03\x04"):
        return "xlsx"
    if content.startswith(b"\xd0\xcf\x11\xe0"):
        return "xls"
    return None


def stage_fetch(session: requests.Session):
    os.makedirs(PDF_DIR, exist_ok=True)
    posts = load_json(POSTS, []) or []
    rate = RateLimiter(RATE_DOWNLOAD)
    n_posts = n_ok = n_skip = n_err = 0
    targets = [p for p in posts if p.get("files") or p.get("multi")]
    print(f"[{DISTRICT}] 파일 다운로드: 게시글 {len(targets)}건")
    for i, p in enumerate(targets, 1):
        n_posts += 1
        # 다중파일이면 상세 진입해서 파일 목록 채우기 (캐시: p['files']에 저장)
        files = p.get("files") or []
        if p.get("multi") and not files:
            try:
                files = fetch_multi_files(session, p["id"])
                p["files"] = files
                rate.wait()
            except Exception as e:
                print(f"  [{i}/{len(targets)}] id={p['id']} multi-list err={e}")
                n_err += 1
                continue
        for sn, f in enumerate(files, 1):
            ext_default = "pdf"
            path_pdf = os.path.join(PDF_DIR, f"{p['id']}_{sn}.pdf")
            path_xlsx = os.path.join(PDF_DIR, f"{p['id']}_{sn}.xlsx")
            path_xls = os.path.join(PDF_DIR, f"{p['id']}_{sn}.xls")
            if any(os.path.exists(x) and os.path.getsize(x) > 1000 for x in (path_pdf, path_xlsx, path_xls)):
                n_skip += 1
                continue
            try:
                if f["mode"] == "single":
                    r = session.get(DOWNLOAD_SINGLE, params={"atchmnflStr": f["str"]},
                                    headers=HEADERS, timeout=30)
                else:
                    r = session.get(DOWNLOAD_MULTI,
                                    params=dict(LIST_PARAMS, atchmnflNo=f["no"], nttNo=p["id"]),
                                    headers=HEADERS, timeout=30)
                r.raise_for_status()
                ext = _guess_ext(r.content) or ext_default
                out_path = os.path.join(PDF_DIR, f"{p['id']}_{sn}.{ext}")
                with open(out_path, "wb") as fh:
                    fh.write(r.content)
                n_ok += 1
            except Exception as e:
                print(f"  [{i}/{len(targets)}] id={p['id']} sn={sn} err={e}")
                n_err += 1
            rate.wait()
        if i % 50 == 0 or i == len(targets):
            print(f"  [{i}/{len(targets)}] ok+={n_ok} skip={n_skip} err={n_err}")
    # posts 다시 저장 (multi의 files 채워진 상태)
    save_json(POSTS, posts)
    print(f"[{DISTRICT}] ✅ 파일: ok={n_ok} skip={n_skip} err={n_err} → {PDF_DIR}")


def stage_parse(limit: int = 0):
    posts = load_json(POSTS, []) or []
    targets = [p for p in posts if p.get("files") or p.get("multi")]
    if limit > 0:
        targets = targets[:limit]
    print(f"[{DISTRICT}] 파싱 대상: {len(targets)}건")
    n_ok = n_err = n_records = 0
    with open(RAW_OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for i, p in enumerate(targets, 1):
            files = p.get("files") or []
            dept = extract_dept_from_title(p.get("title", ""), DISTRICT)
            kept_post = 0
            for sn, _ in enumerate(files, 1):
                # 확장자 탐색
                for ext in ("pdf", "xlsx", "xls"):
                    path = os.path.join(PDF_DIR, f"{p['id']}_{sn}.{ext}")
                    if os.path.exists(path):
                        break
                else:
                    continue
                if ext != "pdf":
                    # xlsx/xls는 현재 pipeline에서 드묾 — skip 경고만
                    # (성동구는 실제로 거의 PDF만 올라옴)
                    continue
                try:
                    recs = extract_records_from_pdf(path)
                except Exception as e:
                    print(f"  [{i}/{len(targets)}] id={p['id']} sn={sn} 파싱실패: {e}")
                    n_err += 1
                    continue
                for rec in recs:
                    out = record_to_csv(rec, district=DISTRICT, dept=dept,
                                        source_id=f"seongdong_{p['id']}_{sn}")
                    if out:
                        w.writerow(out)
                        kept_post += 1
            n_records += kept_post
            if kept_post > 0:
                n_ok += 1
            if i % 50 == 0 or i == len(targets):
                print(f"  [{i}/{len(targets)}] id={p['id']} 누계={n_records}")
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
