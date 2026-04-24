import SiteHeader from "@/components/SiteHeader";
import SiteFooter from "@/components/SiteFooter";
import MapExplorer from "@/components/MapExplorer";
import { restaurants } from "@/data/restaurants";

export const metadata = {
  title: "지도 · 공슐랭",
  description: "지도 위에서 공무원 맛집 탐색",
};

export default function MapPage() {
  return (
    <div className="flex flex-1 flex-col bg-zinc-50 dark:bg-zinc-950">
      <SiteHeader />
      <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-8">
        <div className="mb-6">
          <h1 className="text-3xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
            지도에서 보기
          </h1>
          <p className="mt-2 text-sm text-zinc-500 dark:text-zinc-400">
            22개 자치구 공무원 맛집을 지도 위에서 탐색하세요.
          </p>
        </div>
        <MapExplorer restaurants={restaurants} />
      </main>
      <SiteFooter />
    </div>
  );
}
