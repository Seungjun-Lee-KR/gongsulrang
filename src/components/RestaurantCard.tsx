import Link from "next/link";
import type { Restaurant } from "@/types/restaurant";
import { formatDistance } from "@/lib/distance";

type Props = {
  restaurant: Restaurant;
  distanceMeters?: number;
  /** 카드 그리드의 최댓값. heat bar 비율 계산용 */
  maxVisits?: number;
};

const rankBadgeClass = (rank: number) => {
  if (rank === 1)
    return "bg-accent text-[#1a0f08] border-accent";
  if (rank === 2 || rank === 3)
    return "bg-accent2 text-[#14210a] border-accent2";
  return "bg-base/80 text-ink border-line2 backdrop-blur";
};

function nameInitial(raw: string): string {
  const stripped = raw.replace(/^[(（][^)）]+[)）]\s*/, "").trim();
  return (stripped[0] || raw.trim()[0] || "?").toUpperCase();
}

function nameHue(name: string): number {
  let h = 7;
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) | 0;
  return Math.abs(h) % 360;
}

export default function RestaurantCard({
  restaurant,
  distanceMeters,
  maxVisits,
}: Props) {
  const {
    rank,
    name,
    region,
    visits,
    rating,
    deptCount,
    guDong,
    photos,
  } = restaurant;
  const photo = photos?.[0];
  const locationLabel = guDong || region;
  const heat = maxVisits ? Math.max(6, Math.min(100, (visits / maxVisits) * 100)) : null;

  return (
    <Link
      href={`/restaurant/${rank}`}
      className="group relative flex flex-col overflow-hidden rounded-2xl border border-line bg-elev transition hover:-translate-y-1 hover:border-accent focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
    >
      {/* 사진 / 플레이스홀더 영역 */}
      <div className="relative aspect-[4/3] overflow-hidden bg-elev2">
        {photo ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={photo}
            alt={name}
            loading="lazy"
            className="h-full w-full object-cover transition duration-500 group-hover:scale-105"
          />
        ) : (
          <PlaceholderArt name={name} />
        )}
        {/* 하단 그라데이션 */}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-x-0 bottom-0 h-32 bg-gradient-to-t from-black/85 via-black/40 to-transparent"
        />
        {/* 랭크 배지 */}
        <span
          className={`absolute left-3 top-3 rounded-md border px-2 py-1 font-mono text-xs font-semibold tabular ${rankBadgeClass(rank)}`}
        >
          #{rank}
        </span>
        {/* 거리 배지 */}
        {distanceMeters !== undefined && (
          <span className="absolute right-3 top-3 rounded-md border border-line2 bg-base/85 px-2 py-1 font-mono text-[11px] font-medium text-accent backdrop-blur">
            📍 {formatDistance(distanceMeters)}
          </span>
        )}
        {/* 식당명 + 위치 */}
        <div className="absolute inset-x-0 bottom-0 p-4">
          {locationLabel && (
            <div className="mb-1 text-[11px] font-medium uppercase tracking-[0.1em] text-white/70">
              📍 {locationLabel}
            </div>
          )}
          <h3 className="text-lg font-bold leading-tight tracking-tight text-white">
            {name}
          </h3>
        </div>
      </div>

      {/* 통계 그리드 */}
      <div className="grid grid-cols-3 gap-3 px-4 pt-4">
        <Stat label="방문" value={visits.toLocaleString()} highlight />
        <Stat label="부서" value={deptCount.toString()} />
        <Stat
          label="평점"
          value={rating !== undefined ? `★ ${rating.toFixed(1)}` : "—"}
        />
      </div>

      {/* heat bar */}
      <div className="mt-3 flex items-center gap-2 px-4 pb-4">
        <span className="font-mono text-[10px] tabular text-mute">
          {heat !== null ? `${Math.round(heat)}%` : "—"}
        </span>
        <div className="heat-track flex-1">
          <div
            className="heat-fill"
            style={{ width: heat !== null ? `${heat}%` : "0%" }}
          />
        </div>
      </div>
    </Link>
  );
}

function Stat({
  label,
  value,
  highlight = false,
}: {
  label: string;
  value: string;
  highlight?: boolean;
}) {
  return (
    <div className="flex flex-col gap-0.5">
      <span
        className={`font-mono tabular ${
          highlight
            ? "text-accent text-lg font-bold"
            : "text-ink text-base font-semibold"
        }`}
      >
        {value}
      </span>
      <span className="text-[10px] uppercase tracking-[0.1em] text-mute">
        {label}
      </span>
    </div>
  );
}

function PlaceholderArt({ name }: { name: string }) {
  const hue = nameHue(name);
  const initial = nameInitial(name);
  return (
    <div
      className="relative flex h-full w-full items-center justify-center text-white"
      style={{
        background: `linear-gradient(135deg, hsl(${hue} 62% 38%), hsl(${(hue + 35) % 360} 70% 28%))`,
      }}
    >
      <div
        aria-hidden
        className="pointer-events-none absolute -right-8 -top-8 h-32 w-32 rounded-full bg-white/10 blur-2xl"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute -bottom-10 -left-8 h-40 w-40 rounded-full bg-black/25 blur-2xl"
      />
      <span className="text-6xl font-extrabold tracking-tight drop-shadow-md">
        {initial}
      </span>
    </div>
  );
}
