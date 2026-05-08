"""
12단계: places_enrich.json의 ok 항목 중 photo_refs 비어있는 항목에 대해
        Google Place Details (photos field만) 호출로 photo `name`을 백필.

- 입력: data/output/places_enrich.json
- 출력: 동일 파일에 photo_refs 채워서 in-place 업데이트
- API: Place Details (New) — Field Mask "photos" (Pro tier ~$17/1k)
- 사용 사례: 옵션 B (동적 프록시) 전환 시 기존 enrich 데이터에 ref만 추가

비용: 약 3000건 호출 → ~$51 (Google 무료 크레딧 $200 안에서)

사용:
    python3 scripts/12_backfill_photo_refs.py             # 모든 ok 항목 처리
    python3 scripts/12_backfill_photo_refs.py --limit 50  # 처음 50개만 (테스트용)
    python3 scripts/12_backfill_photo_refs.py --dry-run   # 실제 호출 없이 대상 카운트만
"""

import os as _os
from pathlib import Path as _Path
_os.chdir(_Path(__file__).resolve().parent.parent)
import argparse
import json
import os
import sys
import time

import requests
from dotenv import load_dotenv

load_dotenv(".env.local")
KEY = os.getenv("GOOGLE_PLACES_API_KEY")
if not KEY:
    print("GOOGLE_PLACES_API_KEY가 .env.local에 없습니다.")
    sys.exit(1)

ENRICH = "data/output/places_enrich.json"
DETAILS_URL = "https://places.googleapis.com/v1/places/{pid}"
FIELD_MASK = "photos"
PHOTO_MAX = 3
RATE = 0.1
SAVE_EVERY = 50


def fetch_photo_refs(pid: str) -> tuple[list[str], str]:
    r = requests.get(
        DETAILS_URL.format(pid=pid),
        headers={
            "X-Goog-Api-Key": KEY,
            "X-Goog-FieldMask": FIELD_MASK,
        },
        timeout=15,
    )
    if r.status_code != 200:
        return [], f"http_{r.status_code}"
    data = r.json()
    photos = data.get("photos") or []
    return [p["name"] for p in photos[:PHOTO_MAX] if "name" in p], "ok"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="처음 N개만 처리 (테스트용)")
    ap.add_argument("--dry-run", action="store_true", help="API 호출 없이 대상만 카운트")
    args = ap.parse_args()

    if not os.path.exists(ENRICH):
        print(f"❌ {ENRICH} 없음")
        sys.exit(1)

    with open(ENRICH, encoding="utf-8") as f:
        enrich = json.load(f)

    targets = []
    for k, v in enrich.items():
        if v.get("status") != "ok":
            continue
        if not v.get("place_id"):
            continue
        if v.get("photo_refs"):
            continue
        targets.append(k)

    total_ok = sum(1 for v in enrich.values() if v.get("status") == "ok")
    print(f"places_enrich.json ok 항목: {total_ok}")
    print(f"백필 대상 (photo_refs 없음): {len(targets)}")

    if args.limit:
        targets = targets[:args.limit]
        print(f"--limit {args.limit} → {len(targets)}건만 처리")

    if args.dry_run:
        print("dry-run: API 호출 없이 종료")
        return

    if not targets:
        print("처리할 대상 없음.")
        return

    est_cost_usd = len(targets) * 0.017
    print(f"예상 호출: {len(targets)}건 (~${est_cost_usd:.2f})")

    n_ok = n_fail = n_no_photos = 0
    for i, key in enumerate(targets, 1):
        v = enrich[key]
        pid = v["place_id"]
        try:
            refs, status = fetch_photo_refs(pid)
        except Exception as ex:
            refs, status = [], f"err:{type(ex).__name__}: {ex}"

        if status == "ok":
            v["photo_refs"] = refs
            if refs:
                n_ok += 1
            else:
                n_no_photos += 1
        else:
            n_fail += 1
            v["photo_refs_status"] = status

        if i % SAVE_EVERY == 0 or i == len(targets):
            with open(ENRICH, "w", encoding="utf-8") as f:
                json.dump(enrich, f, ensure_ascii=False, indent=2)
            print(f"  [{i}/{len(targets)}] ok_with_photos={n_ok} no_photos={n_no_photos} fail={n_fail}")

        time.sleep(RATE)

    print(f"\n✅ 완료: ok_with_photos={n_ok} no_photos={n_no_photos} fail={n_fail} / {len(targets)}")


if __name__ == "__main__":
    main()
