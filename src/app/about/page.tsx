import SiteHeader from "@/components/SiteHeader";
import SiteFooter from "@/components/SiteFooter";

export const metadata = {
  title: "소개 · 공슐랭",
  description: "공슐랭은 무엇이고, 어떤 데이터를 어떻게 분석하는지 설명합니다.",
};

const CONTACT_EMAIL = "myelsj+gongsulrang@gmail.com";

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
          합성어로, 공무원 업무추진비(법카) 결제 내역에 자주 등장하는 식당을
          모아 보여주는 사이트입니다. 전문가 평론가 대신{" "}
          <em className="text-accent2 not-italic">공공 지출 데이터</em>가
          가리키는 빈도 통계입니다.
        </p>

        <Section title="데이터 출처">
          <ul className="mt-2 list-disc space-y-1.5 pl-6">
            <li>
              <strong className="text-ink">업무추진비 집행내역</strong> — 서울
              열린데이터광장(서울시청)과 25개 자치구가 공개한 분기·연도별
              집행내역
            </li>
            <li>
              <strong className="text-ink">
                식당 사진·평점·영업시간·전화번호
              </strong>{" "}
              — Google Places API
            </li>
            <li>
              <strong className="text-ink">좌표·주소·구·동</strong> — Kakao
              Local API
            </li>
          </ul>
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
              가맹점명이 다르게 등록된 같은 식당(예: 본점/지점)은 같은 구
              안에서만 합쳐져 별개로 집계됩니다.
            </li>
            <li>
              데이터는 공개 시점까지의 분기/연도 단위 집계입니다. 실시간 정보가
              아닙니다.
            </li>
          </ul>
        </Section>

        <Section title="알림">
          <ul className="mt-2 list-disc space-y-1.5 pl-6">
            <li>
              이 사이트는{" "}
              <strong className="text-ink">공공 데이터의 가공·시각화</strong>를
              목적으로 한 비영리 프로젝트입니다.
            </li>
            <li>
              사이트 곳곳에 등장하는 “공슐랭”·“맛집 탐방” 등 표현은 결제 빈도
              통계에 대한 비유적 카피이며, 식당의 영업·품질에 대한 공식 인증이나
              평가가 아닙니다.
            </li>
            <li>
              랭킹과 통계는 <strong className="text-ink">참고용 정보</strong>로
              제공되며, 식당의 실제 영업 활동과 무관할 수 있습니다.
            </li>
            <li>
              공개 자료의 누락·표기 차이로 가맹점명이나 주소가 부정확할 수
              있습니다.
            </li>
          </ul>
        </Section>

        <Section id="correction" title="정정·삭제 요청">
          <p>
            아래 항목에 대해 이메일로 정정·삭제 요청을 받습니다.
          </p>
          <ul className="mt-3 list-disc space-y-1.5 pl-6">
            <li>식당 정보 정정 — 가맹점명, 주소, 영업 상태 등</li>
            <li>사진 삭제 — 특정 사진의 노출 중단</li>
            <li>특정 식당 페이지의 노출 중단</li>
            <li>그 외 표기·표현에 대한 의견</li>
          </ul>
          <p className="mt-4">메일에 다음 내용을 포함해 주시면 빠른 처리에 도움이 됩니다.</p>
          <ul className="mt-2 list-disc space-y-1 pl-6">
            <li>대상 식당명·주소·관련 URL</li>
            <li>요청 내용과 사유</li>
            <li>본인 확인이 필요한 경우 사업자등록증·명함 등</li>
          </ul>
          <a
            href={`mailto:${CONTACT_EMAIL}?subject=${encodeURIComponent("공슐랭 정정·삭제 요청")}`}
            className="mt-6 inline-flex items-center gap-2 rounded-lg border border-accent bg-accent px-4 py-2 text-sm font-semibold text-[#1a0f08] transition hover:bg-accent/90"
          >
            이메일로 요청하기 ({CONTACT_EMAIL}) →
          </a>
          <p className="mt-4 text-sm">
            원본 업무추진비 데이터는 각 공공기관이 공개한 자료입니다. 본
            사이트는 가공·표시 영역만 담당하며, 원본 자료의 변경·취하는 발행
            기관(서울시청, 각 자치구청)에 직접 문의해야 합니다.
          </p>
        </Section>
      </main>

      <SiteFooter />
    </div>
  );
}

function Section({
  id,
  title,
  children,
}: {
  id?: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section id={id} className="mt-14 scroll-mt-20">
      <h2 className="text-xl font-bold tracking-tight text-ink">{title}</h2>
      <div className="mt-3 text-base leading-7 text-mute">{children}</div>
    </section>
  );
}
