import Link from "next/link";
import { notFound } from "next/navigation";
import SiteHeader from "@/components/SiteHeader";
import SiteFooter from "@/components/SiteFooter";
import { Board, MOMENTUM_COLORS } from "@/components/MomentumBoards";
import {
  districtMomentum,
  getDistrictMomentum,
} from "@/data/momentum-districts";

export function generateStaticParams() {
  return districtMomentum.map((d) => ({ gu: d.name }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ gu: string }>;
}) {
  const { gu } = await params;
  const name = decodeURIComponent(gu);
  return {
    title: `${name} 뜨는 집 · 공슐랭`,
    description: `${name} 업무추진비 데이터로 찾은 분기별 식당 트렌드 — 뜨는 집, 신규 진입, 스테디셀러`,
  };
}

export default async function DistrictTrendingPage({
  params,
}: {
  params: Promise<{ gu: string }>;
}) {
  const { gu } = await params;
  const name = decodeURIComponent(gu);
  const d = getDistrictMomentum(name);
  if (!d) notFound();

  const matchTargets = d.stats.kakaoMatched + d.stats.kakaoUnmatched;

  return (
    <div className="flex flex-1 flex-col bg-base text-ink">
      <SiteHeader />
      <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-12">
        <div className="mb-4">
          <Link href="/trending" className="text-xs text-mute hover:text-ink">
            ← 서울시 전체 뜨는 집
          </Link>
          <div className="mt-3 text-[10px] font-medium uppercase tracking-[0.18em] text-accent">
            Trending
          </div>
          <h1 className="mt-1 text-4xl font-extrabold tracking-tight text-ink sm:text-5xl">
            {d.name} 뜨는 집
          </h1>
          <p className="mt-3 max-w-prose text-sm text-mute">
            {d.name} 공무원들이 {d.quarters.length}개 분기 동안 긁은{" "}
            <strong className="font-semibold text-ink">
              법인카드 {d.stats.transactions.toLocaleString()}건
            </strong>
            으로 본 우리 동네 식당의 움직임입니다. 리뷰는 조작할 수 있지만
            지출 기록은 조작할 수 없습니다.
          </p>
          <Link
            href={`/region/${encodeURIComponent(d.name)}`}
            className="mt-3 inline-block rounded-full border border-accent/40 px-3 py-1 text-xs font-semibold text-accent transition hover:bg-accent/10"
          >
            {d.name} 누적 랭킹 보기 →
          </Link>
        </div>

        <nav
          aria-label="다른 자치구"
          className="mt-6 flex flex-wrap gap-1.5"
        >
          {districtMomentum.map((o) =>
            o.slug === d.slug ? (
              <span
                key={o.slug}
                aria-current="page"
                className="rounded-full bg-accent/15 px-3 py-1 text-[12.5px] font-semibold text-accent"
              >
                {o.name}
              </span>
            ) : (
              <Link
                key={o.slug}
                href={`/trending/${encodeURIComponent(o.name)}`}
                className="rounded-full border border-line2 px-3 py-1 text-[12.5px] font-medium text-ink/80 transition hover:border-accent hover:text-accent"
              >
                {o.name}
              </Link>
            ),
          )}
        </nav>

        <Board
          title="뜨는 집"
          how="기존 식당 중 최근 2분기 방문이 전년 동기 대비 가장 가파르게 는 곳"
          color={MOMENTUM_COLORS.rising}
          items={d.rising.slice(0, 10)}
          quarters={d.quarters}
          metric={(e) => ({
            value: `${e.growth}×`,
            label: `${e.base} → ${e.recent}회`,
          })}
        />
        <Board
          title="신규 진입"
          how="전년 동분기 기록이 없다가 최근 2분기에 나타난 곳 — 방문수 순"
          color={MOMENTUM_COLORS.newcomers}
          items={d.newcomers.slice(0, 10)}
          quarters={d.quarters}
          metric={(e) => ({ value: `${e.recent}회`, label: "최근 2분기" })}
        />
        <Board
          title="스테디셀러"
          how={`${d.quarters.length}개 분기 전부 등장하며 변동이 가장 적은 곳 — 검증된 동네 노포`}
          color={MOMENTUM_COLORS.steady}
          items={d.steady.slice(0, 10)}
          quarters={d.quarters}
          metric={(e) => ({
            value: `cv ${e.cv}`,
            label: "변동계수 · 낮을수록 꾸준",
          })}
        />

        <div className="mt-14 rounded-2xl border border-line bg-elev p-6">
          <h3 className="text-[13px] font-semibold uppercase tracking-[0.1em] text-mute">
            방법과 한계
          </h3>
          <ul className="mt-3 list-disc space-y-1.5 pl-5 text-[13.5px] leading-relaxed text-mute marker:text-line2">
            <li>
              <strong className="font-semibold text-ink/90">계절성 제거:</strong>{" "}
              최근 2분기({d.recentQuarters.join("+")})를 전년 동분기(
              {d.baseQuarters.join("+")})와 비교합니다.
            </li>
            <li>
              <strong className="font-semibold text-ink/90">노이즈 필터:</strong>{" "}
              최근 방문 8회 미만, 이용 부서 2곳 미만은 제외합니다 — 자치구
              장부는 본청보다 작아 본청(15회·3곳)보다 낮춘 기준입니다.
            </li>
            <li>
              <strong className="font-semibold text-ink/90">가게 식별:</strong>{" "}
              {d.name} 장부에는 주소가 없어, 표기 클러스터링 후 구 중심 반경
              10km 카카오 검색으로 가게를 찾고 주소가 {d.name}인지
              검증했습니다 (방문 10회 이상 {matchTargets.toLocaleString()}곳 중{" "}
              {d.stats.kakaoMatched.toLocaleString()}곳,{" "}
              {matchTargets > 0
                ? Math.round((d.stats.kakaoMatched * 100) / matchTargets)
                : 0}
              %).
            </li>
            <li>
              <strong className="font-semibold text-ink/90">장부명 배지:</strong>{" "}
              같은 이름의 지점이 구 안에 여럿이거나(프랜차이즈) 카카오에서
              찾지 못한 곳입니다. 틀린 지점을 조용히 보여주느니 장부 표기를
              그대로 둡니다.
            </li>
            <li>
              스파크라인 세로축은 행마다 독립입니다 — 추세를 읽는 용도이며
              행간 절대량 비교가 아닙니다.
            </li>
          </ul>
        </div>
      </main>
      <SiteFooter />
    </div>
  );
}
