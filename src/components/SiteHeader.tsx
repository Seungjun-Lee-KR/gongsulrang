import Link from "next/link";

export default function SiteHeader() {
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-base/70 backdrop-blur-md">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3.5 sm:px-6 sm:py-4">
        <Link href="/" className="flex shrink-0 items-center gap-2.5 group">
          <span
            aria-hidden
            className="h-2.5 w-2.5 rounded-full"
            style={{
              background:
                "linear-gradient(135deg, var(--color-accent), #ffd07a 60%, var(--color-accent2))",
            }}
          />
          <span className="text-base font-bold tracking-tight text-ink">
            공슐랭
          </span>
          <span className="hidden text-[11px] font-medium uppercase tracking-[0.18em] text-mute sm:inline">
            The Officials' Guide
          </span>
        </Link>
        <nav className="-mr-2 flex items-center gap-0.5 text-[13px] font-medium text-mute sm:gap-1 sm:text-sm">
          {[
            { href: "/region", label: "구별" },
            { href: "/agency", label: "기관별" },
            { href: "/map", label: "지도" },
            { href: "/about", label: "소개" },
          ].map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="rounded-md px-2 py-1.5 transition hover:bg-elev hover:text-ink sm:px-3"
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
