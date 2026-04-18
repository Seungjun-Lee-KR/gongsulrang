"use client";

import { useMemo, useState } from "react";
import RestaurantCard from "@/components/RestaurantCard";
import type { Restaurant } from "@/types/restaurant";
import { haversineMeters } from "@/lib/distance";
import { useGeolocation } from "@/hooks/useGeolocation";

type Props = {
  restaurants: Restaurant[];
};

const ALL = "전체";

type SortKey = "visits" | "totalAmount" | "avgAmount" | "deptCount" | "nearby";

const SORT_OPTIONS: { key: Exclude<SortKey, "nearby">; label: string }[] = [
  { key: "visits", label: "이용횟수" },
  { key: "totalAmount", label: "총금액" },
  { key: "avgAmount", label: "평균금액" },
  { key: "deptCount", label: "부서수" },
];

export default function RestaurantList({ restaurants }: Props) {
  const regions = useMemo(() => {
    const set = new Set(restaurants.map((r) => r.region));
    return [ALL, ...Array.from(set)];
  }, [restaurants]);

  const [query, setQuery] = useState("");
  const [selectedRegion, setSelectedRegion] = useState<string>(ALL);
  const [sortKey, setSortKey] = useState<SortKey>("visits");
  const { state: geoState, request: requestGeo } = useGeolocation();

  const userCoord = geoState.status === "success" ? geoState.coord : null;

  const distances = useMemo(() => {
    if (!userCoord) return null;
    const map = new Map<number, number>();
    for (const r of restaurants) {
      if (r.lat === undefined || r.lng === undefined) continue;
      map.set(r.rank, haversineMeters(userCoord, { lat: r.lat, lng: r.lng }));
    }
    return map;
  }, [restaurants, userCoord]);

  const items = useMemo(() => {
    const q = query.trim().toLowerCase();
    const filtered = restaurants.filter((r) => {
      if (selectedRegion !== ALL && r.region !== selectedRegion) return false;
      if (q && !r.name.toLowerCase().includes(q)) return false;
      if (sortKey === "nearby" && !distances?.has(r.rank)) return false;
      return true;
    });

    if (sortKey === "nearby" && distances) {
      return [...filtered].sort(
        (a, b) => (distances.get(a.rank) ?? Infinity) - (distances.get(b.rank) ?? Infinity),
      );
    }
    const key = sortKey as Exclude<SortKey, "nearby">;
    return [...filtered].sort((a, b) => b[key] - a[key]);
  }, [restaurants, selectedRegion, sortKey, query, distances]);

  const isFiltering = query.trim() !== "" || selectedRegion !== ALL;

  const handleNearbyClick = () => {
    if (userCoord) {
      setSortKey("nearby");
      return;
    }
    requestGeo();
    setSortKey("nearby");
  };

  return (
    <>
      <div className="mb-6">
        <div className="relative">
          <span
            aria-hidden
            className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-zinc-400"
          >
            🔍
          </span>
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="식당명 검색"
            className="w-full rounded-full border border-zinc-200 bg-white py-3 pl-11 pr-4 text-sm text-zinc-900 placeholder-zinc-400 focus:border-orange-400 focus:outline-none focus:ring-2 focus:ring-orange-200 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-100 dark:focus:ring-orange-900/50"
          />
        </div>
      </div>

      <div className="mb-6 flex flex-wrap gap-2">
        {regions.map((region) => {
          const active = region === selectedRegion;
          return (
            <button
              key={region}
              type="button"
              onClick={() => setSelectedRegion(region)}
              className={`rounded-full px-3.5 py-1.5 text-sm font-medium transition ${
                active
                  ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
                  : "bg-zinc-100 text-zinc-700 hover:bg-zinc-200 dark:bg-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-700"
              }`}
            >
              {region}
            </button>
          );
        })}
      </div>

      <div className="mb-6 flex flex-wrap items-center gap-2 text-sm">
        <span className="text-zinc-500 dark:text-zinc-400">정렬:</span>
        <div className="flex flex-wrap gap-1.5">
          <button
            type="button"
            onClick={handleNearbyClick}
            disabled={geoState.status === "loading"}
            className={`rounded-full px-3 py-1 text-xs font-medium transition ${
              sortKey === "nearby"
                ? "bg-orange-500 text-white"
                : "bg-transparent text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800"
            } disabled:opacity-60`}
          >
            📍 내 근처
            {geoState.status === "loading" && " ..."}
          </button>
          {SORT_OPTIONS.map(({ key, label }) => {
            const active = key === sortKey;
            return (
              <button
                key={key}
                type="button"
                onClick={() => setSortKey(key)}
                className={`rounded-full px-3 py-1 text-xs font-medium transition ${
                  active
                    ? "bg-orange-500 text-white"
                    : "bg-transparent text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800"
                }`}
              >
                {label} ↓
              </button>
            );
          })}
        </div>
      </div>

      {sortKey === "nearby" && geoState.status === "error" && (
        <p className="mb-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-900/40 dark:bg-amber-950/30 dark:text-amber-200">
          {geoState.message}
        </p>
      )}

      {items.length === 0 ? (
        <p className="rounded-xl border border-dashed border-zinc-300 py-16 text-center text-sm text-zinc-500 dark:border-zinc-700 dark:text-zinc-400">
          {sortKey === "nearby" && geoState.status !== "success"
            ? "위치를 가져온 뒤 근처 맛집이 표시됩니다."
            : isFiltering
              ? "검색 조건에 맞는 맛집이 없습니다."
              : "표시할 데이터가 없습니다."}
        </p>
      ) : (
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((r) => (
            <RestaurantCard
              key={r.rank}
              restaurant={r}
              distanceMeters={distances?.get(r.rank)}
            />
          ))}
        </div>
      )}
    </>
  );
}
