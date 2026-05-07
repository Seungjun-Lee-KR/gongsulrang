"""
서울 25 자치구 업무추진비 페이지 프로빙

- 각 URL GET → 상태, title, 목록 구조, 페이징 파라미터, 키워드 매칭
- 첫 게시글 상세로 1회 더 진입 → 첨부 확장자 샘플링
- 결과: output/districts_probe.csv / .json
"""

import os as _os
from pathlib import Path as _Path
_os.chdir(_Path(__file__).resolve().parent.parent)
import csv
import json
import re
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (gongsulrang-probe; edu-research)",
    "Accept-Language": "ko,en;q=0.8",
}
RATE = 1.2
OUT_JSON = "data/output/districts_probe.json"
OUT_CSV = "data/output/districts_probe.csv"

DISTRICTS = [
    {"org": "강남구", "url": "https://www.gangnam.go.kr/board/B_000054/list.do"},
    {"org": "강동구", "url": "https://www.gangdong.go.kr/web/newportal/contents/gg_expense_01.do"},
    {"org": "송파구", "url": "https://www.songpa.go.kr/www/selectBbsNttList.do?bbsNo=215"},
    {"org": "서초구", "url": "https://www.seocho.go.kr/site/seocho/expenditureList.do"},
    {"org": "광진구", "url": "https://www.gwangjin.go.kr/portal/bbs/B0000135/list.do"},
    {"org": "강서구", "url": "https://www.gangseo.seoul.kr/portal/bbs/B0000268/list.do"},
    {"org": "양천구", "url": "https://www.yangcheon.go.kr/site/yangcheon/expenditureList.do"},
    {"org": "구로구", "url": "https://www.guro.go.kr/www/selectBbsNttList.do?bbsNo=307"},
    {"org": "금천구", "url": "https://www.geumcheon.go.kr/portal/selectBbsNttList.do?bbsNo=86"},
    {"org": "영등포구", "url": "https://www.ydp.go.kr/www/selectBbsNttList.do?bbsNo=222"},
    {"org": "은평구", "url": "https://www.ep.go.kr/CmsWeb/viewPage.req?idx=PG0000003845"},
    {"org": "서대문구", "url": "https://www.sdm.go.kr/board/list.do?bbsId=BBSMSTR_000000000285"},
    {"org": "마포구", "url": "https://www.mapo.go.kr/site/main/board/expense"},
    {"org": "종로구", "url": "https://www.jongno.go.kr/portal/bbs/B0000206/list.do"},
    {"org": "중구", "url": "https://www.junggu.seoul.kr/content.do?cmsid=14892"},
    {"org": "용산구", "url": "https://www.yongsan.go.kr/portal/bbs/B0000203/list.do"},
    {"org": "성동구", "url": "https://www.sd.go.kr/main/bbs/B0000123/list.do"},
    {"org": "성북구", "url": "https://www.sb.go.kr/portal/bbs/B0000163/list.do"},
    {"org": "동대문구", "url": "https://www.ddm.go.kr/portal/bbs/B0000137/list.do"},
    {"org": "중랑구", "url": "https://www.jungnang.go.kr/portal/bbs/B0000130/list.do"},
    {"org": "노원구", "url": "https://www.nowon.kr/www/selectBbsNttList.do?bbsNo=246"},
    {"org": "도봉구", "url": "https://www.dobong.go.kr/site/main/board/expense"},
    {"org": "강북구", "url": "https://www.gangbuk.go.kr/portal/bbs/B0000182/list.do"},
    {"org": "관악구", "url": "https://www.gwanak.go.kr/site/gwanak/estimate/estimateList.do"},
    {"org": "동작구", "url": "https://www.dongjak.go.kr/portal/bbs/B0000132/list.do"},
]

PAGING_KEYS = [
    "pageIndex", "currentPageNo", "pageNo", "cpage", "pageNum",
    "nowPage", "pg", "pageUnit",
]

FILE_EXTS = (".xlsx", ".xls", ".xlsm", ".hwp", ".hwpx", ".pdf", ".csv")

EXPENSE_KEYWORDS = ["업무추진비", "추진비", "카드사용내역"]


def detect_pagination(html: str):
    hits = {}
    for key in PAGING_KEYS:
        cnt = html.count(f"{key}=")
        if cnt:
            hits[key] = cnt
    # AJAX 힌트
    ajax = any(kw in html for kw in ("ajax(", "XMLHttpRequest", "axios", "fetch("))
    return hits, ajax


