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
    <div className="flex flex-1 flex-col bg-base text-ink">
      <SiteHeader />
      <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-10">
        <div className="mb-8">
          <div className="text-[10px] font-medium uppercase tracking-[0.18em] text-accent">
            Map
          </div>
          <h1 className="mt-2 text-4xl font-extrabold tracking-tight text-ink sm:text-5xl">
            지도에서 보기
          </h1>
          <p className="mt-3 max-w-prose text-sm text-mute">
            26개 자치구 공무원 맛집을 지도 위에서 탐색하세요.
          </p>
        </div>
        <MapExplorer restaurants={restaurants} />
      </main>
      <SiteFooter />
    </div>
  );
}
