import Link from "next/link";
import RestaurantList from "@/components/RestaurantList";
import KakaoMap, { type MapMarker } from "@/components/KakaoMap";
import { restaurants, usingSampleData } from "@/data/restaurants";

export default function Home() {
  const markers: MapMarker[] = restaurants
    .filter((r): r is typeof r & { lat: number; lng: number } =>
      r.lat !== undefined && r.lng !== undefined,
    )
    .map((r) => ({
      id: r.rank,
      lat: r.lat,
      lng: r.lng,
      label: `${r.rank}. ${r.name}`,
      href: `/restaurant/${r.rank}`,
    }));

  return (
    <div className="flex flex-1 flex-col bg-zinc-50 dark:bg-zinc-950">
      <header className="border-b border-zinc-200 bg-white/80 backdrop-blur dark:border-zinc-800 dark:bg-zinc-900/80">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
          <div className="flex items-center gap-2">
            <span className="text-2xl">🏛️</span>
            <span className="text-lg font-bold text-zinc-900 dark:text-zinc-50">
              공슐랭
            </span>
          </div>
          <nav className="hidden gap-6 text-sm font-medium text-zinc-600 dark:text-zinc-400 sm:flex">
            <a href="#list" className="hover:text-zinc-900 dark:hover:text-zinc-50">
              맛집
            </a>
            <Link
              href="/about"
              className="hover:text-zinc-900 dark:hover:text-zinc-50"
            >
              소개
            </Link>
          </nav>
        </div>
      </header>

      <main className="flex-1">
        {usingSampleData && (
          <div className="mx-auto max-w-6xl px-6 pt-6">
            <div className="rounded-2xl border border-amber-200 bg-amber-50 px-5 py-3 text-sm text-amber-900 dark:border-amber-900/40 dark:bg-amber-950/30 dark:text-amber-200">
              현재 표시 중인 데이터는 시연용 샘플입니다.{" "}
              <Link
                href="/about"
                className="font-medium underline-offset-2 hover:underline"
              >
                자세히
              </Link>
            </div>
          </div>
        )}

        <section className="mx-auto max-w-6xl px-6 py-16 text-center sm:py-24">
          <h1 className="text-4xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50 sm:text-5xl">
            공무원이 인정한 맛집
          </h1>
          <p className="mx-auto mt-4 max-w-xl text-base text-zinc-600 dark:text-zinc-400 sm:text-lg">
            업무추진비 집행 데이터를 분석해 공무원들이 자주 찾는 진짜 맛집을 골라냈습니다.
          </p>
        </section>

        {markers.length > 0 && (
          <section className="mx-auto max-w-6xl px-6 pb-16">
            <div className="mb-4 flex items-end justify-between">
              <h2 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">
                지도에서 보기
              </h2>
              <span className="text-sm text-zinc-500 dark:text-zinc-400">
                {markers.length}개 맛집
              </span>
            </div>
            <KakaoMap markers={markers} className="h-[420px] w-full" />
          </section>
        )}

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

      <footer className="border-t border-zinc-200 bg-white py-8 text-center text-sm text-zinc-500 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-400">
        © 2026 공슐랭
      </footer>
    </div>
  );
}
