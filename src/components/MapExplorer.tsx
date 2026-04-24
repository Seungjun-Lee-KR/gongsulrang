"use client";

import { useMemo, useState } from "react";
import KakaoMap, { type MapMarker } from "@/components/KakaoMap";
import type { Restaurant } from "@/types/restaurant";
import { formatWon } from "@/lib/format";

const ALL = "전체";
const LIMIT_OPTIONS = [50, 100, 300, 1000];

type Props = {
  restaurants: Restaurant[];
};

export default function MapExplorer({ restaurants }: Props) {
  const geocoded = useMemo(
    () => restaurants.filter((r) => r.lat !== undefined && r.lng !== undefined),
    [restaurants],
  );

  const regions = useMemo(() => {
    const s = new Set(geocoded.map((r) => r.region));
    return [ALL, ...Array.from(s).sort()];
  }, [geocoded]);

  const [region, setRegion] = useState<string>(ALL);
  const [limit, setLimit] = useState<number>(100);
  const [hovered, setHovered] = useState<number | null>(null);

  const filtered = useMemo(() => {
    const list = region === ALL ? geocoded : geocoded.filter((r) => r.region === region);
    return [...list].sort((a, b) => b.visits - a.visits).slice(0, limit);
  }, [geocoded, region, limit]);

  const markers: MapMarker[] = useMemo(
    () =>
      filtered.map((r) => ({
        id: r.rank,
        lat: r.lat!,
        lng: r.lng!,
        label: r.name,
        href: `/restaurant/${r.rank}`,
      })),
    [filtered],
  );

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-3 text-sm">
        <div className="flex items-center gap-2">
          <span className="text-zinc-500 dark:text-zinc-400">지역:</span>
          <select
            value={region}
            onChange={(e) => setRegion(e.target.value)}
            className="rounded-full border border-zinc-200 bg-white px-3 py-1.5 text-sm text-zinc-800 focus:border-orange-400 focus:outline-none dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-200"
          >
            {regions.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-zinc-500 dark:text-zinc-400">TOP:</span>
          {LIMIT_OPTIONS.map((n) => (
            <button
              key={n}
              type="button"
              onClick={() => setLimit(n)}
              className={`rounded-full px-3 py-1 text-xs font-medium transition ${
                limit === n
                  ? "bg-orange-500 text-white"
                  : "bg-transparent text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800"
              }`}
            >
              {n}
            </button>
          ))}
        </div>
        <span className="ml-auto text-xs text-zinc-500 dark:text-zinc-400">
          지도에 {filtered.length.toLocaleString()}개 표시 · 전체 geocoded {geocoded.length.toLocaleString()}
        </span>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1fr_320px]">
        <KakaoMap markers={markers} level={9} className="h-[70vh] w-full" />
        <aside className="flex max-h-[70vh] flex-col overflow-hidden rounded-2xl border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900">
          <div className="border-b border-zinc-100 px-4 py-3 text-xs font-semibold text-zinc-700 dark:border-zinc-800 dark:text-zinc-300">
            표시 중인 식당
          </div>
          <ul className="flex-1 divide-y divide-zinc-100 overflow-y-auto text-sm dark:divide-zinc-800">
            {filtered.map((r) => (
              <li
                key={r.rank}
                onMouseEnter={() => setHovered(r.rank)}
                onMouseLeave={() => setHovered(null)}
                className={`px-4 py-2.5 transition ${
                  hovered === r.rank
                    ? "bg-orange-50 dark:bg-orange-950/30"
                    : "hover:bg-zinc-50 dark:hover:bg-zinc-800/40"
                }`}
              >
                <a
                  href={`/restaurant/${r.rank}`}
                  className="flex items-start gap-2"
                >
                  <span className="shrink-0 rounded-full bg-zinc-100 px-1.5 py-0.5 text-[11px] font-semibold text-zinc-600 tabular-nums dark:bg-zinc-800 dark:text-zinc-400">
                    {r.rank}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="truncate font-medium text-zinc-900 dark:text-zinc-100">
                      {r.name}
                    </div>
                    <div className="flex items-center gap-2 text-[11px] text-zinc-500 dark:text-zinc-400">
                      <span>{r.region}</span>
                      <span className="text-orange-600 dark:text-orange-400">
                        {r.visits.toLocaleString()}회
                      </span>
                      <span>{formatWon(r.totalAmount)}</span>
                    </div>
                  </div>
                </a>
              </li>
            ))}
          </ul>
        </aside>
      </div>
    </div>
  );
}
