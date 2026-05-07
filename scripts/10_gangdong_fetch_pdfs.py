"""
10단계(강동구): posts.json의 PDF UUID → 실제 PDF 다운로드

- 입력: output/gangdong_posts.json
- 출력: output/gangdong_pdfs/{uuid}.pdf
- 재시작 안전: 이미 파일이 있으면 스킵
"""

import os as _os
from pathlib import Path as _Path
_os.chdir(_Path(__file__).resolve().parent.parent)
import json
import os
import time

import requests

POSTS = "data/output/gangdong_posts.json"
OUT_DIR = "data/output/gangdong_pdfs"
URL = "https://www.gangdong.go.kr/web/newportal/file/download/uu/{uuid}"
HEADERS = {"User-Agent": "Mozilla/5.0 (gongsulrang-collector; edu-research)"}
RATE = 0.6


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    posts = json.load(open(POSTS, encoding="utf-8"))
    todo = [p for p in posts if p.get("pdf_uuid")]
    print(f"PDF 대상: {len(todo)}건")

    n_ok = n_skip = n_err = 0
    for i, p in enumerate(todo, 1):
        uuid = p["pdf_uuid"]
        path = os.path.join(OUT_DIR, f"{uuid}.pdf")
        if os.path.exists(path) and os.path.getsize(path) > 1000:
            n_skip += 1
            continue
        try:
            r = requests.get(URL.format(uuid=uuid), headers=HEADERS, timeout=30)
            r.raise_for_status()
            if not r.content.startswith(b"%PDF"):
                print(f"  [{i}/{len(todo)}] id={p['id']} non-pdf content — 스킵")
                n_err += 1
                continue
            with open(path, "wb") as f:
                f.write(r.content)
            n_ok += 1
        except Exception as e:
            print(f"  [{i}/{len(todo)}] id={p['id']} err={e}")
            n_err += 1
        if i % 25 == 0 or i == len(todo):
            print(f"  [{i}/{len(todo)}] ok+={n_ok} skip={n_skip} err={n_err}")
        time.sleep(RATE)

    print(f"\n✅ ok={n_ok} skip(이미있음)={n_skip} err={n_err} → {OUT_DIR}")


if __name__ == "__main__":
    main()