def expense_keyword_hit(soup):
    text = soup.get_text(" ", strip=True)[:30000]
    return [kw for kw in EXPENSE_KEYWORDS if kw in text]


def pick_first_detail(soup, base_url):
    # table 기반
    for a in soup.select("table tbody tr a, table tr a"):
        href = a.get("href") or ""
        if not href or href == "#" or href.startswith("javascript:"):
            continue
        return urljoin(base_url, href), (a.get_text(strip=True) or "")[:80]
    # ul/ol 리스트 기반
    for a in soup.select("ul li a, ol li a"):
        href = a.get("href") or ""
        if not href or href == "#" or href.startswith("javascript:"):
            continue
        text = (a.get_text(strip=True) or "")
        if len(text) < 6:  # navigation link 배제
            continue
        return urljoin(base_url, href), text[:80]
    return None, None


def find_attachments(soup):
    exts = set()
    for a in soup.find_all("a"):
        href = (a.get("href") or "").lower()
        text = (a.get_text() or "").lower()
        for ext in FILE_EXTS:
            if ext in href or ext in text:
                exts.add(ext.lstrip("."))
    js_markers = []
    html_low = str(soup).lower()
    for m in ("filedownload(", "cfile_download", "download.do", "egov_filedownload", "atchfileid"):
        if m in html_low:
            js_markers.append(m)
    return sorted(exts), js_markers


def probe(d):
    row = {"org": d["org"], "url": d["url"]}
    try:
        r = requests.get(d["url"], headers=HEADERS, timeout=20, allow_redirects=True)
        row["status"] = r.status_code
        row["final_url"] = r.url
        row["content_length"] = len(r.text)
        if r.status_code != 200:
            return row

        soup = BeautifulSoup(r.text, "html.parser")
        title_tag = soup.find("title")
        row["title"] = title_tag.get_text(strip=True) if title_tag else None
        row["expense_keywords"] = expense_keyword_hit(soup)
        row["table_rows"] = len(soup.select("table tbody tr"))
        row["li_anchors"] = len(soup.select("ul li a, ol li a"))
        paging, ajax = detect_pagination(r.text)
        row["paging_params"] = paging
        row["ajax_hint"] = ajax

        detail_url, detail_text = pick_first_detail(soup, r.url)
        row["first_detail_url"] = detail_url
        row["first_detail_text"] = detail_text

        if detail_url:
            time.sleep(RATE)
            try:
                dr = requests.get(detail_url, headers=HEADERS, timeout=20, allow_redirects=True)
                row["detail_status"] = dr.status_code
                if dr.status_code == 200:
                    dsoup = BeautifulSoup(dr.text, "html.parser")
                    exts, js_markers = find_attachments(dsoup)
                    row["attachment_exts"] = exts
                    row["js_download_markers"] = js_markers
            except Exception as e:
                row["detail_error"] = f"{type(e).__name__}: {e}"
    except Exception as e:
        row["error"] = f"{type(e).__name__}: {e}"
    return row


def main():
    rows = []
    for i, d in enumerate(DISTRICTS, 1):
        print(f"[{i:2d}/25] {d['org']} …")
        rows.append(probe(d))
        time.sleep(RATE)

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

    fields = [
        "org", "url", "status", "final_url", "title", "expense_keywords",
        "table_rows", "li_anchors", "paging_params", "ajax_hint",
        "first_detail_url", "first_detail_text", "detail_status",
        "attachment_exts", "js_download_markers", "detail_error", "error",
    ]
    with open(OUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(fields)
        for r in rows:
            w.writerow([
                r.get(k) if not isinstance(r.get(k), (list, dict)) else json.dumps(r.get(k), ensure_ascii=False)
                for k in fields
            ])

    # 요약 출력
    print("\n=== 분류 요약 ===")
    for r in rows:
        tag = []
        if r.get("status") != 200:
            tag.append(f"HTTP {r.get('status')}")
        if not r.get("expense_keywords"):
            tag.append("키워드 없음")
        exts = r.get("attachment_exts") or []
        if exts:
            tag.append("+".join(exts))
        else:
            tag.append("첨부없음/JS")
        print(f"  {r['org']:5s} : {', '.join(tag)}")

    print(f"\n✅ {OUT_CSV}")


if __name__ == "__main__":
    main()
