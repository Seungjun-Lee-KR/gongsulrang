import Link from "next/link";
import SiteHeader from "@/components/SiteHeader";
import SiteFooter from "@/components/SiteFooter";
import { Board, MOMENTUM_COLORS } from "@/components/MomentumBoards";
import { momentum } from "@/data/momentum";
import { districtMomentum } from "@/data/momentum-districts";

export const metadata = {
  title: "요즘 뜨는 집 · 공슐랭",
  description:
    "서울시 본청 업무추진비 15만 건으로 찾은 분기별 식당 트렌드 — 뜨는 집, 신규 진입, 스테디셀러",
};

export default function TrendingPage() {
  const { rising, newcomers, steady, stats, quarters, recentQuarters, baseQuarters } =
    momentum;

  return (
    <div className="flex flex-1 flex-col bg-base text-ink">
      <SiteHeader />
      <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-12">
        <div className="mb-4">
          <div className="text-[10px] font-medium uppercase tracking-[0.18em] text-accent">
            Trending
          </div>
          <h1 className="mt-2 text-4xl font-extrabold tracking-tight text-ink sm:text-5xl">
            요즘 뜨는 집
          </h1>
          <p className="mt-3 max-w-prose text-sm text-mute">
            서울시 본청 415개 부서가 13개 분기 동안 긁은{" "}
            <strong className="font-semibold text-ink">
              법인카드 {stats.transactions.toLocaleString()}건
            </strong>
            을 분기별로 접어, 정적 랭킹이 보여주지 못하는 움직임을 봅니다.
            리뷰는 조작할 수 있지만 지출 기록은 조작할 수 없습니다.
          </p>
        </div>

        {districtMomentum.length > 0 && (
          <nav
            aria-label="자치구별 뜨는 집"
            className="mt-6 rounded-2xl border border-line bg-elev p-4"
          >
            <div className="text-[11px] font-semibold uppercase tracking-[0.1em] text-mute">
              자치구별로 보기
            </div>
            <div className="mt-2.5 flex flex-wrap gap-1.5">
              {districtMomentum.map((d) => (
                <Link
                  key={d.slug}
                  href={`/trending/${encodeURIComponent(d.name)}`}
                  className="rounded-full border border-line2 px-3 py-1 text-[12.5px] font-medium text-ink/80 transition hover:border-accent hover:text-accent"
                >
                  {d.name}
                </Link>
              ))}
            </div>
          </nav>
        )}

        <Board
          title="뜨는 집"
          how="기존 식당 중 최근 2분기 방문이 전년 동기 대비 가장 가파르게 는 곳"
          color={MOMENTUM_COLORS.rising}
          items={rising.slice(0, 10)}
          quarters={quarters}
          metric={(e) => ({
            value: `${e.growth}×`,
            label: `${e.base} → ${e.recent}회`,
          })}
        />
        <Board
          title="신규 진입"
          how="전년 동분기 기록이 없다가 최근 2분기에 나타난 곳 — 방문수 순"
          color={MOMENTUM_COLORS.newcomers}
          items={newcomers.slice(0, 10)}
          quarters={quarters}
          metric={(e) => ({ value: `${e.recent}회`, label: "최근 2분기" })}
        />
        <Board
          title="스테디셀러"
          how="13개 분기 전부 등장하며 변동이 가장 적은 곳 — 검증된 노포"
          color={MOMENTUM_COLORS.steady}
          items={steady.slice(0, 10)}
          quarters={quarters}
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
              최근 2분기({recentQuarters.join("+")})를 전년 동분기(
              {baseQuarters.join("+")})와 비교합니다 — 연말 회식 시즌 효과가
              성장으로 둔갑하지 않습니다.
            </li>
            <li>
              <strong className="font-semibold text-ink/90">노이즈 필터:</strong>{" "}
              최근 방문 15회 미만, 이용 부서 3곳 미만은 제외합니다 — 한 부서의
              단골집이 &ldquo;뜨는 집&rdquo;으로 잡히는 것을 막습니다.
            </li>
            <li>
              <strong className="font-semibold text-ink/90">
                가게 식별(정규화):
              </strong>{" "}
              같은 가게가 장부에 수십 가지 표기로 등장합니다. 이름·주소
              클러스터링 후 카카오 장소 매칭으로 실제 가게에 앵커링했습니다
              (방문 10회 이상{" "}
              {(stats.kakaoMatched + stats.kakaoUnmatched).toLocaleString()}곳 중{" "}
              {stats.kakaoMatched.toLocaleString()}곳,{" "}
              {Math.round(
                (stats.kakaoMatched * 100) /
                  (stats.kakaoMatched + stats.kakaoUnmatched),
              )}
              %). 매칭된 상호는 카카오맵 공식 명칭입니다.
            </li>
            <li>
              <strong className="font-semibold text-ink/90">장부명 배지:</strong>{" "}
              카카오에서 찾지 못한 곳입니다 — 브랜드를 유추할 수 없는
              법인명이거나 폐업했을 수 있습니다. 틀린 이름을 조용히 보여주느니
              장부 표기를 그대로 둡니다.
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
