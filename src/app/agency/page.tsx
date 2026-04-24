import Link from "next/link";
import SiteHeader from "@/components/SiteHeader";
import SiteFooter from "@/components/SiteFooter";
import { getAgencySummaries, slugifyAgency } from "@/lib/aggregations";
import { formatWon } from "@/lib/format";

export const metadata = {
  title: "기관별 공슐랭 · 공슐랭",
  description: "집행 부서(기관)별 공무원 맛집 랭킹",
};

export default function AgencyIndex() {
  const summaries = getAgencySummaries();

  return (
    <div className="flex flex-1 flex-col bg-zinc-50 dark:bg-zinc-950">
      <SiteHeader />
      <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-10">
        <div className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
            기관별 공슐랭
          </h1>
          <p className="mt-2 text-sm text-zinc-500 dark:text-zinc-400">
            각 식당의 주요 이용 부서 기준. "이 부서는 여기를 자주 간다" 관점.
          </p>
        </div>

        <div className="overflow-hidden rounded-2xl border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900">
          <table className="w-full text-sm">
            <thead className="border-b border-zinc-100 bg-zinc-50 text-xs text-zinc-500 dark:border-zinc-800 dark:bg-zinc-950 dark:text-zinc-400">
              <tr>
                <th className="px-4 py-3 text-left">#</th>
                <th className="px-4 py-3 text-left">주요 이용 기관</th>
                <th className="px-4 py-3 text-right">식당</th>
                <th className="px-4 py-3 text-right">총 이용</th>
                <th className="px-4 py-3 text-right">총 금액</th>
                <th className="px-4 py-3 text-left">대표 맛집</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
              {summaries.map((s, i) => (
                <tr
                  key={s.agency}
                  className="group transition hover:bg-zinc-50 dark:hover:bg-zinc-800/40"
                >
                  <td className="px-4 py-3 text-zinc-500 tabular-nums">{i + 1}</td>
                  <td className="px-4 py-3">
                    <Link
                      href={`/agency/${slugifyAgency(s.agency)}`}
                      className="font-semibold text-zinc-900 hover:text-orange-600 dark:text-zinc-50 dark:hover:text-orange-400"
                    >
                      {s.agency}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums text-zinc-700 dark:text-zinc-300">
                    {s.restaurantCount}
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums font-semibold text-orange-600 dark:text-orange-400">
                    {s.totalVisits.toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums text-zinc-600 dark:text-zinc-400">
                    {formatWon(s.totalAmount)}
                  </td>
                  <td className="px-4 py-3 text-zinc-600 dark:text-zinc-400">
                    🥇 {s.topRestaurant.name}
                    <span className="ml-1 text-xs text-zinc-400">
                      ({s.topRestaurant.region})
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </main>
      <SiteFooter />
    </div>
  );
}
