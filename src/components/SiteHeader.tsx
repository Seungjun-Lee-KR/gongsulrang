import Link from "next/link";

export default function SiteHeader() {
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-base/70 backdrop-blur-md">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link href="/" className="flex items-center gap-2.5 group">
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
        <nav className="hidden items-center gap-1 text-sm font-medium text-mute sm:flex">
          {[
            { href: "/region", label: "구별" },
            { href: "/agency", label: "기관별" },
            { href: "/map", label: "지도" },
            { href: "/about", label: "소개" },
          ].map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="rounded-md px-3 py-1.5 transition hover:bg-elev hover:text-ink"
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
