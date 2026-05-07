"""
구청 업무추진비 수집 공통 유틸 — 헤더 자동 탐지 기반 파서

- PDF / XLS 모두 "헤더 행"을 먼저 찾고 컬럼 인덱스 맵을 만든 뒤 데이터 row 추출
- 구청별로 컬럼 순서/이름/개수가 달라도 동작
- 반환: {user, date, time, place, purpose, count, amount, pay, bimok}
"""

import os as _os
from pathlib import Path as _Path
_os.chdir(_Path(__file__).resolve().parent.parent)
import csv
import os
import re
import time
from datetime import datetime, timedelta

import pdfplumber

FIELDS = [
    "부서_메타", "부서명", "사용일", "사용시간", "사용장소", "식당명",
    "주소", "사용목적", "사용금액", "사용자", "결제방법", "비목", "source_file",
]

# 헤더에서 각 논리 컬럼을 찾는 키워드 (normalize된 텍스트에 substring)
# 주의: 키워드 길이 ↓ 순으로 정렬 권장 — 더 구체적인 키워드가 먼저 매칭되게.
COL_KEYS = [
    ("user",     ["사용자", "집행자"]),
    ("datetime", ["사용일시", "집행일시", "일시"]),
    ("date",     ["사용일자", "집행일자", "집행일", "사용일", "일자"]),
    ("time",     ["사용시간", "시간", "시각"]),
    ("place",    ["사용장소", "가맹점", "사용처", "장소"]),
    ("purpose",  ["집행목적", "사용목적", "목적", "내용"]),
    ("count",    ["대상인원", "참여인원", "인원"]),
    ("amount",   ["사용금액", "집행금액", "집행액", "금액"]),
    ("pay",      ["결제방법", "결제수단", "결제"]),
    ("bimok",    ["비목"]),
    ("seq",      ["연번", "순번", "번호"]),
]


def _norm(s) -> str:
    if s is None:
        return ""
    return re.sub(r"\s+", "", str(s))


