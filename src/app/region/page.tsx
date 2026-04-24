import Link from "next/link";
import SiteHeader from "@/components/SiteHeader";
import SiteFooter from "@/components/SiteFooter";
import { getRegionSummaries } from "@/lib/aggregations";
import { formatWon } from "@/lib/format";

export const metadata = {
  title: "구별 공슐랭 · 공슐랭",
  description: "서울 22개 자치구별 공무원 맛집 랭킹",
};

export default function RegionIndex() {
  const summaries = getRegionSummaries();

  return (
    <div className="flex flex-1 flex-col bg-zinc-50 dark:bg-zinc-950">
      <SiteHeader />
      <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-10">
        <div className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
            구별 공슐랭
          </h1>
          <p className="mt-2 text-sm text-zinc-500 dark:text-zinc-400">
            서울 22개 자치구(+본청) 맛집 랭킹. 클릭해서 해당 구의 TOP 식당을 확인하세요.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {summaries.map((s) => (
            <Link
              key={s.region}
              href={`/region/${encodeURIComponent(s.region)}`}
              className="group flex flex-col gap-3 rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm transition hover:-translate-y-1 hover:shadow-lg dark:border-zinc-800 dark:bg-zinc-900"
            >
              <div className="flex items-baseline justify-between gap-2">
                <h2 className="text-xl font-bold text-zinc-900 dark:text-zinc-50">
                  {s.region}
                </h2>
                <span className="text-xs text-zinc-500 dark:text-zinc-400">
                  {s.restaurantCount}개 식당
                </span>
              </div>
              <div className="flex items-center gap-3 text-sm">
                <span className="rounded-full bg-orange-100 px-2.5 py-1 text-xs font-semibold text-orange-700 dark:bg-orange-900/40 dark:text-orange-300">
                  {s.totalVisits.toLocaleString()}회
                </span>
                <span className="text-zinc-500 dark:text-zinc-400">
                  총 {formatWon(s.totalAmount)}
                </span>
              </div>
              <div className="mt-1 border-t border-zinc-100 pt-3 text-xs text-zinc-500 dark:border-zinc-800 dark:text-zinc-400">
                🥇 {s.topRestaurant.name}
                <span className="ml-1 text-zinc-400">
                  ({s.topRestaurant.visits.toLocaleString()}회)
                </span>
              </div>
            </Link>
          ))}
        </div>
      </main>
      <SiteFooter />
    </div>
  );
}
