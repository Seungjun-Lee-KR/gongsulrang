"""
11단계(강동구): PDF 표 → raw CSV (서울시본청 스키마 호환)

- 입력: output/gangdong_pdfs/{uuid}.pdf + output/gangdong_posts.json
- 출력: output/gangdong_expense_raw.csv
- 컬럼: 부서_메타, 부서명, 사용일, 사용시간, 사용장소, 식당명, 주소,
        사용목적, 사용금액, 사용자, 결제방법, 비목, source_file

PDF 표 컬럼: [연번, 사용자, 사용일시, 장소, 집행목적, 인원, 집행액, 결제방법, 비목]
"""

import os as _os
from pathlib import Path as _Path
_os.chdir(_Path(__file__).resolve().parent.parent)
import argparse
import csv
import json
import os
import re
import sys

import pdfplumber

POSTS = "data/output/gangdong_posts.json"
PDF_DIR = "data/output/gangdong_pdfs"
OUT = "data/output/gangdong_expense_raw.csv"

FIELDS = [
    "부서_메타", "부서명", "사용일", "사용시간", "사용장소", "식당명",
    "주소", "사용목적", "사용금액", "사용자", "결제방법", "비목", "source_file",
]

HEADER_TOKENS = ("연번", "사용자", "사용일시", "장소", "집행", "인원", "결제", "비목")


def clean_cell(s: str | None) -> str:
    if not s:
        return ""
    s = s.replace("\n", " ").replace("\r", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def is_header(row: list[str | None]) -> bool:
    joined = " ".join((c or "") for c in row)
    return sum(1 for t in HEADER_TOKENS if t in joined) >= 3


def parse_amount(s: str) -> int:
    if not s:
        return 0
    s = clean_cell(s).replace(",", "").replace("원", "").strip()
    if not s or s in ("-", "합 계", "합계"):
        return 0
    try:
        return int(float(s))
    except ValueError:
        return 0


def parse_datetime(s: str) -> tuple[str, str]:
    s = clean_cell(s)
    if not s:
        return "", ""
    # "2026-03-03 12:10:00" 또는 "2026.03.03 12:10" 등
    m = re.match(r"(\d{4})[-.](\d{1,2})[-.](\d{1,2})\s*(\d{1,2}:\d{2}(?::\d{2})?)?", s)
    if m:
        y, mo, d, t = m.group(1), m.group(2).zfill(2), m.group(3).zfill(2), (m.group(4) or "")
        return f"{y}-{mo}-{d}", t
    return s, ""


def strip_place(raw: str) -> str:
    s = clean_cell(raw)
    if not s:
        return ""
    # 장소명 끝의 "(영문)" 잔해 제거 — "버니코(Bunnyc" → "버니코"
    s = re.sub(r"\([A-Za-z][^)]*$", "", s).strip()
    # 끝에 괄호로 시작하다가 본문 내용 없이 잘린 경우 "지에스 더 프레시(" → "지에스 더 프레시"
    s = re.sub(r"\($", "", s).strip()
    # 쉼표/괄호 짝 맞추기
    if s.count("(") > s.count(")"):
        s += ")" * (s.count("(") - s.count(")"))
    return s.rstrip(",").strip()


def merge_wrapped_rows(rows: list[list[str]]) -> list[list[str]]:
    """pdfplumber가 줄바꿈으로 쪼갠 연번 비어있는 continuation 행을 이전 행에 합침"""
    out: list[list[str]] = []
    for r in rows:
        seq = clean_cell(r[0]) if r else ""
        if seq.isdigit() or re.match(r"^\d+$", seq):
            out.append([clean_cell(c) for c in r])
        else:
            if not out:
                continue
            # 이전 행의 각 셀에 이어붙이기
            for i, c in enumerate(r):
                if i >= len(out[-1]):
                    continue
                add = clean_cell(c)
                if not add:
                    continue
                sep = " " if out[-1][i] else ""
                out[-1][i] = (out[-1][i] + sep + add).strip()
    return out


def extract_rows(pdf_path: str) -> list[list[str]]:
    collected: list[list[str]] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables() or []:
                data_rows = [row for row in table if not is_header(row)]
                # 합계 행 제거 (사용일시 비어있고 집행액 라벨이 "합 계" 등)
                data_rows = [row for row in data_rows
                             if any(clean_cell(c) for c in row[:3])]
                collected.extend(merge_wrapped_rows(data_rows))
    return collected


def row_to_record(row: list[str], post: dict) -> dict | None:
    # [연번, 사용자, 사용일시, 장소, 집행목적, 인원, 집행액, 결제방법, 비목]
    if len(row) < 9:
        row = row + [""] * (9 - len(row))
    seq, user, dt, place, purpose, _num, amount, pay, bimok = row[:9]
    place_clean = strip_place(place)
    if not place_clean:
        return None
    date, time_part = parse_datetime(dt)
    amt = parse_amount(amount)
    dept = post.get("dept") or ""
    dept_full = f"강동구 {dept}".strip()
    return {
        "부서_메타": dept_full,
        "부서명": dept_full,
        "사용일": date,
        "사용시간": time_part,
        "사용장소": clean_cell(place),
        "식당명": place_clean,
        "주소": "",
        "사용목적": clean_cell(purpose),
        "사용금액": amt,
        "사용자": clean_cell(user),
        "결제방법": clean_cell(pay),
        "비목": clean_cell(bimok),
        "source_file": f"gangdong_{post.get('id','')}",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="테스트용: 처음 N개 PDF만")
    args = ap.parse_args()

    posts = json.load(open(POSTS, encoding="utf-8"))
    by_uuid = {p["pdf_uuid"]: p for p in posts if p.get("pdf_uuid")}
    targets = list(by_uuid.items())
    if args.limit > 0:
        targets = targets[:args.limit]
    print(f"대상 PDF: {len(targets)}건")

    n_pdf_ok = n_pdf_err = n_records = 0
    with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for i, (uuid, post) in enumerate(targets, 1):
            path = os.path.join(PDF_DIR, f"{uuid}.pdf")
            if not os.path.exists(path):
                n_pdf_err += 1
                continue
            try:
                rows = extract_rows(path)
            except Exception as e:
                print(f"  [{i}/{len(targets)}] id={post['id']} 파싱 실패: {e}")
                n_pdf_err += 1
                continue
            kept = 0
            for row in rows:
                rec = row_to_record(row, post)
                if rec:
                    w.writerow(rec)
                    kept += 1
            n_records += kept
            n_pdf_ok += 1
            if i % 25 == 0 or i == len(targets):
                print(f"  [{i}/{len(targets)}] id={post['id']} +{kept}행 누계 records={n_records}")

    print(f"\n✅ PDFs ok={n_pdf_ok} err={n_pdf_err} → records={n_records} → {OUT}")


if __name__ == "__main__":
    main()
