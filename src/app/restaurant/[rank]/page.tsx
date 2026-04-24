import Link from "next/link";
import { notFound } from "next/navigation";
import { restaurants } from "@/data/restaurants";
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

  const photos = r.photos ?? [];
  const photoSlots = [0, 1, 2];

  return (
    <div className="flex flex-1 flex-col bg-zinc-50 dark:bg-zinc-950">
      <header className="border-b border-zinc-200 bg-white/80 backdrop-blur dark:border-zinc-800 dark:bg-zinc-900/80">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
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

      <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-6">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="flex items-center gap-2 text-sm text-zinc-500 dark:text-zinc-400">
              <span className="rounded-full bg-amber-400 px-3 py-1 font-bold text-amber-950">
                {r.rank}위
              </span>
              <span>{r.region}</span>
            </div>
            <h1 className="mt-2 text-3xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
              {r.name}
            </h1>
            {r.topAgency && (
              <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">
                주요 이용 기관:{" "}
                <span className="font-medium">서울시(본청) {r.topAgency}</span>
              </p>
            )}
          </div>
          <div className="flex shrink-0 items-start gap-5">
            <div className="flex flex-col items-end">
              <span className="text-2xl font-bold leading-none text-orange-600 tabular-nums dark:text-orange-400">
                {r.visits.toLocaleString()}회
              </span>
              <span className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">
                공무원 방문 · {r.deptCount}개 부서
              </span>
            </div>
            {r.naverVisitorReviewCount !== undefined && (
              <div className="flex flex-col items-end border-l border-zinc-200 pl-5 dark:border-zinc-800">
                <span className="text-2xl font-bold leading-none text-[#03c75a] tabular-nums">
                  {r.naverVisitorReviewCount.toLocaleString()}
                </span>
                <span className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">
                  네이버 방문자 리뷰수
                </span>
              </div>
            )}
            {r.rating !== undefined && (
              <div className="flex flex-col items-end border-l border-zinc-200 pl-5 dark:border-zinc-800">
                <span className="text-2xl font-bold leading-none text-orange-600 dark:text-orange-400">
                  ★ {r.rating.toFixed(1)}
                </span>
                {r.ratingCount !== undefined && (
                  <span className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">
                    Google 리뷰 {r.ratingCount.toLocaleString()}개
                  </span>
                )}
              </div>
            )}
          </div>
        </div>

        <section className="mt-5 grid grid-cols-3 gap-3">
          {photoSlots.map((i) => {
            const src = photos[i];
            return (
              <div
                key={i}
                className="relative aspect-[4/3] overflow-hidden rounded-xl border border-zinc-200 bg-zinc-100 dark:border-zinc-800 dark:bg-zinc-900"
              >
                {src ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={src}
                    alt={`${r.name} 사진 ${i + 1}`}
                    className="h-full w-full object-cover"
                    loading="lazy"
                  />
                ) : (
                  <div className="flex h-full w-full items-center justify-center text-xs text-zinc-400 dark:text-zinc-600">
                    사진 없음
                  </div>
                )}
              </div>
            );
          })}
        </section>

        <section className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-3">
          <div className="overflow-hidden rounded-xl border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900">
            {r.lat !== undefined && r.lng !== undefined ? (
              <KakaoMap
                markers={[
                  { id: r.rank, lat: r.lat, lng: r.lng, label: r.name },
                ]}
                level={4}
                className="h-56 w-full"
              />
            ) : (
              <div className="flex h-56 w-full items-center justify-center text-sm text-zinc-400 dark:text-zinc-600">
                위치 정보 없음
              </div>
            )}
          </div>

          <div className="flex h-56 flex-col divide-y divide-zinc-100 overflow-hidden rounded-xl border border-zinc-200 bg-white dark:divide-zinc-800 dark:border-zinc-800 dark:bg-zinc-900">
            {r.formattedAddress || r.googleMapsUri ? (
              <a
                href={r.googleMapsUri ?? "#"}
                target="_blank"
                rel="noopener noreferrer"
                className="group flex items-start gap-2.5 px-3 py-2.5 transition hover:bg-zinc-50 dark:hover:bg-zinc-800/40"
              >
                <IconPin className="mt-0.5 h-4 w-4 shrink-0 text-zinc-400 group-hover:text-orange-500 dark:text-zinc-500" />
                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm font-medium text-zinc-900 dark:text-zinc-100">
                    {r.formattedAddress ?? "지도에서 보기"}
                  </div>
                  {r.googleMapsUri && (
                    <div className="text-[11px] text-zinc-400 group-hover:text-orange-500 dark:text-zinc-500">
                      Google 지도에서 열기 ↗
                    </div>
                  )}
                </div>
              </a>
            ) : (
              <InfoEmpty icon={<IconPin className="h-4 w-4" />} text="주소 정보 없음" />
            )}

            {r.phone ? (
              <a
                href={`tel:${r.phone.replace(/\s+/g, "")}`}
                className="group flex items-center gap-2.5 px-3 py-2.5 transition hover:bg-zinc-50 dark:hover:bg-zinc-800/40"
              >
                <IconPhone className="h-4 w-4 shrink-0 text-zinc-400 group-hover:text-orange-500 dark:text-zinc-500" />
                <span className="truncate text-sm font-medium text-zinc-900 tabular-nums dark:text-zinc-100">
                  {r.phone}
                </span>
              </a>
            ) : (
              <InfoEmpty icon={<IconPhone className="h-4 w-4" />} text="전화번호 없음" />
            )}

            <div className="flex min-h-0 flex-1 items-start gap-2.5 px-3 py-2.5">
              <IconClock className="mt-0.5 h-4 w-4 shrink-0 text-zinc-400 dark:text-zinc-500" />
              <div className="min-w-0 flex-1 overflow-y-auto pr-1">
                {r.hours && r.hours.length > 0 ? (
                  <ul className="space-y-0.5">
                    {r.hours.map((h, i) => {
                      const m = h.match(/^([^:]+):\s*(.+)$/);
                      const day = m?.[1] ?? "";
                      const time = m?.[2] ?? h;
                      return (
                        <li
                          key={i}
                          className="flex gap-2 text-[11px] leading-5"
                        >
                          <span className="w-10 shrink-0 text-zinc-400 dark:text-zinc-500">
                            {day}
                          </span>
                          <span className="text-zinc-700 dark:text-zinc-300">
                            {time}
                          </span>
                        </li>
                      );
                    })}
                  </ul>
                ) : (
                  <span className="text-xs text-zinc-400 dark:text-zinc-600">
                    영업시간 정보 없음
                  </span>
                )}
              </div>
            </div>
          </div>

          <div className="flex h-56 flex-col rounded-xl border border-zinc-200 bg-white p-3 dark:border-zinc-800 dark:bg-zinc-900">
            <div className="mb-2 text-xs font-semibold text-zinc-700 dark:text-zinc-300">
              업무추진비 집행현황
            </div>
            <div className="grid flex-1 grid-cols-2 gap-2">
              <MiniStat
                label="이용횟수"
                value={`${r.visits.toLocaleString()}회`}
                highlight
              />
              <MiniStat label="총 금액" value={formatWon(r.totalAmount)} />
              <MiniStat label="평균 1회" value={formatWon(r.avgAmount)} />
              <MiniStat label="이용 부서" value={`${r.deptCount}개`} />
            </div>
          </div>
        </section>

        <p className="mt-4 text-xs leading-5 text-zinc-500 dark:text-zinc-500">
          수치는 지방재정365가 공개한 업무추진비 집행내역을 가맹점별로 집계한
          결과입니다. 평점·사진·영업시간은 Google Places 데이터입니다.
        </p>
      </main>

      <footer className="border-t border-zinc-200 bg-white py-5 text-center text-xs text-zinc-500 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-400">
        © 2026 공슐랭
      </footer>
    </div>
  );
}

function InfoEmpty({ icon, text }: { icon: React.ReactNode; text: string }) {
  return (
    <div className="flex items-center gap-2.5 px-3 py-2.5 text-zinc-400 dark:text-zinc-600">
      <span className="shrink-0">{icon}</span>
      <span className="text-sm">{text}</span>
    </div>
  );
}

function IconPin({ className = "" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden
    >
      <path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0z" />
      <circle cx="12" cy="10" r="3" />
    </svg>
  );
}

function IconPhone({ className = "" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden
    >
      <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6A19.79 19.79 0 0 1 2.12 4.18 2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.13.96.36 1.9.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.91.34 1.85.57 2.81.7A2 2 0 0 1 22 16.92z" />
    </svg>
  );
}

function IconClock({ className = "" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden
    >
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </svg>
  );
}

function MiniStat({
  label,
  value,
  highlight = false,
}: {
  label: string;
  value: string;
  highlight?: boolean;
}) {
  return (
    <div className="flex flex-col justify-center rounded-lg bg-zinc-50 p-2 dark:bg-zinc-800/60">
      <div className="text-[10px] text-zinc-500 dark:text-zinc-400">
        {label}
      </div>
      <div
        className={`mt-0.5 text-base font-bold leading-tight ${
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
