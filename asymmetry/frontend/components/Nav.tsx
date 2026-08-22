"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

const LINKS: { href: string; label: string; hint: string }[] = [
  { href: "/", label: "Opportunities", hint: "Top ranked by composite score" },
  { href: "/discoveries", label: "Discoveries", hint: "Recently surfaced" },
  { href: "/watchlist", label: "Watchlist", hint: "Grouped by verdict" },
  { href: "/signals", label: "Signals", hint: "Detected changes" },
  { href: "/thesis", label: "Thesis tracker", hint: "Conditions and breaks" },
  { href: "/risk", label: "Risk", hint: "Red flags by weight" },
  { href: "/agents", label: "Agent activity", hint: "Runs, tokens, cost" },
];

function isActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/" || pathname.startsWith("/opportunities");
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function Nav() {
  const pathname = usePathname() ?? "/";
  const [open, setOpen] = useState(false);

  const items = (
    <nav className="flex flex-col gap-0.5">
      {LINKS.map((l) => {
        const active = isActive(pathname, l.href);
        return (
          <Link
            key={l.href}
            href={l.href}
            onClick={() => setOpen(false)}
            className={`group rounded px-2.5 py-1.5 text-[13px] transition-colors ${
              active
                ? "bg-neutral-800/80 text-amber-300"
                : "text-neutral-400 hover:bg-neutral-800/40 hover:text-neutral-200"
            }`}
          >
            <span className="flex items-center gap-2">
              <span
                className={`h-1.5 w-1.5 rounded-full ${
                  active ? "bg-amber-400" : "bg-neutral-700 group-hover:bg-neutral-500"
                }`}
              />
              {l.label}
            </span>
            <span className="ml-3.5 block text-[10px] text-neutral-600">
              {l.hint}
            </span>
          </Link>
        );
      })}
    </nav>
  );

  return (
    <>
      {/* Mobile bar */}
      <div className="sticky top-0 z-30 flex items-center gap-3 border-b border-neutral-800 bg-neutral-950/95 px-4 py-2.5 backdrop-blur lg:hidden">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          aria-label="Toggle navigation"
          className="rounded border border-neutral-800 p-1.5 text-neutral-400 hover:text-neutral-100"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
            <path
              d="M2 4h12M2 8h12M2 12h12"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
            />
          </svg>
        </button>
        <Wordmark />
      </div>
      {open ? (
        <div className="border-b border-neutral-800 bg-neutral-950 px-3 py-2 lg:hidden">
          {items}
        </div>
      ) : null}

      {/* Desktop sidebar */}
      <aside className="sticky top-0 hidden h-dvh w-56 shrink-0 flex-col border-r border-neutral-800 bg-neutral-950 px-3 py-4 lg:flex">
        <div className="px-2.5 pb-4">
          <Wordmark />
        </div>
        {items}
        <div className="mt-auto px-2.5 pt-4 text-[10px] leading-relaxed text-neutral-600">
          Research tooling. Nothing here is a recommendation to transact, and no
          figure on any page is a forecast.
        </div>
      </aside>
    </>
  );
}

function Wordmark() {
  return (
    <Link href="/" className="flex items-center gap-2">
      <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
        <path d="M2 15 L9 3 L16 15" fill="none" stroke="#fbbf24" strokeWidth="1.6" strokeLinejoin="round" />
        <path d="M5.6 11 L12.4 11" stroke="#fbbf24" strokeWidth="1.2" opacity="0.5" />
      </svg>
      <span className="text-[13px] font-semibold tracking-tight text-neutral-100">
        Asymmetry<span className="text-amber-400"> Engine</span>
      </span>
    </Link>
  );
}
