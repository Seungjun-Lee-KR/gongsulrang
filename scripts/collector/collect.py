"""
공슐랭 — 지방재정365 업무추진비 데이터 수집기
=============================================
지방재정365 Open API에서 전국 광역/기초지자체의
업무추진비 집행내역을 수집하여 식당별로 집계합니다.

⚠️  인증키는 절대 코드에 직접 입력하지 마세요.
    아래처럼 .env 파일에 저장 후 불러오세요.

    .env 파일 내용:
        LOFIN_API_KEY=<발급받은_지방재정365_API_키>

사용법:
    pip install requests pandas python-dotenv tqdm
    python gongsullaeng_data_collector.py
"""

import argparse
import os
import time
import json
import requests
import pandas as pd
from tqdm import tqdm
from dotenv import load_dotenv

# ── 인증키 로드 (.env 파일에서 읽어옴) ──────────────────────────────
load_dotenv()
API_KEY = os.getenv("LOFIN_API_KEY")
if not API_KEY:
    raise ValueError("LOFIN_API_KEY가 .env 파일에 없습니다.")

# ── 지방재정365 API 기본 설정 ────────────────────────────────────────
BASE_URL = "http://lofin.mois.go.kr/HUB"

# 업무추진비 관련 주요 테이블 코드
# (지방재정365 개발자공간 > API 목록에서 확인 가능)
TABLES = {
    "업무추진비_집행내역":    "GRCBDAL",   # 업무추진비 나눠쓰기 집행내역
    "세출예산_집행현황":      "CDDFA",     # 회계별 단체별 세출결산
    "기능별_세출결산":        "GGNSE",     # 구조별/기능별 세출결산
}

# 전국 광역지자체 코드 (17개)
SIDO_CODES = {
    "서울특별시":    "6110000",
    "부산광역시":    "6260000",
    "대구광역시":    "6270000",
    "인천광역시":    "6280000",
    "광주광역시":    "6290000",
    "대전광역시":    "6300000",
    "울산광역시":    "6310000",
    "세종특별자치시": "5690000",
    "경기도":       "6410000",
    "강원도":       "6420000",
    "충청북도":      "6430000",
    "충청남도":      "6440000",
    "전라북도":      "6450000",
    "전라남도":      "6460000",
    "경상북도":      "6470000",
    "경상남도":      "6480000",
    "제주특별자치도": "6500000",
}


def fetch_lofin(table_code: str, year: int, sido_code: str = None,
                page: int = 1, page_size: int = 100) -> dict:
    """
    지방재정365 API 단일 페이지 호출

    Parameters
    ----------
    table_code : str   API 테이블 코드 (예: 'GRCBDAL')
    year       : int   회계연도 (예: 2024)
    sido_code  : str   지자체 코드 (None이면 전국)
    page       : int   페이지 번호 (1부터 시작)
    page_size  : int   페이지당 건수 (최대 100)

    Returns
    -------
    dict  API 응답 JSON
    """
    url = f"{BASE_URL}/{table_code}"
    params = {
        "key":         API_KEY,
        "type":        "json",
        "pindex":      page,
        "psize":       page_size,
        "accnut_year": year,
    }
    if sido_code:
        params["sido_code"] = sido_code

    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


def fetch_all_pages(table_code: str, year: int,
                    sido_code: str = None) -> list[dict]:
    """
    지방재정365 API 전체 페이지 수집 (페이지네이션 자동 처리)
    """
    records = []
    page = 1

    while True:
        try:
            data = fetch_lofin(table_code, year, sido_code, page)
        except requests.HTTPError as e:
            print(f"  HTTP 오류 (page={page}): {e}")
            break

        # API 응답 구조: {"RESULT": {"CODE": "INFO-000", ...}, "row": [...]}
        result_code = data.get("RESULT", {}).get("CODE", "")
        if result_code != "INFO-000":
            # 더 이상 데이터 없음
            break

        rows = data.get("row", [])
        if not rows:
            break

        records.extend(rows)
        print(f"    page {page}: {len(rows)}건 수집 (누계 {len(records)}건)")

        if len(rows) < 100:
            # 마지막 페이지
            break

        page += 1
        time.sleep(0.3)   # API 과호출 방지

    return records


