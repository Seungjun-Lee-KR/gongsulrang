"""기존 geumcheon_expense_raw.csv를 재파싱해 식당명/주소 분리만 다시 적용.
재크롤 없이 사용장소 컬럼에서 (주소) 패턴을 분리해 식당명·주소 컬럼을 재기록한다.
"""

import os as _os
from pathlib import Path as _Path
_os.chdir(_Path(__file__).resolve().parent.parent)
import csv
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collect_common import parse_place_with_addr

RAW = "data/output/geumcheon_expense_raw.csv"
BAK = RAW + ".bak"


def main():
    if not os.path.exists(BAK):
        shutil.copy2(RAW, BAK)
        print(f"백업: {BAK}")
    rows_in = 0
    rows_out = 0
    fixed_name = 0
    filled_addr = 0
    dropped = 0
    with open(BAK, encoding="utf-8-sig", newline="") as fin:
        rdr = csv.DictReader(fin)
        fields = rdr.fieldnames
        rows = list(rdr)
    with open(RAW, "w", encoding="utf-8-sig", newline="") as fout:
        w = csv.DictWriter(fout, fieldnames=fields)
        w.writeheader()
        for row in rows:
            rows_in += 1
            place = (row.get("사용장소") or "").strip()
            old_name = (row.get("식당명") or "").strip()
            old_addr = (row.get("주소") or "").strip()
            name, addr = parse_place_with_addr(place)
            if not name:
                dropped += 1
                continue
            if name != old_name:
                fixed_name += 1
            if addr and not old_addr:
                filled_addr += 1
            row["식당명"] = name
            if addr:
                row["주소"] = addr
            w.writerow(row)
            rows_out += 1
    print(f"in={rows_in} out={rows_out} dropped={dropped} fixed_name={fixed_name} filled_addr={filled_addr}")


if __name__ == "__main__":
    main()
