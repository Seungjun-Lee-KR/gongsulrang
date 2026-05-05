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
          <span className="text-mute">지역:</span>
          <select
            value={region}
            onChange={(e) => setRegion(e.target.value)}
            className="rounded-full border border-line2 bg-elev px-3 py-1.5 text-sm text-ink focus:border-accent focus:outline-none"
          >
            {regions.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-mute">TOP:</span>
          {LIMIT_OPTIONS.map((n) => (
            <button
              key={n}
              type="button"
              onClick={() => setLimit(n)}
              className={`rounded-full px-3 py-1 text-xs font-medium transition border ${
                limit === n
                  ? "bg-accent text-[#1a0f08] border-accent"
                  : "bg-transparent text-mute border-line2 hover:text-ink hover:border-accent"
              }`}
            >
              {n}
            </button>
          ))}
        </div>
        <span className="ml-auto font-mono text-xs tabular text-mute">
          지도에 {filtered.length.toLocaleString()}개 표시 · 전체 geocoded {geocoded.length.toLocaleString()}
        </span>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1fr_320px]">
        <div className="overflow-hidden rounded-2xl border border-line">
          <KakaoMap markers={markers} level={9} className="h-[70vh] w-full" />
        </div>
        <aside className="flex max-h-[70vh] flex-col overflow-hidden rounded-2xl border border-line bg-elev">
          <div className="border-b border-line px-4 py-3 text-[10px] font-semibold uppercase tracking-[0.12em] text-mute">
            표시 중인 식당
          </div>
          <ul className="flex-1 divide-y divide-line overflow-y-auto text-sm">
            {filtered.map((r) => (
              <li
                key={r.rank}
                onMouseEnter={() => setHovered(r.rank)}
                onMouseLeave={() => setHovered(null)}
                className={`px-4 py-2.5 transition ${
                  hovered === r.rank ? "bg-accent/10" : "hover:bg-elev2"
                }`}
              >
                <a
                  href={`/restaurant/${r.rank}`}
                  className="flex items-start gap-2"
                >
                  <span className="shrink-0 rounded-md bg-elev2 px-1.5 py-0.5 font-mono text-[11px] font-semibold tabular text-mute">
                    {r.rank}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="truncate font-medium text-ink">
                      {r.name}
                    </div>
                    <div className="flex items-center gap-2 font-mono text-[11px] tabular text-mute">
                      <span>{r.region}</span>
                      <span className="text-accent">
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
