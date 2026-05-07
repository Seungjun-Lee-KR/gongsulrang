"""Naver 캐시 키 포맷 마이그레이션: {name}|{addr} → {name}|{region}|{addr}.
gongsulrang_ranking_seoul_2024_geo.csv를 룩업 테이블로 사용.
"""

import os as _os
from pathlib import Path as _Path
_os.chdir(_Path(__file__).resolve().parent.parent)
import csv
import json
import os
import shutil

CACHE = "data/output/.naver_cache.json"
RANK = "data/output/gongsulrang_ranking_seoul_2024_geo.csv"
BAK = CACHE + ".bak"


def main():
    cache = json.load(open(CACHE, encoding="utf-8"))
    if not os.path.exists(BAK):
        shutil.copy2(CACHE, BAK)
        print(f"백업: {BAK}")

    # name|addr → region 룩업 테이블
    name_addr_to_region: dict[tuple[str, str], str] = {}
    for r in csv.DictReader(open(RANK, encoding="utf-8-sig")):
        n = (r["식당명"] or "").strip()
        a = (r["주소"] or "").strip()
        rg = (r["지역"] or "").strip()
        name_addr_to_region.setdefault((n, a), rg)

    new_cache: dict[str, dict] = {}
    migrated = 0
    skipped = 0
    already = 0
    for k, v in cache.items():
        # 이미 새 포맷이면 그대로
        if k.count("|") >= 2:
            new_cache[k] = v
            already += 1
            continue
        # 옛 포맷
        name, _, addr = k.partition("|")
        region = name_addr_to_region.get((name, addr), "")
        if not region:
            # 못 찾으면 그래도 보존 (새 키에 region="" 빈값)
            skipped += 1
        new_key = f"{name}|{region}|{addr}"
        new_cache[new_key] = v
        migrated += 1
    json.dump(new_cache, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"migrated={migrated} no_region_lookup={skipped} already_new={already} total={len(new_cache)}")


if __name__ == "__main__":
    main()
