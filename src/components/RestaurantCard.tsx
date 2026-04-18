import Link from "next/link";
import type { Restaurant } from "@/types/restaurant";
import { formatWon } from "@/lib/format";
import { formatDistance } from "@/lib/distance";

type Props = {
  restaurant: Restaurant;
  distanceMeters?: number;
};

const rankBadgeClass = (rank: number) => {
  if (rank === 1) return "bg-amber-400 text-amber-950";
  if (rank === 2) return "bg-zinc-300 text-zinc-800";
  if (rank === 3) return "bg-orange-300 text-orange-950";
  return "bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300";
};

export default function RestaurantCard({ restaurant, distanceMeters }: Props) {
  const { rank, name, region, visits, totalAmount, avgAmount, deptCount, topAgency } =
    restaurant;

  return (
    <Link
      href={`/restaurant/${rank}`}
      className="group relative flex flex-col gap-4 rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm transition hover:-translate-y-1 hover:shadow-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-500 dark:border-zinc-800 dark:bg-zinc-900"
    >
      <div className="flex items-start justify-between gap-3">
        <span
          className={`inline-flex h-10 w-10 items-center justify-center rounded-full text-sm font-bold ${rankBadgeClass(
            rank,
          )}`}
        >
          {rank}
        </span>
        <div className="flex items-center gap-1.5">
          {distanceMeters !== undefined && (
            <span className="rounded-full bg-orange-100 px-2.5 py-1 text-xs font-semibold text-orange-700 dark:bg-orange-900/40 dark:text-orange-300">
              📍 {formatDistance(distanceMeters)}
            </span>
          )}
          <span className="rounded-full bg-zinc-100 px-2.5 py-1 text-xs font-medium text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300">
            {region}
          </span>
        </div>
      </div>

      <div>
        <h3 className="text-lg font-bold leading-tight text-zinc-900 dark:text-zinc-50">
          {name}
        </h3>
        {topAgency && (
          <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">
            주요 이용: {topAgency}
          </p>
        )}
      </div>

      <div className="grid grid-cols-3 gap-2 border-t border-zinc-100 pt-4 dark:border-zinc-800">
        <Stat label="이용횟수" value={`${visits.toLocaleString()}회`} highlight />
        <Stat label="총 금액" value={formatWon(totalAmount)} />
        <Stat label="부서수" value={`${deptCount}개`} />
      </div>

      <div className="text-xs text-zinc-400 dark:text-zinc-500">
        평균 1회 {formatWon(avgAmount)}
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
      <span className="text-[11px] text-zinc-500 dark:text-zinc-400">{label}</span>
      <span
        className={`text-sm font-semibold ${
          highlight
            ? "text-orange-600 dark:text-orange-400"
            : "text-zinc-800 dark:text-zinc-200"
        }`}
      >
        {value}
      </span>
    </div>
  );
}
