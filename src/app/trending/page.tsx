import SiteHeader from "@/components/SiteHeader";
import SiteFooter from "@/components/SiteFooter";
import { momentum } from "@/data/momentum";
import type { MomentumEntry } from "@/types/momentum";

export const metadata = {
  title: "요즘 뜨는 집 · 공슐랭",
  description:
    "서울시 본청 업무추진비 15만 건으로 찾은 분기별 식당 트렌드 — 뜨는 집, 신규 진입, 스테디셀러",
};

const SECTION_COLORS = {
  rising: "var(--color-accent)",
  newcomers: "var(--color-accent2)",
  steady: "#a9b2c4",
} as const;

/** 분기별 방문 추이 스파크라인 (서버 렌더, 네이티브 툴팁) */
function Sparkline({
  series,
  quarters,
  color,
}: {
  series: number[];
  quarters: string[];
  color: string;
}) {
  const W = 200;
  const H = 40;
  const PAD = 3;
  const max = Math.max(...series, 1);
  const x = (i: number) => PAD + (i * (W - PAD * 2)) / (series.length - 1);
  const y = (v: number) => H - PAD - (v * (H - PAD * 2)) / max;
  const pts = series.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`);
  const line = pts.join(" ");
  const area = `${PAD},${H - PAD} ${line} ${W - PAD},${H - PAD}`;
  const bandX = x(series.length - 2); // 최근 2분기 강조 밴드
  const last = series[series.length - 1];

  return (
    <svg
      width={W}
      height={H}
      viewBox={`0 0 ${W} ${H}`}
      role="img"
      aria-label={`분기별 방문 추이: ${series.join(", ")}`}
      className="block"
    >
      <rect
        x={bandX.toFixed(1)}
        y={0}
        width={(W - PAD - bandX).toFixed(1)}
        height={H}
        fill={color}
        opacity={0.07}
      />
      <line
        x1={PAD}
        y1={H - PAD}
        x2={W - PAD}
        y2={H - PAD}
        stroke="var(--color-line2)"
        strokeWidth={1}
      />
      <polygon points={area} fill={color} opacity={0.1} />
      <polyline
        points={line}
        fill="none"
        stroke={color}
        strokeWidth={2}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      <circle
        cx={x(series.length - 1).toFixed(1)}
        cy={y(last).toFixed(1)}
        r={3}
        fill={color}
        stroke="var(--color-elev)"
        strokeWidth={2}
      />
      {series.map((v, i) => (
        <rect
          key={i}
          x={(x(i) - 7.7).toFixed(1)}
          y={0}
          width={15.4}
          height={H}
          fill="transparent"
        >
          <title>{`${quarters[i].replace("-", " ")} · ${v}회`}</title>
        </rect>
      ))}
    </svg>
  );
}

function Row({
  entry,
  index,
  color,
  metric,
}: {
  entry: MomentumEntry;
  index: number;
  color: string;
  metric: { value: string; label: string };
}) {
  return (
    <tr className="border-t border-line first:border-t-0 transition hover:bg-elev2">
      <td className="w-9 py-3 pl-4 pr-0 text-right font-mono text-[13px] tabular text-mute">
        {index + 1}
      </td>
      <td className="min-w-[220px] px-3.5 py-3">
        <div className="text-[15px] font-bold tracking-tight text-ink">
          {entry.kakao ? (
            <>
              <a
                href={entry.kakao.url}
                target="_blank"
                rel="noopener noreferrer"
                className="border-b border-line2 transition hover:border-accent"
              >
                {entry.name}
              </a>
              <span className="ml-1.5 rounded border border-line2 px-1.5 py-px align-[1px] text-[10.5px] font-semibold text-mute">
                {entry.kakao.category}
              </span>
            </>
          ) : (
            <>
              {entry.name}
              <span
                className="ml-1.5 rounded border border-dashed border-line2 px-1.5 py-px align-[1px] text-[10.5px] font-semibold text-mute"
                title="카카오 장소 매칭 실패 — 장부상 표기 그대로"
              >
                장부명
              </span>
            </>
          )}
        </div>
        <div className="mt-0.5 text-xs tabular text-mute">
          {entry.kakao ? `${entry.kakao.address} · ` : ""}평균{" "}
          {entry.avgAmount.toLocaleString()}원 · {entry.depts}개 부서
        </div>
      </td>
      <td className="w-[216px] px-3.5 py-3">
        <Sparkline series={entry.series} quarters={momentum.quarters} color={color} />
      </td>
      <td className="w-24 whitespace-nowrap px-3.5 py-3 text-right tabular">
        <span className="text-[14.5px] font-extrabold" style={{ color }}>
          {metric.value}
        </span>
        <span className="block text-[11px] font-medium text-mute">
          {metric.label}
        </span>
      </td>
    </tr>
  );
}

function Board({
  title,
  how,
  color,
  items,
  metric,
}: {
  title: string;
  how: string;
  color: string;
  items: MomentumEntry[];
  metric: (e: MomentumEntry) => { value: string; label: string };
}) {
  return (
    <section className="mt-12">
      <div className="flex flex-wrap items-baseline gap-3">
        <h2 className="flex items-center gap-2.5 text-xl font-extrabold tracking-tight text-ink">
          <span
            aria-hidden
            className="h-2.5 w-2.5 shrink-0 rounded-[3px]"
            style={{ background: color }}
          />
          {title}
        </h2>
        <span className="text-[12.5px] text-mute">{how}</span>
      </div>
      <div className="mt-3.5 overflow-x-auto rounded-2xl border border-line bg-elev">
        <table className="w-full min-w-[720px] border-collapse">
          <tbody>
            {items.map((e, i) => (
              <Row
                key={e.kakao?.id ?? e.name}
                entry={e}
                index={i}
                color={color}
                metric={metric(e)}
              />
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export default function TrendingPage() {
  const { rising, newcomers, steady, stats, recentQuarters, baseQuarters } =
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

        <Board
          title="뜨는 집"
          how="기존 식당 중 최근 2분기 방문이 전년 동기 대비 가장 가파르게 는 곳"
          color={SECTION_COLORS.rising}
          items={rising.slice(0, 10)}
          metric={(e) => ({
            value: `${e.growth}×`,
            label: `${e.base} → ${e.recent}회`,
          })}
        />
        <Board
          title="신규 진입"
          how="전년 동분기 기록이 없다가 최근 2분기에 나타난 곳 — 방문수 순"
          color={SECTION_COLORS.newcomers}
          items={newcomers.slice(0, 10)}
          metric={(e) => ({ value: `${e.recent}회`, label: "최근 2분기" })}
        />
        <Board
          title="스테디셀러"
          how="13개 분기 전부 등장하며 변동이 가장 적은 곳 — 검증된 노포"
          color={SECTION_COLORS.steady}
          items={steady.slice(0, 10)}
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
