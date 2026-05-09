import Link from "next/link";
import { notFound } from "next/navigation";
import { restaurants } from "@/data/restaurants";
import { formatWon } from "@/lib/format";
import KakaoMap from "@/components/KakaoMap";
import SiteHeader from "@/components/SiteHeader";
import SiteFooter from "@/components/SiteFooter";
import CommentSection from "@/components/CommentSection";

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

  const jsonLd: Record<string, unknown> = {
    "@context": "https://schema.org",
    "@type": "Restaurant",
    name: r.name,
    url: `https://gongsulrang.vercel.app/restaurant/${r.rank}`,
  };
  if (r.formattedAddress || r.guDong || r.region) {
    jsonLd.address = {
      "@type": "PostalAddress",
      addressCountry: "KR",
      addressRegion: "서울특별시",
      addressLocality: r.guDong || r.region || undefined,
      streetAddress: r.formattedAddress || r.address || undefined,
    };
  }
  if (r.lat !== undefined && r.lng !== undefined) {
    jsonLd.geo = {
      "@type": "GeoCoordinates",
      latitude: r.lat,
      longitude: r.lng,
    };
  }
  if (r.phone) jsonLd.telephone = r.phone;
  if (r.rating !== undefined) {
    jsonLd.aggregateRating = {
      "@type": "AggregateRating",
      ratingValue: r.rating,
      ratingCount: r.ratingCount ?? undefined,
      bestRating: 5,
      worstRating: 1,
    };
  }
  if (r.hours && r.hours.length > 0) {
    jsonLd.openingHours = r.hours;
  }

  return (
    <div className="flex flex-1 flex-col bg-base text-ink">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <SiteHeader />

      <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-8">
        <Link href="/" className="text-xs text-mute hover:text-ink">
          ← 랭킹으로
        </Link>
        <div className="mt-4 flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
          <div className="min-w-0">
            <div className="flex items-center gap-2 text-sm">
              <span className="rounded-md border border-accent bg-accent px-2 py-1 font-mono text-xs font-bold tabular text-[#1a0f08]">
                #{r.rank}
              </span>
              <span className="text-mute">{r.region}</span>
            </div>
            <h1 className="mt-3 break-keep text-3xl font-extrabold tracking-tight text-ink sm:text-5xl">
              {r.name}
            </h1>
            {r.topAgency && (
              <p className="mt-2 break-keep text-sm text-mute">
                주요 이용 기관:{" "}
                <span className="font-medium text-ink">{r.topAgency}</span>
              </p>
            )}
          </div>
          <div className="flex items-start gap-3 divide-x divide-line sm:shrink-0 sm:gap-5 sm:divide-x-0">
            <div className="flex flex-1 flex-col items-start sm:flex-none sm:items-end">
              <span className="font-mono text-2xl font-bold leading-none tabular text-accent sm:text-3xl">
                {r.visits.toLocaleString()}
              </span>
              <span className="mt-1.5 text-[10px] uppercase tracking-[0.12em] text-mute">
                방문 · {r.deptCount}개 부서
              </span>
            </div>
            {r.rating !== undefined && (
              <div className="flex flex-1 flex-col items-start pl-3 sm:flex-none sm:items-end sm:border-l sm:border-line sm:pl-5">
                <span className="font-mono text-2xl font-bold leading-none tabular text-accent2 sm:text-3xl">
                  ★ {r.rating.toFixed(1)}
                </span>
                {r.ratingCount !== undefined && (
                  <span className="mt-1.5 text-[10px] uppercase tracking-[0.12em] text-mute">
                    Google {r.ratingCount.toLocaleString()}개
                  </span>
                )}
              </div>
            )}
          </div>
        </div>

        <section className="mt-6 grid grid-cols-3 gap-3">
          {photoSlots.map((i) => {
            const src = photos[i];
            return (
              <div
                key={i}
                className="relative aspect-[4/3] overflow-hidden rounded-xl border border-line bg-elev"
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
                  <PhotoPlaceholder
                    name={r.name}
                    region={r.region}
                    rank={r.rank}
                    slot={i}
                  />
                )}
              </div>
            );
          })}
        </section>

        <section className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-3">
          <div className="overflow-hidden rounded-xl border border-line bg-elev">
            {r.lat !== undefined && r.lng !== undefined ? (
              <KakaoMap
                markers={[
                  { id: r.rank, lat: r.lat, lng: r.lng, label: r.name },
                ]}
                level={4}
                className="h-56 w-full"
              />
            ) : (
              <div className="flex h-56 w-full items-center justify-center text-sm text-mute">
                위치 정보 없음
              </div>
            )}
          </div>

          <div className="flex h-56 flex-col divide-y divide-line overflow-hidden rounded-xl border border-line bg-elev">
            {r.formattedAddress || r.googleMapsUri ? (
              <a
                href={r.googleMapsUri ?? "#"}
                target="_blank"
                rel="noopener noreferrer"
                className="group flex items-start gap-2.5 px-3 py-2.5 transition hover:bg-elev2"
              >
                <IconPin className="mt-0.5 h-4 w-4 shrink-0 text-mute group-hover:text-accent" />
                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm font-medium text-ink">
                    {r.formattedAddress ?? "지도에서 보기"}
                  </div>
                  {r.googleMapsUri && (
                    <div className="text-[11px] text-mute group-hover:text-accent">
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
                className="group flex items-center gap-2.5 px-3 py-2.5 transition hover:bg-elev2"
              >
                <IconPhone className="h-4 w-4 shrink-0 text-mute group-hover:text-accent" />
                <span className="truncate text-sm font-medium text-ink tabular-nums">
                  {r.phone}
                </span>
              </a>
            ) : (
              <InfoEmpty icon={<IconPhone className="h-4 w-4" />} text="전화번호 없음" />
            )}

            <div className="flex min-h-0 flex-1 items-start gap-2.5 px-3 py-2.5">
              <IconClock className="mt-0.5 h-4 w-4 shrink-0 text-mute" />
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
                          <span className="w-10 shrink-0 text-mute">{day}</span>
                          <span className="text-ink/85">{time}</span>
                        </li>
                      );
                    })}
                  </ul>
                ) : (
                  <span className="text-xs text-mute">영업시간 정보 없음</span>
                )}
              </div>
            </div>
          </div>

          <div className="flex h-56 flex-col rounded-xl border border-line bg-elev p-3">
            <div className="mb-2 text-[10px] font-semibold uppercase tracking-[0.12em] text-mute">
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

        <p className="mt-6 text-xs leading-5 text-mute">
          수치는 서울 열린데이터광장·각 자치구가 공개한 업무추진비 집행내역을
          가맹점별로 집계한 결과입니다. 평점·사진·영업시간은 Google Places
          데이터입니다.
        </p>

        <section className="mt-10 border-t border-line pt-8">
          <h2 className="text-xl font-bold tracking-tight text-ink">댓글</h2>
          <p className="mt-1 text-sm text-mute">
            가본 후기·정정 의견·일행 추천 등 자유롭게 남겨주세요.
          </p>
          <div className="mt-5">
            <CommentSection rank={r.rank} />
          </div>
        </section>
      </main>

      <SiteFooter />
    </div>
  );
}

