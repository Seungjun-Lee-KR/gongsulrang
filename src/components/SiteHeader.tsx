import Link from "next/link";

export default function SiteHeader() {
  return (
    <header className="border-b border-zinc-200 bg-white/80 backdrop-blur dark:border-zinc-800 dark:bg-zinc-900/80">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
        <Link href="/" className="flex items-center gap-2">
          <span className="text-2xl">🏛️</span>
          <span className="text-lg font-bold text-zinc-900 dark:text-zinc-50">
            공슐랭
          </span>
          <span className="hidden text-xs text-zinc-500 dark:text-zinc-400 sm:inline">
            공무원이 사용한 법인카드 결제 정보를 활용한 맛집 소개
          </span>
        </Link>
        <nav className="hidden gap-6 text-sm font-medium text-zinc-600 dark:text-zinc-400 sm:flex">
          <Link href="/region" className="hover:text-zinc-900 dark:hover:text-zinc-50">
            구별
          </Link>
          <Link href="/agency" className="hover:text-zinc-900 dark:hover:text-zinc-50">
            기관별
          </Link>
          <Link href="/map" className="hover:text-zinc-900 dark:hover:text-zinc-50">
            지도
          </Link>
          <Link href="/about" className="hover:text-zinc-900 dark:hover:text-zinc-50">
            소개
          </Link>
        </nav>
      </div>
    </header>
  );
}
