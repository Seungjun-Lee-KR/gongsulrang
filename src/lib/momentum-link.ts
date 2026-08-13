import { momentum } from "@/data/momentum";
import { districtMomentum } from "@/data/momentum-districts";
import { restaurants } from "@/data/restaurants";
import type { MomentumData, MomentumEntry } from "@/types/momentum";

/**
 * 모멘텀 보드의 카카오 매칭 가게 ↔ 누적 랭킹(restaurants.json) 연결.
 *
 * 두 데이터의 장소 id 체계가 다르다(모멘텀=카카오, 누적=구글 placeId).
 * 대신 양쪽 다 좌표와 상호가 있으므로 150m 근접 + 이름 유사로 조인한다.
 * 모듈 로드 시 한 번 계산 — 서버 컴포넌트에서만 임포트할 것.
 */

export const BOARD_LABELS = {
  rising: "뜨는 집",
  newcomers: "신규 진입",
  steady: "스테디셀러",
  lunchSpots: "점심 명당",
  dinnerSpots: "저녁 회식 명당",
} as const;

export type BoardKey = keyof typeof BOARD_LABELS;

export type MomentumAppearance = {
  /** "서울시 본청" 또는 구명 */
  scope: string;
  /** 해당 트렌딩 페이지 경로 */
  href: string;
  quarters: string[];
  entry: MomentumEntry;
  boards: { key: BoardKey; label: string; position: number }[];
};

const MAX_DIST_M = 150;

function normalizeName(s: string): string {
  return s
    .replace(/\(주\)|㈜|주식회사/g, "")
    .replace(/\s*[(（][^)）]*[)）]?\s*$/, "")
    .replace(/\s+/g, "")
    .trim();
}

function bigrams(s: string): Set<string> {
  if (s.length <= 1) return new Set([s]);
  const out = new Set<string>();
  for (let i = 0; i < s.length - 1; i++) out.add(s.slice(i, i + 2));
  return out;
}

function nameSimilar(a: string, b: string): boolean {
  const na = normalizeName(a);
  const nb = normalizeName(b);
  if (!na || !nb) return false;
  if (na.length >= 2 && nb.length >= 2 && (na.includes(nb) || nb.includes(na)))
    return true;
  const A = bigrams(na);
  const B = bigrams(nb);
  let inter = 0;
  for (const g of A) if (B.has(g)) inter++;
  return inter / (A.size + B.size - inter) >= 0.5;
}

function distanceM(lat1: number, lng1: number, lat2: number, lng2: number) {
  // 서울 규모의 근거리 비교엔 equirectangular 근사로 충분하다
  const dy = (lat1 - lat2) * 111320;
  const dx = (lng1 - lng2) * 111320 * Math.cos((lat1 * Math.PI) / 180);
  return Math.sqrt(dx * dx + dy * dy);
}

// 좌표 그리드(~220m 셀)로 후보를 좁힌다 — 전수 비교 방지
const CELL = 0.002;
const grid = new Map<string, number[]>(); // cellKey → restaurants 인덱스
restaurants.forEach((r, i) => {
  if (r.lat === undefined || r.lng === undefined) return;
  const key = `${Math.round(r.lat / CELL)}:${Math.round(r.lng / CELL)}`;
  const arr = grid.get(key);
  if (arr) arr.push(i);
  else grid.set(key, [i]);
});

function findRank(name: string, lat: number, lng: number): number | undefined {
  const cy = Math.round(lat / CELL);
  const cx = Math.round(lng / CELL);
  let best: { rank: number; dist: number } | undefined;
  for (let dy = -1; dy <= 1; dy++) {
    for (let dx = -1; dx <= 1; dx++) {
      for (const i of grid.get(`${cy + dy}:${cx + dx}`) ?? []) {
        const r = restaurants[i];
        const dist = distanceM(lat, lng, r.lat!, r.lng!);
        if (dist > MAX_DIST_M || !nameSimilar(name, r.name)) continue;
        if (!best || dist < best.dist) best = { rank: r.rank, dist };
      }
    }
  }
  return best?.rank;
}

const rankOfKakaoId = new Map<string, number>();
const appearancesOfRank = new Map<number, MomentumAppearance[]>();

function collect(data: MomentumData, scope: string, href: string) {
  const byRank = new Map<number, MomentumAppearance>();
  (Object.keys(BOARD_LABELS) as BoardKey[]).forEach((key) => {
    (data[key] ?? []).forEach((entry, idx) => {
      if (!entry.kakao) return;
      let rank = rankOfKakaoId.get(entry.kakao.id);
      if (rank === undefined) {
        rank = findRank(entry.name, entry.kakao.lat, entry.kakao.lng);
        if (rank === undefined) return;
        rankOfKakaoId.set(entry.kakao.id, rank);
      }
      let app = byRank.get(rank);
      if (!app) {
        app = { scope, href, quarters: data.quarters, entry, boards: [] };
        byRank.set(rank, app);
      }
      app.boards.push({ key, label: BOARD_LABELS[key], position: idx + 1 });
    });
  });
  byRank.forEach((app, rank) => {
    const arr = appearancesOfRank.get(rank);
    if (arr) arr.push(app);
    else appearancesOfRank.set(rank, [app]);
  });
}

collect(momentum, "서울시 본청", "/trending");
districtMomentum.forEach((d) =>
  collect(d, d.name, `/trending/${encodeURIComponent(d.name)}`),
);

/** 트렌딩 행 → 누적 랭킹 상세 링크용 */
export function getRankForKakaoId(id: string): number | undefined {
  return rankOfKakaoId.get(id);
}

/** 식당 상세 → 모멘텀 출연 목록 (본청·자치구 각각 최대 1건) */
export function getMomentumForRank(rank: number): MomentumAppearance[] {
  return appearancesOfRank.get(rank) ?? [];
}