def collect_business_cost(years: list[int], sidos: dict[str, str] | None = None) -> pd.DataFrame:
    """
    전국 광역지자체별 업무추진비 집행내역 수집

    업무추진비 집행내역 주요 필드:
        - SELF_GVNM_NM  : 자치단체명
        - DEPT_NM       : 부서명
        - ACNT_NM       : 세부사업명 / 계정명
        - EXPNDTR_DE    : 집행일자
        - VENDER_NM     : 가맹점명 (식당명)
        - USE_AMNTHG    : 사용금액
        - USE_CN        : 사용내용 (목적)
        - MLSFC_NM      : 세목명 (업무추진비 구분)
    """
    all_records = []
    target_sidos = sidos if sidos is not None else SIDO_CODES

    for year in years:
        print(f"\n📅 {year}년 업무추진비 수집 시작")
        for sido_name, sido_code in tqdm(target_sidos.items(),
                                         desc=f"{year}년 광역지자체"):
            print(f"\n  🏛️  {sido_name} ({sido_code})")
            records = fetch_all_pages(
                table_code="GRCBDAL",   # 업무추진비 집행내역 테이블
                year=year,
                sido_code=sido_code,
            )
            for r in records:
                r["_year"] = year
                r["_sido"] = sido_name
            all_records.extend(records)

    if not all_records:
        print("⚠️  수집된 데이터가 없습니다. 테이블 코드를 확인하세요.")
        return pd.DataFrame()

    df = pd.DataFrame(all_records)
    print(f"\n✅ 총 {len(df):,}건 수집 완료")
    return df


def aggregate_restaurants(df: pd.DataFrame) -> pd.DataFrame:
    """
    식당(가맹점)별 이용 횟수 / 금액 집계
    → 공슐랭 랭킹 데이터 생성
    """
    if df.empty:
        return df

    # 금액 컬럼 숫자 변환
    df["USE_AMNTHG"] = pd.to_numeric(df["USE_AMNTHG"], errors="coerce").fillna(0)

    # 식당명 기준 집계
    grouped = (
        df.groupby(["VENDER_NM", "_sido"])
        .agg(
            이용횟수   = ("USE_AMNTHG", "count"),
            총이용금액  = ("USE_AMNTHG", "sum"),
            평균금액   = ("USE_AMNTHG", "mean"),
            집행부서수  = ("DEPT_NM", "nunique"),
        )
        .reset_index()
        .rename(columns={"VENDER_NM": "식당명", "_sido": "지역"})
        .sort_values("이용횟수", ascending=False)
    )

    grouped["순위"] = range(1, len(grouped) + 1)
    grouped["평균금액"] = grouped["평균금액"].round(0).astype(int)

    return grouped


def save_results(df_raw: pd.DataFrame, df_ranked: pd.DataFrame,
                 output_dir: str = "."):
    """수집 결과를 CSV로 저장"""
    os.makedirs(output_dir, exist_ok=True)

    raw_path    = os.path.join(output_dir, "업무추진비_원본.csv")
    ranked_path = os.path.join(output_dir, "공슐랭_랭킹.csv")

    df_raw.to_csv(raw_path, index=False, encoding="utf-8-sig")
    df_ranked.to_csv(ranked_path, index=False, encoding="utf-8-sig")

    print(f"\n💾 저장 완료")
    print(f"   원본 데이터  : {raw_path}")
    print(f"   공슐랭 랭킹  : {ranked_path}")


def parse_args():
    p = argparse.ArgumentParser(
        description="공슐랭 — 지방재정365 업무추진비 데이터 수집기",
    )
    p.add_argument(
        "--years", type=int, nargs="+", default=[2022, 2023, 2024],
        help="수집 회계연도 (예: --years 2024 또는 --years 2022 2023 2024)",
    )
    p.add_argument(
        "--sido", type=str, nargs="+", default=None,
        help="수집할 시도명 (예: --sido 서울특별시). 미지정 시 전국 17개.",
    )
    p.add_argument(
        "--output", type=str, default="./data",
        help="출력 디렉터리 (기본: ./data)",
    )
    return p.parse_args()


def main():
    args = parse_args()

    print("=" * 55)
    print("  공슐랭 — 지방재정365 업무추진비 데이터 수집기")
    print("=" * 55)
    print(f"  연도: {args.years}")
    print(f"  시도: {args.sido or '전국 17개'}")
    print(f"  출력: {args.output}")
    print("=" * 55)

    selected_sidos = None
    if args.sido:
        unknown = [s for s in args.sido if s not in SIDO_CODES]
        if unknown:
            print(f"❌ 알 수 없는 시도명: {unknown}")
            print(f"   사용 가능: {list(SIDO_CODES.keys())}")
            return
        selected_sidos = {s: SIDO_CODES[s] for s in args.sido}

    df_raw = collect_business_cost(years=args.years, sidos=selected_sidos)

    if df_raw.empty:
        print("\n❌ 데이터 수집 실패. API 키 또는 테이블 코드를 확인하세요.")
        print("   지방재정365 개발자공간: https://lofin.mois.go.kr")
        return

    print("\n🍽️  식당별 집계 중...")
    df_ranked = aggregate_restaurants(df_raw)

    save_results(df_raw, df_ranked, output_dir=args.output)

    print("\n🏆 공슐랭 TOP 20 미리보기")
    print("-" * 55)
    print(df_ranked.head(20).to_string(index=False))


if __name__ == "__main__":
    main()
