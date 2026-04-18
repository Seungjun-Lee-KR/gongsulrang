import Link from "next/link";
import { notFound } from "next/navigation";
import { restaurants, usingSampleData } from "@/data/restaurants";
import { formatWon } from "@/lib/format";
import KakaoMap from "@/components/KakaoMap";

export function generateStaticParams() {
  return restaurants.map((r) => ({ rank: String(r.rank) }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ rank: string }>;
}) {
  const { rank } = await params;
  const r = restaurants.find((x) => String(x.rank) === rank);
  if (!r) return { title: "공슐랭" };
  return {
    title: `${r.name} · 공슐랭 ${r.rank}위`,
    description: `${r.region} · ${r.visits.toLocaleString()}회 이용 · ${r.deptCount}개 부서`,
  };
}

export default async function Page({
  params,
}: {
  params: Promise<{ rank: string }>;
}) {
  const { rank } = await params;
  const r = restaurants.find((x) => String(x.rank) === rank);
  if (!r) notFound();

  return (
    <div className="flex flex-1 flex-col bg-zinc-50 dark:bg-zinc-950">
      <header className="border-b border-zinc-200 bg-white/80 backdrop-blur dark:border-zinc-800 dark:bg-zinc-900/80">
        <div className="mx-auto flex max-w-4xl items-center justify-between px-6 py-5">
          <Link href="/" className="flex items-center gap-2">
            <span className="text-2xl">🏛️</span>
            <span className="text-lg font-bold text-zinc-900 dark:text-zinc-50">
              공슐랭
            </span>
          </Link>
          <Link
            href="/"
            className="text-sm text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-50"
          >
            ← 랭킹으로
          </Link>
        </div>
      </header>

      <main className="mx-auto w-full max-w-4xl flex-1 px-6 py-12">
        <div className="mb-8 flex items-center gap-3 text-sm text-zinc-500 dark:text-zinc-400">
          <span className="rounded-full bg-amber-400 px-3 py-1 font-bold text-amber-950">
            {r.rank}위
          </span>
          <span>{r.region}</span>
        </div>

        <h1 className="text-4xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
          {r.name}
        </h1>
        {r.topAgency && (
          <p className="mt-3 text-base text-zinc-600 dark:text-zinc-400">
            주요 이용 기관: <span className="font-medium">{r.topAgency}</span>
          </p>
        )}

        <section className="mt-10 grid grid-cols-2 gap-4 sm:grid-cols-4">
          <Stat label="이용횟수" value={`${r.visits.toLocaleString()}회`} highlight />
          <Stat label="총 이용금액" value={formatWon(r.totalAmount)} />
          <Stat label="평균 1회" value={formatWon(r.avgAmount)} />
          <Stat label="이용 부서" value={`${r.deptCount}개`} />
        </section>

        {r.lat !== undefined && r.lng !== undefined && (
          <section className="mt-10">
            <h2 className="mb-3 text-base font-semibold text-zinc-900 dark:text-zinc-50">
              위치
            </h2>
            <KakaoMap
              markers={[
                { id: r.rank, lat: r.lat, lng: r.lng, label: r.name },
              ]}
              level={4}
              className="h-[320px] w-full"
            />
          </section>
        )}

        <section className="mt-10 rounded-2xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-900">
          <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-50">
            데이터 출처
          </h2>
          <p className="mt-2 text-sm leading-6 text-zinc-600 dark:text-zinc-400">
            지방재정365(lofin.mois.go.kr)에서 공개한 업무추진비 집행 내역을
            가맹점(식당)별로 집계한 결과입니다. 본 페이지의 수치는 해당 식당이
            업무추진비 카드 결제 데이터에 등장한 횟수와 금액을 기반으로 합니다.
          </p>
          {usingSampleData && (
            <p className="mt-3 text-xs text-zinc-400 dark:text-zinc-500">
              ※ 현재 표시 중인 데이터는 시연용 샘플입니다.
            </p>
          )}
        </section>
      </main>

      <footer className="border-t border-zinc-200 bg-white py-8 text-center text-sm text-zinc-500 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-400">
        © 2026 공슐랭
      </footer>
    </div>
  );
}

function Stat({
  label,
  value,
  highlight = false,
}: {
  label: string;
  value: string;
  highlight?: boolean;
}) {
  return (
    <div className="rounded-2xl border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-900">
      <div className="text-xs text-zinc-500 dark:text-zinc-400">{label}</div>
      <div
        className={`mt-2 text-2xl font-bold ${
          highlight
            ? "text-orange-600 dark:text-orange-400"
            : "text-zinc-900 dark:text-zinc-50"
        }`}
      >
        {value}
      </div>
    </div>
  );
}
