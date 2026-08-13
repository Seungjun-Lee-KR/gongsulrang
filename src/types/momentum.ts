export type MomentumKakao = {
  id: string;
  category: string;
  address: string;
  url: string;
  lat: number;
  lng: number;
};

export type MomentumEntry = {
  /** 카카오 공식 상호, 미매칭 시 장부상 표기 */
  name: string;
  /** 분기별 방문수 (quarters와 같은 길이) */
  series: number[];
  /** 최근 2분기 방문수 합 */
  recent: number;
  /** 전년 동분기 방문수 합 */
  base: number;
  /** 최근 2분기 이용 부서 수 */
  depts: number;
  avgAmount: number;
  /** 장부상 표기 변형 수 */
  variants: number;
  /** 카카오 장소 매칭 결과. null이면 장부명 그대로 */
  kakao: MomentumKakao | null;
  /** rising 항목만: 전년 동기 대비 성장 배수 */
  growth?: number;
  /** steady 항목만: 분기 방문수 변동계수 (낮을수록 꾸준) */
  cv?: number;
  /** 인당 지출 중앙값 (결제액/인원, "과장 등 6명" 파싱). 표본 5건 미만이면 null */
  perPerson?: number | null;
  /** 인당 지출 표본 수 */
  perPersonN?: number;
  /** 끼니 분류 행수 — timed가 분모 (시간·목적으로 분류된 전체) */
  lunch?: number;
  dinner?: number;
  timed?: number;
  /** lunchSpots/dinnerSpots 항목만 */
  lunchShare?: number;
  dinnerShare?: number;
};

export type MomentumData = {
  source: string;
  quarters: string[];
  recentQuarters: string[];
  baseQuarters: string[];
  rising: MomentumEntry[];
  newcomers: MomentumEntry[];
  steady: MomentumEntry[];
  /** 점심(11–14시) 비중 70% 이상 — 방문수 순 */
  lunchSpots: MomentumEntry[];
  /** 저녁(17시 이후) 비중 50% 이상 — 방문수 순 */
  dinnerSpots: MomentumEntry[];
  stats: {
    transactions: number;
    restaurants: number;
    candidates: number;
    kakaoMatched: number;
    kakaoUnmatched: number;
    kakaoMerged: number;
  };
};

/** scripts/15가 만드는 자치구별 모멘텀 — 본청과 같은 구조 + 구 식별자 */
export type DistrictMomentum = MomentumData & {
  /** CSV 접두 (예: "gangnam") */
  slug: string;
  /** 한글 구명 (예: "강남구") — URL 세그먼트로도 쓴다 */
  name: string;
};

export type DistrictMomentumFile = {
  districts: DistrictMomentum[];
};
