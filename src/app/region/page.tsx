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
    <div className="flex flex-1 flex-col bg-base text-ink">
      <SiteHeader />
      <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-12">
        <div className="mb-10">
          <div className="text-[10px] font-medium uppercase tracking-[0.18em] text-accent">
            District
          </div>
          <h1 className="mt-2 text-4xl font-extrabold tracking-tight text-ink sm:text-5xl">
            구별 공슐랭
          </h1>
          <p className="mt-3 max-w-prose text-sm text-mute">
            서울 22개 자치구(+본청) 맛집 랭킹. 클릭해서 해당 구의 TOP 식당을
            확인하세요.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {summaries.map((s) => (
            <Link
              key={s.region}
              href={`/region/${encodeURIComponent(s.region)}`}
              className="group flex flex-col gap-3 rounded-2xl border border-line bg-elev p-5 transition hover:-translate-y-1 hover:border-accent"
            >
              <div className="flex items-baseline justify-between gap-2">
                <h2 className="text-xl font-bold tracking-tight text-ink">
                  {s.region}
                </h2>
                <span className="font-mono text-xs tabular text-mute">
                  {s.restaurantCount}개 식당
                </span>
              </div>
              <div className="flex items-center gap-2.5 text-sm">
                <span className="rounded-full bg-accent/15 px-2.5 py-1 font-mono text-xs font-semibold tabular text-accent">
                  {s.totalVisits.toLocaleString()}회
                </span>
                <span className="text-mute">
                  총 {formatWon(s.totalAmount)}
                </span>
              </div>
              <div className="mt-1 border-t border-line pt-3 text-xs text-mute">
                <span className="text-accent2">🥇</span> {s.topRestaurant.name}
                <span className="ml-1 font-mono text-mute/70 tabular">
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
