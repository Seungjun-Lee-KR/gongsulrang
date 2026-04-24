"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import KakaoMap, { type MapMarker } from "@/components/KakaoMap";
import { useGeolocation } from "@/hooks/useGeolocation";
import { formatDistance, haversineMeters } from "@/lib/distance";
import { formatWon } from "@/lib/format";
import { loadKakaoMaps, searchPlaceByKeyword, type PlaceHit } from "@/lib/kakao-maps";
import type { Coord } from "@/lib/distance";
import type { Restaurant } from "@/types/restaurant";

type Props = {
  restaurants: Restaurant[];
};

const RADIUS_OPTIONS = [
  { m: 500, label: "0.5km" },
  { m: 700, label: "0.7km" },
  { m: 1000, label: "1km" },
  { m: 2000, label: "2km" },
] as const;

const TOP_N = 10;

type Ranked = Restaurant & { distanceM?: number; localRank: number };

type SearchCenter = {
  coord: Coord;
  label: string;
  address: string;
};

const appkey = process.env.NEXT_PUBLIC_KAKAO_MAP_KEY;

export default function NearbyLeaderboard({ restaurants }: Props) {
  const [radiusM, setRadiusM] = useState<number>(1000);
  const [query, setQuery] = useState("");
  const [searchCenter, setSearchCenter] = useState<SearchCenter | null>(null);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const { state: geoState, request: requestGeo } = useGeolocation();

  useEffect(() => {
    requestGeo();
  }, [requestGeo]);

  const geoCoord = geoState.status === "success" ? geoState.coord : null;
  const effectiveCoord: Coord | null = searchCenter?.coord ?? geoCoord;
  const usingSearch = searchCenter !== null;

  const handleSearch = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      const q = query.trim();
      if (!q) return;
      if (!appkey) {
        setSearchError("Kakao 지도 키가 설정되지 않았습니다.");
        return;
      }
      setSearching(true);
      setSearchError(null);
      try {
        const hit = await resolvePlace(q, appkey);
        if (!hit) {
          setSearchError(`"${q}" 검색 결과가 없습니다.`);
          return;
        }
        setSearchCenter({
          coord: { lat: hit.lat, lng: hit.lng },
          label: hit.name,
          address: hit.address,
        });
      } catch (err) {
        setSearchError(err instanceof Error ? err.message : "검색에 실패했습니다.");
      } finally {
        setSearching(false);
      }
    },
    [query],
  );

  const clearSearch = useCallback(() => {
    setSearchCenter(null);
    setSearchError(null);
    setQuery("");
  }, []);

  const withCoord = useMemo(
    () =>
      restaurants.filter(
        (r): r is Restaurant & { lat: number; lng: number } =>
          r.lat !== undefined && r.lng !== undefined,
      ),
    [restaurants],
  );

  const sortedByAmount = useMemo(
    () => [...withCoord].sort((a, b) => b.totalAmount - a.totalAmount),
    [withCoord],
  );

  const nearby: Ranked[] = useMemo(() => {
    if (!effectiveCoord) return [];
    return withCoord
      .map((r) => ({
        ...r,
        distanceM: haversineMeters(effectiveCoord, { lat: r.lat, lng: r.lng }),
      }))
      .filter((r) => r.distanceM <= radiusM)
      .sort((a, b) => b.totalAmount - a.totalAmount)
      .slice(0, TOP_N)
      .map((r, i) => ({ ...r, localRank: i + 1 }));
  }, [withCoord, effectiveCoord, radiusM]);

  const fallback: Ranked[] = useMemo(
    () =>
      sortedByAmount
        .slice(0, TOP_N)
        .map((r, i) => ({ ...r, localRank: i + 1 })),
    [sortedByAmount],
  );

  const isFallback = !effectiveCoord || nearby.length === 0;
  const items: Ranked[] = isFallback ? fallback : nearby;

  const markers: MapMarker[] = items.map((r) => ({
    id: r.rank,
    lat: r.lat!,
    lng: r.lng!,
    label: `${r.localRank}. ${r.name}`,
    href: `/restaurant/${r.rank}`,
  }));

  const statusLabel = (() => {
    if (usingSearch) {
      if (nearby.length === 0)
        return `${searchCenter!.label} 주변 ${formatRadius(radiusM)}에 맛집이 없어 전체 TOP ${TOP_N}을 표시합니다`;
      return `${searchCenter!.label} 주변 ${formatRadius(radiusM)} 총금액 TOP ${nearby.length}`;
    }
    if (geoState.status === "loading") return "위치 확인 중…";
    if (geoState.status === "error") return `전체 총금액 TOP ${TOP_N} (${geoState.message})`;
    if (geoState.status === "success" && nearby.length === 0)
      return `반경 내 맛집이 없어 전체 총금액 TOP ${TOP_N}을 표시합니다`;
    if (geoState.status === "success")
      return `내 주변 ${formatRadius(radiusM)} 총금액 TOP ${nearby.length}`;
    return `전체 총금액 TOP ${TOP_N}`;
  })();

  const headline = usingSearch
    ? `${searchCenter!.label} 주변 공무원 맛집 TOP10`
    : "공무원들이 자주 찾는 내 주변 맛집 TOP10";

  return (
    <section className="mx-auto max-w-6xl px-6 pb-16">
      <div className="mb-4">
        <SearchForm
          query={query}
          onQueryChange={setQuery}
          onSubmit={handleSearch}
          searching={searching}
          searchCenter={searchCenter}
          onClear={clearSearch}
          error={searchError}
        />
      </div>

      <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">
            {headline}
          </h2>
          <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
            {statusLabel}
          </p>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {RADIUS_OPTIONS.map(({ m, label }) => {
            const active = m === radiusM;
            return (
              <button
                key={m}
                type="button"
                onClick={() => setRadiusM(m)}
                className={`rounded-full px-3 py-1 text-xs font-medium transition ${
                  active
                    ? "bg-orange-500 text-white"
                    : "bg-zinc-100 text-zinc-700 hover:bg-zinc-200 dark:bg-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-700"
                }`}
              >
                {label}
              </button>
            );
          })}
        </div>
      </div>

      <ol className="mb-8 grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-5">
        {items.map((r) => (
          <LeaderboardRow key={r.rank} item={r} />
        ))}
      </ol>

      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">
          지도에서 보기
        </h3>
        {!usingSearch && geoState.status === "error" && (
          <button
            type="button"
            onClick={requestGeo}
            className="text-xs font-medium text-orange-600 hover:underline dark:text-orange-400"
          >
            위치 다시 시도
          </button>
        )}
      </div>
      <KakaoMap
        markers={markers}
        userCoord={effectiveCoord}
        userCircleRadius={effectiveCoord && !isFallback ? radiusM : undefined}
        className="h-[420px] w-full"
      />
    </section>
  );
}

