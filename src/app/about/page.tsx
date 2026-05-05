import SiteHeader from "@/components/SiteHeader";
import SiteFooter from "@/components/SiteFooter";

export const metadata = {
  title: "소개 · 공슐랭",
  description: "공슐랭은 무엇이고, 어떤 데이터를 어떻게 분석하는지 설명합니다.",
};

export default function AboutPage() {
  return (
    <div className="flex flex-1 flex-col bg-base text-ink">
      <SiteHeader />

      <main className="mx-auto w-full max-w-3xl flex-1 px-6 py-16">
        <div className="text-[10px] font-medium uppercase tracking-[0.18em] text-accent">
          About
        </div>
        <h1 className="mt-2 text-4xl font-extrabold tracking-tight text-ink sm:text-5xl">
          공슐랭이 뭔가요?
        </h1>
        <p className="mt-6 text-lg leading-8 text-mute">
          공슐랭은{" "}
          <strong className="font-semibold text-ink">공무원 + 미슐랭</strong>의
          합성어로, 공무원들이 업무추진비로 자주 찾는 식당을 모아 보여주는
          사이트입니다. 전문가 평론가 대신{" "}
          <em className="text-accent2 not-italic">공공 지출 데이터</em>가 매긴
          랭킹입니다.
        </p>

        <Section title="데이터 출처">
          서울시가 공개한 서울시청 및 25개 구청의{" "}
          <strong className="text-ink">업무추진비 집행내역</strong>을
          분석하였습니다.
        </Section>

        <Section title="랭킹 산정 방식">
          <p>
            가맹점명을 기준으로 모든 집행 기록을 묶어, 다음 네 가지 지표로
            정렬합니다. 기본은 이용횟수 내림차순입니다.
          </p>
          <ul className="mt-4 list-disc space-y-1.5 pl-6">
            <li>
              <strong className="text-ink">이용횟수</strong> — 해당 식당이
              업무추진비 카드 결제에 등장한 총 횟수
            </li>
            <li>
              <strong className="text-ink">총이용금액</strong> — 집계 기간 누적
              결제액
            </li>
            <li>
              <strong className="text-ink">평균금액</strong> — 결제 1회당 평균
              금액
            </li>
            <li>
              <strong className="text-ink">집행부서수</strong> — 해당 식당을
              이용한 서로 다른 부서의 수
            </li>
          </ul>
        </Section>

        <Section title="알아두실 점">
          <ul className="mt-2 list-disc space-y-1.5 pl-6">
            <li>
              랭킹은 <strong className="text-ink">이용 빈도</strong>이지, 음식
              맛이나 서비스 품질의 평가가 아닙니다. 청사 인근 입지나 단체 회식이
              가능한 규모 등 행정 편의도 영향을 미칩니다.
            </li>
            <li>
              가맹점명이 다르게 등록된 같은 식당(예: 본점/지점)은 같은 구 안에서만
              합쳐져 별개로 집계됩니다.
            </li>
            <li>
              데이터는 공개 시점까지의 분기/연도 단위 집계입니다. 실시간 정보가
              아닙니다.
            </li>
          </ul>
        </Section>
      </main>

      <SiteFooter />
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
    <section className="mt-14">
      <h2 className="text-xl font-bold tracking-tight text-ink">{title}</h2>
      <div className="mt-3 text-base leading-7 text-mute">{children}</div>
    </section>
  );
}

