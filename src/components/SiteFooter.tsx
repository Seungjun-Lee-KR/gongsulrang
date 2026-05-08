import Link from "next/link";

export default function SiteFooter() {
  return (
    <footer className="mt-auto border-t border-line bg-base py-10 text-xs leading-relaxed text-mute">
      <div className="mx-auto flex max-w-6xl flex-col gap-5 px-6 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-2">
          <div className="font-medium text-ink/80">© 2026 공슐랭</div>
          <div>
            출처: 서울 열린데이터광장 · 25개 자치구 업무추진비 공개자료
            <br />
            식당 사진·평점·영업시간: Google Places · 좌표: Kakao Local
          </div>
        </div>
        <nav className="flex flex-wrap gap-x-5 gap-y-2">
          <Link href="/about" className="transition hover:text-ink">
            소개
          </Link>
          <Link href="/about#correction" className="transition hover:text-ink">
            정정·삭제 요청
          </Link>
        </nav>
      </div>
    </footer>
  );
}
