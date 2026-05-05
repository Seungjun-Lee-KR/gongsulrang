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
  const maxVisits = list[0]?.visits ?? 1;

  return (
    <div className="flex flex-1 flex-col bg-base text-ink">
      <SiteHeader />
      <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-10">
        <div className="mb-8">
          <Link
            href="/region"
            className="text-xs text-mute hover:text-ink"
          >
            ← 전체 구 보기
          </Link>
          <div className="mt-3 text-[10px] font-medium uppercase tracking-[0.18em] text-accent">
            District
          </div>
          <h1 className="mt-1 text-4xl font-extrabold tracking-tight text-ink sm:text-5xl">
            {region}
          </h1>
          <div className="mt-4 flex flex-wrap items-center gap-2 text-sm">
            <span className="rounded-full border border-line2 bg-elev px-3 py-1 font-mono text-xs tabular text-mute">
              식당 {list.length.toLocaleString()}개
            </span>
            <span className="rounded-full bg-accent/15 px-3 py-1 font-mono text-xs font-semibold tabular text-accent">
              총 {totalVisits.toLocaleString()}회 이용
            </span>
            <span className="rounded-full border border-line2 bg-elev px-3 py-1 font-mono text-xs tabular text-mute">
              총 {formatWon(totalAmount)}
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {list.map((r) => (
            <RestaurantCard key={r.rank} restaurant={r} maxVisits={maxVisits} />
          ))}
        </div>
      </main>
      <SiteFooter />
    </div>
  );
}
