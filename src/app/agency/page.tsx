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
    <div className="flex flex-1 flex-col bg-base text-ink">
      <SiteHeader />
      <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-12">
        <div className="mb-10">
          <div className="text-[10px] font-medium uppercase tracking-[0.18em] text-accent">
            Agency
          </div>
          <h1 className="mt-2 text-4xl font-extrabold tracking-tight text-ink sm:text-5xl">
            기관별 공슐랭
          </h1>
          <p className="mt-3 max-w-prose text-sm text-mute">
            각 식당의 주요 이용 부서 기준. "이 부서는 여기를 자주 간다" 관점.
          </p>
        </div>

        <div className="overflow-x-auto rounded-2xl border border-line bg-elev">
          <table className="w-full min-w-[720px] text-sm">
            <thead className="border-b border-line bg-elev2 text-[10px] uppercase tracking-[0.12em] text-mute">
              <tr>
                <th className="px-4 py-3 text-left font-medium">#</th>
                <th className="px-4 py-3 text-left font-medium">주요 이용 기관</th>
                <th className="px-4 py-3 text-right font-medium">식당</th>
                <th className="px-4 py-3 text-right font-medium">총 이용</th>
                <th className="px-4 py-3 text-right font-medium">총 금액</th>
                <th className="px-4 py-3 text-left font-medium">대표 맛집</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {summaries.map((s, i) => (
                <tr
                  key={s.agency}
                  className="group transition hover:bg-elev2"
                >
                  <td className="px-4 py-3 font-mono text-xs tabular text-mute">
                    {i + 1}
                  </td>
                  <td className="px-4 py-3">
                    <Link
                      href={`/agency/${slugifyAgency(s.agency)}`}
                      className="font-semibold text-ink hover:text-accent"
                    >
                      {s.agency}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-right font-mono tabular text-mute">
                    {s.restaurantCount}
                  </td>
                  <td className="px-4 py-3 text-right font-mono font-semibold tabular text-accent">
                    {s.totalVisits.toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-right font-mono tabular text-mute">
                    {formatWon(s.totalAmount)}
                  </td>
                  <td className="px-4 py-3 text-mute">
                    <span className="text-accent2">🥇</span>{" "}
                    {s.topRestaurant.name}
                    <span className="ml-1 text-xs text-mute/70">
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
