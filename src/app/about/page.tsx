import Link from "next/link";

export const metadata = {
  title: "소개 · 공슐랭",
  description: "공슐랭은 무엇이고, 어떤 데이터를 어떻게 분석하는지 설명합니다.",
};

export default function AboutPage() {
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
          <nav className="flex gap-6 text-sm font-medium text-zinc-600 dark:text-zinc-400">
            <Link href="/" className="hover:text-zinc-900 dark:hover:text-zinc-50">
              맛집
            </Link>
            <Link
              href="/about"
              className="text-zinc-900 dark:text-zinc-50"
            >
              소개
            </Link>
          </nav>
        </div>
      </header>

      <main className="mx-auto w-full max-w-3xl flex-1 px-6 py-16">
        <h1 className="text-4xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
          공슐랭이 뭔가요?
        </h1>
        <p className="mt-4 text-lg leading-8 text-zinc-600 dark:text-zinc-400">
          공슐랭은 <strong className="font-semibold text-zinc-900 dark:text-zinc-100">공무원 + 미슐랭</strong>의
          합성어로, 공무원들이 업무추진비로 자주 찾는 식당을 모아 보여주는 사이트입니다.
          전문가 평론가 대신 <em>공공 지출 데이터</em>가 매긴 랭킹을 보여줍니다.
        </p>

        <Section title="데이터 출처">
          행정안전부가 운영하는{" "}
          <Anchor href="https://www.lofin365.go.kr/">지방재정365</Anchor>의 공개 API를
          통해 전국 17개 광역지자체의{" "}
          <strong>업무추진비 집행내역</strong>을 수집합니다. 각 집행 기록에는
          가맹점명(식당), 사용 금액, 집행 부서, 집행 일자가 포함됩니다.
        </Section>

        <Section title="랭킹 산정 방식">
          가맹점명을 기준으로 모든 집행 기록을 묶어, 다음 네 가지 지표로 정렬합니다.
          기본은 이용횟수 내림차순입니다.
          <ul className="mt-4 list-disc space-y-1.5 pl-6 text-zinc-600 dark:text-zinc-400">
            <li>
              <strong className="text-zinc-800 dark:text-zinc-200">이용횟수</strong> —
              해당 식당이 업무추진비 카드 결제에 등장한 총 횟수
            </li>
            <li>
              <strong className="text-zinc-800 dark:text-zinc-200">총이용금액</strong> —
              집계 기간 누적 결제액
            </li>
            <li>
              <strong className="text-zinc-800 dark:text-zinc-200">평균금액</strong> —
              결제 1회당 평균 금액
            </li>
            <li>
              <strong className="text-zinc-800 dark:text-zinc-200">집행부서수</strong> —
              해당 식당을 이용한 서로 다른 부서의 수
            </li>
          </ul>
        </Section>

        <Section title="알아두실 점">
          <ul className="mt-2 list-disc space-y-1.5 pl-6 text-zinc-600 dark:text-zinc-400">
            <li>
              랭킹은 <strong>이용 빈도</strong>이지, 음식 맛이나 서비스 품질의 평가가
              아닙니다. 청사 인근 입지나 단체 회식이 가능한 규모 등 행정 편의도 영향을
              미칩니다.
            </li>
            <li>
              가맹점명이 다르게 등록된 같은 식당(예: 본점/지점)은 별도로 집계됩니다.
            </li>
            <li>
              데이터는 지방재정365가 공개한 시점까지의 분기/연도 단위 집계입니다.
              실시간 정보가 아닙니다.
            </li>
          </ul>
        </Section>

      </main>

      <footer className="border-t border-zinc-200 bg-white py-8 text-center text-sm text-zinc-500 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-400">
        © 2026 공슐랭
      </footer>
    </div>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="mt-12">
      <h2 className="text-xl font-bold text-zinc-900 dark:text-zinc-50">
        {title}
      </h2>
      <div className="mt-3 text-base leading-7 text-zinc-600 dark:text-zinc-400">
        {children}
      </div>
    </section>
  );
}

function Anchor({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="font-medium text-orange-600 underline-offset-2 hover:underline dark:text-orange-400"
    >
      {children}
    </a>
  );
}