type SearchFormProps = {
  query: string;
  onQueryChange: (v: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  searching: boolean;
  searchCenter: SearchCenter | null;
  onClear: () => void;
  error: string | null;
};

function SearchForm({
  query,
  onQueryChange,
  onSubmit,
  searching,
  searchCenter,
  onClear,
  error,
}: SearchFormProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  return (
    <div className="rounded-2xl border border-zinc-200 bg-white p-3 dark:border-zinc-800 dark:bg-zinc-900">
      <form onSubmit={onSubmit} className="flex gap-2">
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          placeholder="지역·지하철역·동 이름 (예: 고덕역, 여의도, 강남역)"
          className="flex-1 rounded-full border border-zinc-300 bg-white px-4 py-2 text-sm text-zinc-900 placeholder:text-zinc-400 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500/30 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-50"
          disabled={searching}
        />
        <button
          type="submit"
          disabled={searching || query.trim().length === 0}
          className="rounded-full bg-orange-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-orange-600 disabled:cursor-not-allowed disabled:bg-zinc-300 dark:disabled:bg-zinc-700"
        >
          {searching ? "검색 중…" : "주변 검색"}
        </button>
      </form>
      <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
        {searchCenter ? (
          <>
            <span className="inline-flex items-center gap-1 rounded-full bg-orange-50 px-2.5 py-1 font-medium text-orange-700 dark:bg-orange-500/10 dark:text-orange-300">
              <span aria-hidden>📍</span>
              {searchCenter.label}
              {searchCenter.address ? (
                <span className="text-orange-600/70 dark:text-orange-300/70">
                  · {searchCenter.address}
                </span>
              ) : null}
            </span>
            <button
              type="button"
              onClick={onClear}
              className="text-zinc-500 hover:text-zinc-800 hover:underline dark:text-zinc-400 dark:hover:text-zinc-100"
            >
              내 위치로 돌아가기
            </button>
          </>
        ) : (
          <span className="text-zinc-500 dark:text-zinc-400">
            원하는 지역을 입력하면 그 주변의 공무원 맛집을 볼 수 있습니다.
          </span>
        )}
        {error ? (
          <span className="text-red-600 dark:text-red-400">{error}</span>
        ) : null}
      </div>
    </div>
  );
}

function LeaderboardRow({ item }: { item: Ranked }) {
  const { localRank, name, region, visits, totalAmount, distanceM, rank } = item;
  return (
    <li>
      <Link
        href={`/restaurant/${rank}`}
        className="group flex items-center gap-4 rounded-xl border border-zinc-200 bg-white px-4 py-3 transition hover:border-orange-300 hover:shadow-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-500 dark:border-zinc-800 dark:bg-zinc-900 dark:hover:border-orange-700/60"
      >
        <span
          className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-bold ${rankBadgeClass(
            localRank,
          )}`}
        >
          {localRank}
        </span>
        <div className="min-w-0 flex-1">
          <div className="truncate text-base font-semibold text-zinc-900 dark:text-zinc-50">
            {name}
          </div>
          <div className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-zinc-500 dark:text-zinc-400">
            <span>{region}</span>
            {distanceM !== undefined && (
              <>
                <span aria-hidden>·</span>
                <span className="font-medium text-orange-600 dark:text-orange-400">
                  📍 {formatDistance(distanceM)}
                </span>
              </>
            )}
          </div>
        </div>
        <div className="flex shrink-0 flex-col items-end">
          <span className="text-sm font-bold text-zinc-900 dark:text-zinc-50">
            {formatWon(totalAmount)}
          </span>
          <span className="text-[11px] text-zinc-500 dark:text-zinc-400">
            {visits.toLocaleString()}회
          </span>
        </div>
      </Link>
    </li>
  );
}

function rankBadgeClass(rank: number): string {
  if (rank === 1) return "bg-amber-400 text-amber-950";
  if (rank === 2) return "bg-zinc-300 text-zinc-800";
  if (rank === 3) return "bg-orange-300 text-orange-950";
  return "bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300";
}

function formatRadius(m: number): string {
  if (m < 1000) return `${m}m`;
  return `${m / 1000}km`;
}

async function resolvePlace(query: string, appkey: string): Promise<PlaceHit | null> {
  try {
    const r = await fetch(`/api/places?q=${encodeURIComponent(query)}`);
    if (r.ok) {
      return (await r.json()) as PlaceHit;
    }
    if (r.status === 404) return null;
  } catch {
    // server route unreachable — fall back to SDK
  }
  await loadKakaoMaps(appkey);
  return searchPlaceByKeyword(query);
}
