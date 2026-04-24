import Link from "next/link";
import { notFound } from "next/navigation";
import SiteHeader from "@/components/SiteHeader";
import SiteFooter from "@/components/SiteFooter";
import RestaurantCard from "@/components/RestaurantCard";
import {
  getRegionSummaries,
  getRestaurantsByRegion,
} from "@/lib/aggregations";
import { formatWon } from "@/lib/format";

export function generateStaticParams() {
  return getRegionSummaries().map((s) => ({ gu: s.region }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ gu: string }>;
}) {
  const { gu } = await params;
  const region = decodeURIComponent(gu);
  return {
    title: `${region} 공슐랭 · 공슐랭`,
    description: `${region} 공무원이 자주 가는 맛집 랭킹`,
  };
}

export default async function RegionDetail({
  params,
}: {
  params: Promise<{ gu: string }>;
}) {
  const { gu } = await params;
  const region = decodeURIComponent(gu);
  const list = getRestaurantsByRegion(region);
  if (list.length === 0) notFound();

  const totalVisits = list.reduce((s, r) => s + r.visits, 0);
  const totalAmount = list.reduce((s, r) => s + r.totalAmount, 0);

  return (
    <div className="flex flex-1 flex-col bg-zinc-50 dark:bg-zinc-950">
      <SiteHeader />
      <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-10">
        <div className="mb-8">
          <Link
            href="/region"
            className="text-xs text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-50"
          >
            ← 전체 구 보기
          </Link>
          <h1 className="mt-2 text-3xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
            {region} 공슐랭
          </h1>
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
