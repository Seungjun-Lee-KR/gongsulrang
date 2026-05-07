"""
9단계(강동구): 업무추진비 게시판 크롤 → 게시글 메타 + PDF UUID 수집

- 리스트: https://www.gangdong.go.kr/web/newportal/bbs/b_054?cp={N}&pageSize=30
- 상세:   https://www.gangdong.go.kr/web/newportal/bbs/b_054/{id}
- 기간:   작성일 2023-09-01 이후 (서울시본청 2023-10~2026-03과 정렬, 한 달 버퍼)
- 출력:   output/gangdong_posts.json  (list of {id, dept, title, date, pdf_uuid, pdf_name, pdf_size})
- 캐시:   output/.gangdong_list_cache.json (재시작 안전)
"""

import os as _os
from pathlib import Path as _Path
_os.chdir(_Path(__file__).resolve().parent.parent)
import argparse
import json
import os
import re
import sys
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

LIST_URL = "https://www.gangdong.go.kr/web/newportal/bbs/b_054"
DETAIL_URL = "https://www.gangdong.go.kr/web/newportal/bbs/b_054/{id}"
OUT = "data/output/gangdong_posts.json"
CACHE = "data/output/.gangdong_list_cache.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (gongsulrang-collector; edu-research)",
           "Accept-Language": "ko,en;q=0.8"}
RATE_LIST = 1.2
RATE_DETAIL = 1.0
PAGE_SIZE = 30
SINCE = datetime(2023, 9, 1)

PDF_RE = re.compile(
    r'/web/newportal/file/download/uu/([a-f0-9]{32})"[^>]*>\s*([^<]+?\.pdf)\s*\(([^)]+)\)',
    re.IGNORECASE,
)


def load_cache() -> dict:
    if os.path.exists(CACHE):
        return json.load(open(CACHE, encoding="utf-8"))
    return {"listed_pages": [], "detail_done": {}}


def save_cache(c: dict):
    json.dump(c, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)


def fetch_list_page(page: int) -> list[dict]:
    r = requests.get(LIST_URL, params={"cp": page, "pageSize": PAGE_SIZE},
                     headers=HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    rows = []
    for tr in soup.select("table tbody tr"):
        tds = tr.find_all("td")
        if len(tds) < 4:
            continue
        a = tr.find("a", href=True)
        if not a:
            continue
        href = a["href"]
        m = re.search(r"/b_054/(\d+)", href)
        if not m:
            continue
        post_id = m.group(1)
        title = a.get_text(" ", strip=True)
        dept = tds[2].get_text(strip=True) if len(tds) > 2 else ""
        date_str = tds[3].get_text(strip=True) if len(tds) > 3 else ""
        rows.append({"id": post_id, "title": title, "dept": dept, "date": date_str})
    return rows


def fetch_pdf_info(post_id: str) -> dict:
    r = requests.get(DETAIL_URL.format(id=post_id), headers=HEADERS, timeout=20)
    r.raise_for_status()
    m = PDF_RE.search(r.text)
    if not m:
        return {"pdf_uuid": "", "pdf_name": "", "pdf_size": ""}
    return {
        "pdf_uuid": m.group(1),
        "pdf_name": m.group(2).strip(),
        "pdf_size": m.group(3).strip(),
    }


def parse_date(s: str) -> datetime | None:
    s = (s or "").strip()
    for fmt in ("%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-pages", type=int, default=500)
    ap.add_argument("--since", default=SINCE.strftime("%Y-%m-%d"))
    args = ap.parse_args()
    since_dt = datetime.strptime(args.since, "%Y-%m-%d")

    cache = load_cache()
    listed_pages = set(cache.get("listed_pages", []))
    detail_done: dict = cache.get("detail_done", {})

    all_posts: dict[str, dict] = {}
    # 기존 캐시된 상세 결과 반영
    for pid, info in detail_done.items():
        all_posts[pid] = info

    print(f"since={args.since} max-pages={args.max_pages} pageSize={PAGE_SIZE}")

    # 1) 리스트 크롤 (역시간순)
    page = 1
    stopped_by_date = False
    while page <= args.max_pages:
        print(f"  list cp={page} …", end=" ", flush=True)
        try:
            rows = fetch_list_page(page)
        except Exception as e:
            print(f"err({e}) — 2s 뒤 재시도")
            time.sleep(2)
            rows = fetch_list_page(page)

        if not rows:
            print("빈 페이지 → 종료")
            break

        in_range, out_of_range = 0, 0
        oldest = None
        for row in rows:
            d = parse_date(row["date"])
            oldest = d if (oldest is None or (d and d < oldest)) else oldest
            if d is None or d >= since_dt:
                in_range += 1
                if row["id"] not in all_posts:
                    all_posts[row["id"]] = row
            else:
                out_of_range += 1

        print(f"rows={len(rows)} in_range={in_range} oldest={oldest.date() if oldest else '?'}")
        listed_pages.add(page)
        cache["listed_pages"] = sorted(listed_pages)
        save_cache(cache)

        # 전체가 범위 밖이면 더 내려갈 필요 없음
        if rows and out_of_range == len(rows):
            stopped_by_date = True
            print(f"  → 전체 행이 {args.since} 이전 — 중단")
            break

        page += 1
        time.sleep(RATE_LIST)

    print(f"\n리스트 완료: {len(all_posts)}건 (상세 fetch 대상)")

    # 2) 각 게시글 상세 → PDF UUID
    todo = [pid for pid in all_posts
            if not all_posts[pid].get("pdf_uuid") and pid not in detail_done]
    print(f"상세 fetch: {len(todo)}건")
    for i, pid in enumerate(todo, 1):
        try:
            info = fetch_pdf_info(pid)
        except Exception as e:
            print(f"  [{i}/{len(todo)}] id={pid} err={e}")
            time.sleep(2)
            try:
                info = fetch_pdf_info(pid)
            except Exception as e2:
                print(f"    재시도 실패 {e2}")
                info = {"pdf_uuid": "", "pdf_name": "", "pdf_size": ""}
        all_posts[pid].update(info)
        detail_done[pid] = all_posts[pid]
        if i % 20 == 0 or i == len(todo):
            print(f"  [{i}/{len(todo)}] id={pid} uuid={info['pdf_uuid'][:8] or '-'}")
            cache["detail_done"] = detail_done
            save_cache(cache)
        time.sleep(RATE_DETAIL)

    cache["detail_done"] = detail_done
    save_cache(cache)

    # 3) 결과 저장
    posts = sorted(all_posts.values(), key=lambda x: x["date"], reverse=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)

    n_pdf = sum(1 for p in posts if p.get("pdf_uuid"))
    print(f"\n✅ {len(posts)}건 저장 (PDF 있음: {n_pdf}) → {OUT}")


if __name__ == "__main__":
    main()
