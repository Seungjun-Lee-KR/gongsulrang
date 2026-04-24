import NearbyLeaderboard from "@/components/NearbyLeaderboard";
import RestaurantList from "@/components/RestaurantList";
import SiteHeader from "@/components/SiteHeader";
import SiteFooter from "@/components/SiteFooter";
import { restaurants } from "@/data/restaurants";

export default function Home() {
  return (
    <div className="flex flex-1 flex-col bg-zinc-50 dark:bg-zinc-950">
      <SiteHeader />

      <main className="flex-1">
        <NearbyLeaderboard restaurants={restaurants} />

        <section id="list" className="mx-auto max-w-6xl px-6 pb-24">
          <div className="mb-8 flex items-end justify-between">
            <h2 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">
              공슐랭 랭킹
            </h2>
            <span className="text-sm text-zinc-500 dark:text-zinc-400">
              이용횟수 기준 TOP {restaurants.length}
            </span>
          </div>
          <RestaurantList restaurants={restaurants} />
        </section>
      </main>

      <SiteFooter />
    </div>
  );
}