function nameInitial(raw: string): string {
  // 선행 (주)/(유) 같은 회사명 prefix 제거 후 첫 글자
  const stripped = raw.replace(/^[(（][^)）]+[)）]\s*/, "").trim();
  return (stripped[0] || raw.trim()[0] || "?").toUpperCase();
}

function nameHue(name: string): number {
  let h = 7;
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) | 0;
  return Math.abs(h) % 360;
}

function PhotoPlaceholder({
  name,
  region,
  rank,
  slot,
}: {
  name: string;
  region: string;
  rank: number;
  slot: number;
}) {
  const hue = nameHue(name);
  const h2 = (hue + 35) % 360;
  const bg = `linear-gradient(135deg, hsl(${hue} 62% 50%), hsl(${h2} 70% 38%))`;
  const initial = nameInitial(name);
  // 슬롯별 부가 정보 변주 (한 면이 다 같은 그림이 안 되도록)
  const sub =
    slot === 0
      ? `${region} · ${rank}위`
      : slot === 1
        ? "사진 준비 중"
        : "공슐랭";
  return (
    <div
      className="relative flex h-full w-full flex-col items-center justify-center overflow-hidden text-white"
      style={{ background: bg }}
    >
      <div
        aria-hidden
        className="pointer-events-none absolute -right-6 -top-6 h-24 w-24 rounded-full bg-white/10 blur-xl"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute -bottom-8 -left-6 h-28 w-28 rounded-full bg-black/15 blur-2xl"
      />
      <span className="text-5xl font-extrabold leading-none drop-shadow-sm">
        {initial}
      </span>
      <span className="mt-2 px-3 text-center text-[11px] font-medium uppercase tracking-wider text-white/80">
        {sub}
      </span>
    </div>
  );
}

function InfoEmpty({ icon, text }: { icon: React.ReactNode; text: string }) {
  return (
    <div className="flex items-center gap-2.5 px-3 py-2.5 text-mute">
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
    <div className="flex flex-col justify-center rounded-lg border border-line bg-base p-2">
      <div className="text-[10px] uppercase tracking-[0.1em] text-mute">
        {label}
      </div>
      <div
        className={`mt-0.5 font-mono leading-tight tabular ${
          highlight
            ? "text-accent text-lg font-bold"
            : "text-ink text-base font-bold"
        }`}
      >
        {value}
      </div>
    </div>
  );
}
