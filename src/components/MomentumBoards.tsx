import type { MomentumEntry } from "@/types/momentum";

export const MOMENTUM_COLORS = {
  rising: "var(--color-accent)",
  newcomers: "var(--color-accent2)",
  steady: "#a9b2c4",
  lunch: "#d99a2b",
  dinner: "#8b7ff0",
} as const;

/** 끼니 성향 배지 — 보드 선정 기준(점심 70%·저녁 50%)과 같은 임계 */
function mealBadge(e: MomentumEntry): string | null {
  if (!e.timed || e.timed < 10) return null;
  if ((e.lunch ?? 0) / e.timed >= 0.7) return "🌞 점심형";
  if ((e.dinner ?? 0) / e.timed >= 0.5) return "🌙 저녁형";
  return null;
}

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
  quarters,
  color,
  metric,
}: {
  entry: MomentumEntry;
  index: number;
  quarters: string[];
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
          {entry.kakao ? `${entry.kakao.address} · ` : ""}
          {entry.perPerson ? (
            <span
              className="font-semibold text-ink/80"
              title={`법인카드 결제액 ÷ 인원 중앙값 (표본 ${entry.perPersonN}건)`}
            >
              인당 {entry.perPerson.toLocaleString()}원
            </span>
          ) : (
            <>평균 {entry.avgAmount.toLocaleString()}원</>
          )}{" "}
          · {entry.depts}개 부서
          {mealBadge(entry) && <> · {mealBadge(entry)}</>}
        </div>
      </td>
      <td className="w-[216px] px-3.5 py-3">
        <Sparkline series={entry.series} quarters={quarters} color={color} />
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

export function Board({
  title,
  how,
  color,
  items,
  quarters,
  metric,
}: {
  title: string;
  how: string;
  color: string;
  items: MomentumEntry[];
  quarters: string[];
  metric: (e: MomentumEntry) => { value: string; label: string };
}) {
  if (items.length === 0) return null;
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
                quarters={quarters}
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
