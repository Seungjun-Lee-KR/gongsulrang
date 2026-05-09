import NearbyLeaderboard from "@/components/NearbyLeaderboard";
import RestaurantList from "@/components/RestaurantList";
import SiteHeader from "@/components/SiteHeader";
import SiteFooter from "@/components/SiteFooter";
import { restaurants } from "@/data/restaurants";
import { getAgencySummaries } from "@/lib/aggregations";

function formatBig(n: number): string {
  if (n >= 100_000_000) return `${(n / 100_000_000).toFixed(1)}억`;
  if (n >= 10_000) return `${(n / 10_000).toFixed(0)}만`;
  return n.toLocaleString();
}

export default function Home() {
  const totalSpend = restaurants.reduce((s, r) => s + r.totalAmount, 0);
  const totalVisits = restaurants.reduce((s, r) => s + r.visits, 0);
  const agencyCount = getAgencySummaries().length;

  return (
    <div className="flex flex-1 flex-col bg-base text-ink">
      <SiteHeader />

      <main className="flex-1">
        {/* Hero */}
        <section className="relative overflow-hidden border-b border-line">
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0"
            style={{
              background:
                "radial-gradient(800px 380px at 25% 0%, rgba(255,106,61,0.10), transparent 70%)",
            }}
          />
          <div className="relative mx-auto max-w-6xl px-6 pb-20 pt-20">
            <div className="inline-flex items-center gap-2 rounded-full border border-line2 bg-elev px-3.5 py-1.5 text-xs text-mute">
              <span className="live-dot block h-1.5 w-1.5 rounded-full bg-accent2" />
              <span>
                26개 자치구 · {restaurants.length.toLocaleString()}개 식당 ·
                매주 갱신
              </span>
            </div>

            <h1 className="mt-6 break-keep text-[2.6rem] font-extrabold tracking-tight leading-[1.05] sm:text-7xl sm:leading-[1.02]">
              서울시 법카사용 데이터로 찾은
              <br />
              <span className="text-gradient-accent">서울 맛집 탐방</span>
            </h1>
            <p className="mt-5 max-w-[58ch] text-base text-mute sm:text-lg">
              서울시청·25개 구청 업무추진비 80만 건에서 찾아낸 식당 {restaurants.length.toLocaleString()}곳
            </p>

            <div className="mt-10 grid grid-cols-2 gap-3 sm:grid-cols-4">
              <HeroStat label="식당 개수" value={restaurants.length.toLocaleString()} />
              <HeroStat label="방문 횟수" value={totalVisits.toLocaleString()} />
              <HeroStat label="결제 금액" value={`${formatBig(totalSpend)}원`} />
              <HeroStat label="방문 부서의 수" value={agencyCount.toLocaleString()} />
            </div>
          </div>
        </section>

        <NearbyLeaderboard restaurants={restaurants} />

        <section
          id="list"
          className="mx-auto max-w-6xl px-6 pb-24 pt-4"
        >
          <div className="mb-8 flex items-end justify-between">
            <h2 className="text-2xl font-bold tracking-tight text-ink sm:text-3xl">
              방문횟수 기준 TOP {restaurants.length.toLocaleString()}
            </h2>
          </div>
          <RestaurantList restaurants={restaurants} />
        </section>
      </main>

      <SiteFooter />
    </div>
  );
}

function HeroStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-line bg-elev px-4 py-4">
      <div className="text-[10px] font-medium uppercase tracking-[0.12em] text-mute">
        {label}
      </div>
      <div className="mt-1.5 font-mono text-2xl font-bold tabular text-ink">
        {value}
      </div>
    </div>
  );
}
