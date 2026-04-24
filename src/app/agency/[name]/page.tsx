import Link from "next/link";
import { notFound } from "next/navigation";
import SiteHeader from "@/components/SiteHeader";
import SiteFooter from "@/components/SiteFooter";
import RestaurantCard from "@/components/RestaurantCard";
import {
  getAgencySummaries,
  getRestaurantsByAgency,
  unslugifyAgency,
  slugifyAgency,
} from "@/lib/aggregations";
import { formatWon } from "@/lib/format";

export function generateStaticParams() {
  return getAgencySummaries().map((s) => ({ name: slugifyAgency(s.agency) }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ name: string }>;
}) {
  const { name } = await params;
  const agency = unslugifyAgency(name);
  return {
    title: `${agency} · 공슐랭 기관별`,
    description: `${agency}이(가) 자주 가는 식당 랭킹`,
  };
}

export default async function AgencyDetail({
  params,
}: {
  params: Promise<{ name: string }>;
}) {
  const { name } = await params;
  const agency = unslugifyAgency(name);
  const list = getRestaurantsByAgency(agency);
  if (list.length === 0) notFound();

  const totalVisits = list.reduce((s, r) => s + r.visits, 0);
  const totalAmount = list.reduce((s, r) => s + r.totalAmount, 0);

  return (
    <div className="flex flex-1 flex-col bg-zinc-50 dark:bg-zinc-950">
      <SiteHeader />
      <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-10">
        <div className="mb-8">
          <Link
            href="/agency"
            className="text-xs text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-50"
          >
            ← 전체 기관 보기
          </Link>
          <h1 className="mt-2 text-3xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
            {agency}
          </h1>
          <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
            이 부서가 주요 이용 기관으로 등록된 식당
          </p>
          <div className="mt-3 flex flex-wrap items-center gap-3 text-sm text-zinc-600 dark:text-zinc-400">
            <span className="rounded-full bg-zinc-100 px-3 py-1 dark:bg-zinc-800">
              식당 {list.length.toLocaleString()}개
            </span>
            <span className="rounded-full bg-orange-100 px-3 py-1 font-semibold text-orange-700 dark:bg-orange-900/40 dark:text-orange-300">
              총 {totalVisits.toLocaleString()}회 이용
            </span>
            <span className="rounded-full bg-zinc-100 px-3 py-1 dark:bg-zinc-800">
              총 {formatWon(totalAmount)}
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {list.map((r) => (
            <RestaurantCard key={r.rank} restaurant={r} />
          ))}
        </div>
      </main>
      <SiteFooter />
    </div>
  );
}