def clean_cell(s) -> str:
    if s is None:
        return ""
    s = str(s).replace("\n", " ").replace("\r", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def detect_header_map(row) -> dict | None:
    """row (list of cells) → {logical_key: col_index} or None if not a header."""
    normed = [_norm(c) for c in row]
    mapping: dict[str, int] = {}
    hits = 0
    for key, kws in COL_KEYS:
        for i, cell in enumerate(normed):
            if not cell:
                continue
            for kw in kws:
                if _norm(kw) in cell:
                    if key not in mapping:
                        mapping[key] = i
                        hits += 1
                    break
    # 헤더로 인정할 최소 기준: 3개 이상 + 필수 (user/place/amount or datetime/date)
    if hits < 3:
        return None
    has_anchor = ("amount" in mapping) and ("place" in mapping) \
        and (("user" in mapping) or ("datetime" in mapping) or ("date" in mapping))
    if not has_anchor:
        return None
    return mapping


def _cell(row: list, idx: int | None) -> str:
    if idx is None or idx >= len(row) or idx < 0:
        return ""
    return clean_cell(row[idx])


def row_to_dict(row: list, m: dict) -> dict:
    return {
        "user":     _cell(row, m.get("user")),
        "datetime": _cell(row, m.get("datetime")),
        "date":     _cell(row, m.get("date")),
        "time":     _cell(row, m.get("time")),
        "place":    _cell(row, m.get("place")),
        "purpose":  _cell(row, m.get("purpose")),
        "count":    _cell(row, m.get("count")),
        "amount":   _cell(row, m.get("amount")),
        "pay":      _cell(row, m.get("pay")),
        "bimok":    _cell(row, m.get("bimok")),
        "seq":      _cell(row, m.get("seq")),
    }


def is_data_rowdict(d: dict) -> bool:
    """의미 있는 데이터 행인가 (합계/빈줄 제거)"""
    joined = " ".join(d.values())
    if not joined.strip():
        return False
    if any(s in joined for s in ("합 계", "합계", "소 계", "소계", "계 :")):
        return False
    # 적어도 장소나 금액 중 하나는 있어야
    return bool(d["place"]) or bool(d["amount"])


def parse_amount(s) -> int:
    s = clean_cell(s).replace(",", "").replace("원", "").strip()
    if not s or s in ("-", "합 계", "합계"):
        return 0
    try:
        return int(float(s))
    except ValueError:
        return 0


def parse_date_text(s: str) -> tuple[str, str]:
    s = clean_cell(s)
    if not s:
        return "", ""
    m = re.match(r"(\d{4})[-./년]\s*(\d{1,2})[-./월]\s*(\d{1,2})[일]?\s*(\d{1,2}:\d{2}(?::\d{2})?)?", s)
    if m:
        y, mo, d, t = m.group(1), m.group(2).zfill(2), m.group(3).zfill(2), (m.group(4) or "")
        return f"{y}-{mo}-{d}", t
    return s, ""


def parse_time_text(s: str) -> str:
    s = clean_cell(s).replace(" ", "")
    m = re.match(r"(\d{1,2}):(\d{2})(?::(\d{2}))?", s)
    if m:
        h, mi, se = m.group(1).zfill(2), m.group(2), m.group(3) or ""
        return f"{h}:{mi}" + (f":{se}" if se else "")
    return ""


def excel_serial_to_date(val) -> tuple[str, str]:
    try:
        f = float(val)
    except (TypeError, ValueError):
        return "", ""
    if f < 1 or f > 100000:
        return "", ""
    try:
        base = datetime(1899, 12, 30)
        d = base + timedelta(days=f)
        return d.strftime("%Y-%m-%d"), d.strftime("%H:%M:%S")
    except Exception:
        return "", ""


def resolve_datetime(d: dict, datetime_is_excel: bool = False) -> tuple[str, str]:
    date_str, time_str = "", ""
    if d["datetime"]:
        if datetime_is_excel:
            date_str, time_str = excel_serial_to_date(d["datetime"])
        else:
            date_str, time_str = parse_date_text(d["datetime"])
    if not date_str and d["date"]:
        if datetime_is_excel:
            date_str, t2 = excel_serial_to_date(d["date"])
            if not time_str:
                time_str = t2
        else:
            date_str, t2 = parse_date_text(d["date"])
            if not time_str:
                time_str = t2
    # time 별도 컬럼이 채워져 있으면 우선 (date-only datetime 경우 여기서 보강)
    if d.get("time"):
        t = parse_time_text(d["time"])
        if t:
            time_str = t
    return date_str, time_str


_ADDR_HINT_RE = re.compile(
    r"(?:[가-힣A-Za-z0-9]+(?:로|길))\s*\d"
    r"|[가-힣A-Za-z0-9]{2,6}동(?:\s*\d|\s|$|[,)])"
    r"|[가-힣]{2,}구\s"
    r"|서울(?:특별시|시)?\s"
)
_CORP_INNER_RE = re.compile(r"^\s*[주유합재학]\s*$")
_PAREN_RE = re.compile(r"\(\s*([^()]+?)\s*\)")
_NOISE_RESIDUE_RE = re.compile(r"^(?:지하)?[B\d]+\s*(?:층|F|호)?\s*[,\-]?\s*$")
_FLOOR_ONLY_RE = re.compile(r"^\s*(?:지하\s*)?\d+\s*[호층]\s*$")


def parse_place_with_addr(raw: str) -> tuple[str, str]:
    """raw place 컬럼에서 식당명과 주소를 분리.
    '식당명(주소)' / '(주소)식당명' / '주소, 식당명' 등 형태 처리.
    `(주)` 같은 회사명 prefix는 보존.
    식당명이 '1층' 같은 노이즈만 남고 주소가 추출된 경우 식당명을 비워 호출측에서 드롭하게 함."""
    if not raw:
        return "", ""
    s = re.sub(r"\s+", " ", str(raw).replace("\n", " ").replace("\r", " ")).strip()
    if not s:
        return "", ""
    addresses: list[str] = []
    kept: list[str] = []
    while True:
        m = _PAREN_RE.search(s)
        if not m:
            break
        inner = m.group(1).strip()
        if _CORP_INNER_RE.match(inner):
            ph = f"\x00K{len(kept)}\x00"
            kept.append(inner)
            s = s[:m.start()] + ph + s[m.end():]
        elif _ADDR_HINT_RE.search(inner) or _FLOOR_ONLY_RE.match(inner):
            addresses.append(inner)
            s = s[:m.start()] + " " + s[m.end():]
        else:
            ph = f"\x00K{len(kept)}\x00"
            kept.append(inner)
            s = s[:m.start()] + ph + s[m.end():]
        s = re.sub(r"\s+", " ", s).strip()
    naked = re.sub(r"\x00K\d+\x00", "", s).strip(" ,.·-_'\"`~")
    if kept and len(kept) == 1 and _NOISE_RESIDUE_RE.match(naked):
        s = kept[0]
    else:
        for i, inner in enumerate(kept):
            s = s.replace(f"\x00K{i}\x00", f"({inner})")
    if "," in s and _ADDR_HINT_RE.search(s):
        parts = [p.strip() for p in s.split(",")]
        if parts and parts[-1] and not _ADDR_HINT_RE.search(parts[-1]) and 2 <= len(parts[-1]) <= 25:
            addresses.insert(0, ", ".join(parts[:-1]))
            s = parts[-1]
    s = re.sub(r"\s+", " ", s).strip(" ,.·-_'\"`~")
    if s and _ADDR_HINT_RE.search(s):
        residue = re.sub(_ADDR_HINT_RE, "", s)
        residue = re.sub(r"[가-힣A-Za-z0-9]{2,6}동", "", residue)
        residue = re.sub(r"\d+(?:-\d+)?\s*[호층]?", "", residue)
        residue = re.sub(r"[\s,.\-()0-9]+", "", residue).strip()
        if len(residue) < 2:
            addresses.insert(0, s)
            s = ""
    # 주소가 추출됐는데 남은 식당명이 '1층' 같은 노이즈뿐이면 식당명 드롭
    if addresses and s and _NOISE_RESIDUE_RE.match(s):
        s = ""
    addr = max(addresses, key=len) if addresses else ""
    return s, addr


def strip_place(raw: str) -> str:
    s = clean_cell(raw)
    if not s:
        return ""
    # "버니코(Bunnyc" → "버니코"
    s = re.sub(r"\([A-Za-z][^)]*$", "", s).strip()
    # "지에스 더 프레시(" → "지에스 더 프레시"
    s = re.sub(r"\($", "", s).strip()
    if s.count("(") > s.count(")"):
        s += ")" * (s.count("(") - s.count(")"))
    return s.rstrip(",").strip()


def merge_wrapped_rows(rows: list[list], m: dict) -> list[list]:
    """
    헤더 map 기준으로 '새로운 레코드 시작' 판단:
      - seq 컬럼이 있으면 seq가 숫자인 행 = 새 레코드
      - seq 없으면 user 또는 date 컬럼이 채워진 행 = 새 레코드
    그 외는 이전 행에 이어붙임.
    """
    out: list[list] = []
    anchors = [k for k in ("seq", "user", "datetime", "date") if k in m]
    def is_new_record(row):
        if "seq" in m:
            v = _cell(row, m["seq"])
            if re.match(r"^\d+\.?\d*$", v):
                return True
            if v:
                return False
        # seq 없거나 비어있으면: user/datetime/date 중 하나라도 비어있지 않으면 새 레코드
        for k in ("user", "datetime", "date"):
            if k in m and _cell(row, m[k]):
                return True
        return False

    for r in rows:
        if is_new_record(r):
            out.append([clean_cell(c) for c in r])
        else:
            if not out:
                continue
            for i, c in enumerate(r):
                if i >= len(out[-1]):
                    continue
                add = clean_cell(c)
                if not add:
                    continue
                sep = " " if out[-1][i] else ""
                out[-1][i] = (out[-1][i] + sep + add).strip()
    return out


def refine_header_with_data(m: dict, data_rows: list) -> dict:
    """첫 몇 개 데이터 row로 time/date 컬럼 위치 보강.
    예: 헤더가 '일시'로 병합돼 date만 잡혔는데 실제로는 date+time 분리된 경우."""
    if not data_rows:
        return m
    # time 컬럼 미지정 + date 또는 datetime 매핑 된 경우: 다음 셀이 시간형식이면 추가
    anchor = m.get("datetime", m.get("date"))
    if "time" not in m and anchor is not None:
        next_idx = anchor + 1
        hits = 0
        checked = 0
        for r in data_rows[:8]:
            if next_idx < len(r):
                v = clean_cell(r[next_idx])
                if v:
                    checked += 1
                    if re.match(r"^\d{1,2}:\d{2}", v):
                        hits += 1
        # next_idx가 다른 키에 이미 할당돼있으면 덮어쓰지 말 것
        already_taken = any(v == next_idx for k, v in m.items() if k != "time")
        if hits >= 2 and checked > 0 and hits / checked >= 0.5 and not already_taken:
            m["time"] = next_idx
    return m


def extract_records_from_pdf(pdf_path: str) -> list[dict]:
    collected: list[dict] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables() or []:
                header_idx = None
                header_map = None
                for i, r in enumerate(table[:5]):
                    hm = detect_header_map(r)
                    if hm:
                        header_idx = i
                        header_map = hm
                        break
                if not header_map:
                    continue
                data = table[header_idx + 1:]
                header_map = refine_header_with_data(header_map, data)
                data = merge_wrapped_rows(data, header_map)
                for row in data:
                    d = row_to_dict(row, header_map)
                    if is_data_rowdict(d):
                        collected.append(d)
    return collected


def extract_records_from_xls(xls_path: str, *, excel_serial_date: bool = True) -> list[dict]:
    import xlrd
    wb = xlrd.open_workbook(xls_path)
    collected: list[dict] = []
    for sh in wb.sheets():
        header_map = None
        header_row = -1
        for r in range(min(sh.nrows, 20)):
            row = [sh.cell_value(r, c) for c in range(sh.ncols)]
            hm = detect_header_map(row)
            if hm:
                header_map = hm
                header_row = r
                break
        if not header_map:
            continue
        data_rows = [[sh.cell_value(r, c) for c in range(sh.ncols)]
                     for r in range(header_row + 1, sh.nrows)]
        header_map = refine_header_with_data(header_map, data_rows)
        for row in data_rows:
            d = row_to_dict(row, header_map)
            if is_data_rowdict(d):
                collected.append(d)
    return collected


def extract_records_from_xlsx(xlsx_path: str) -> list[dict]:
    import openpyxl
    # file-like로 열어 확장자(.xls 등) 기반 거부를 우회
    fh = open(xlsx_path, "rb")
    wb = openpyxl.load_workbook(fh, data_only=True, read_only=True)
    collected: list[dict] = []
    for sh in wb.worksheets:
        all_rows = [list(r) for r in sh.iter_rows(values_only=True)]
        header_map = None
        header_row = -1
        for r_idx, row in enumerate(all_rows[:20]):
            hm = detect_header_map(row)
            if hm:
                header_map = hm
                header_row = r_idx
                break
        if not header_map:
            continue
        data_rows = all_rows[header_row + 1:]
        header_map = refine_header_with_data(header_map, data_rows)
        for row in data_rows:
            d = row_to_dict(row, header_map)
            if is_data_rowdict(d):
                collected.append(d)
    return collected


def record_to_csv(rec: dict, *, district: str, dept: str, source_id: str,
                  datetime_is_excel: bool = False, address: str = "") -> dict | None:
    place = strip_place(rec["place"])
    if not place:
        return None
    date, t = resolve_datetime(rec, datetime_is_excel)
    amt = parse_amount(rec["amount"])
    dept_full = f"{district} {dept}".strip()
    return {
        "부서_메타": dept_full,
        "부서명": dept_full,
        "사용일": date,
        "사용시간": t,
        "사용장소": rec["place"],
        "식당명": place,
        "주소": address,
        "사용목적": rec["purpose"],
        "사용금액": amt,
        "사용자": rec["user"],
        "결제방법": rec["pay"],
        "비목": rec["bimok"],
        "source_file": source_id,
    }


class RateLimiter:
    def __init__(self, interval_sec: float):
        self.interval = interval_sec
        self.last = 0.0

    def wait(self):
        dt = time.time() - self.last
        if dt < self.interval:
            time.sleep(self.interval - dt)
        self.last = time.time()


def load_json(path: str, default=None):
    import json
    if os.path.exists(path):
        try:
            return json.load(open(path, encoding="utf-8"))
        except Exception:
            return default
    return default


def save_json(path: str, obj):
    import json
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(obj, open(path, "w", encoding="utf-8"), ensure_ascii=False)


def extract_dept_from_title(title: str, district: str = "") -> str:
    t = clean_cell(title)
    if not t:
        return ""
    # "2026년 3월 보건위생과 업무추진비 ..." / "2026. 3월 맑은환경과 업무추진비 ..."
    m = re.search(r"(?:\d{4}[년.]\s*\d{1,2}[월.]\s*)?(.+?)\s*(?:기관운영|시책추진|시책|부서운영|업무추진비)", t)
    if m:
        dept = m.group(1).strip()
        dept = re.sub(r"^\d+년.*?월\s*", "", dept).strip()
        dept = re.sub(r"^\d+\.\s*\d+월\s*", "", dept).strip()
        dept = re.sub(r"[(,\s]+$", "", dept).strip()
        return dept
    return ""
