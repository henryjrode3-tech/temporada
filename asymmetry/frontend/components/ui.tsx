import type { ReactNode } from "react";
import type { DataSource } from "@/lib/api";

export function PageHeader({
  title,
  subtitle,
  right,
}: {
  title: string;
  subtitle?: ReactNode;
  right?: ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-3 border-b border-neutral-800 pb-3">
      <div className="min-w-0">
        <h1 className="text-lg font-semibold tracking-tight text-neutral-100">
          {title}
        </h1>
        {subtitle ? (
          <p className="mt-1 max-w-3xl text-[13px] leading-relaxed text-neutral-500">
            {subtitle}
          </p>
        ) : null}
      </div>
      {right ? <div className="shrink-0">{right}</div> : null}
    </div>
  );
}

export function Panel({
  title,
  right,
  children,
  className = "",
  id,
}: {
  title?: ReactNode;
  right?: ReactNode;
  children: ReactNode;
  className?: string;
  id?: string;
}) {
  return (
    <section
      id={id}
      className={`rounded-lg border border-neutral-800 bg-neutral-900/40 ${className}`}
    >
      {title ? (
        <header className="flex flex-wrap items-center justify-between gap-2 border-b border-neutral-800 px-4 py-2.5">
          <h2 className="text-[12px] font-semibold uppercase tracking-wider text-neutral-400">
            {title}
          </h2>
          {right}
        </header>
      ) : null}
      <div className="p-4">{children}</div>
    </section>
  );
}

/** Tables must scroll inside this, so the page body never scrolls sideways. */
export function ScrollTable({ children }: { children: ReactNode }) {
  return (
    <div className="-mx-4 overflow-x-auto px-4">
      <div className="min-w-max">{children}</div>
    </div>
  );
}

export function Th({
  children,
  className = "",
  align = "left",
}: {
  children: ReactNode;
  className?: string;
  align?: "left" | "right" | "center";
}) {
  const a =
    align === "right" ? "text-right" : align === "center" ? "text-center" : "text-left";
  return (
    <th
      scope="col"
      className={`whitespace-nowrap border-b border-neutral-800 px-3 py-2 text-[10px] font-medium uppercase tracking-wider text-neutral-500 ${a} ${className}`}
    >
      {children}
    </th>
  );
}

export function Td({
  children,
  className = "",
  align = "left",
}: {
  children: ReactNode;
  className?: string;
  align?: "left" | "right" | "center";
}) {
  const a =
    align === "right" ? "text-right" : align === "center" ? "text-center" : "text-left";
  return (
    <td
      className={`whitespace-nowrap border-b border-neutral-800/60 px-3 py-2 text-[12.5px] text-neutral-300 ${a} ${className}`}
    >
      {children}
    </td>
  );
}

export function Callout({
  tone = "note",
  title,
  children,
}: {
  tone?: "note" | "warn" | "danger" | "accent";
  title?: ReactNode;
  children: ReactNode;
}) {
  const styles = {
    note: "border-neutral-700/60 bg-neutral-800/30 text-neutral-400",
    warn: "border-amber-500/30 bg-amber-500/[0.06] text-amber-200/80",
    danger: "border-rose-500/30 bg-rose-500/[0.06] text-rose-200/80",
    accent: "border-cyan-500/30 bg-cyan-500/[0.06] text-cyan-200/80",
  }[tone];
  return (
    <div className={`rounded-md border px-3 py-2.5 text-[12px] leading-relaxed ${styles}`}>
      {title ? (
        <div className="mb-1 text-[11px] font-semibold uppercase tracking-wider">
          {title}
        </div>
      ) : null}
      {children}
    </div>
  );
}

export function SourceTag({
  source,
  error,
}: {
  source: DataSource;
  error?: string | null;
}) {
  const live = source === "live";
  return (
    <span
      title={
        live
          ? "Served by the research API"
          : `Research API unreachable (${error ?? "no response"}). Showing the bundled fixture dataset.`
      }
      className={`inline-flex items-center gap-1.5 rounded px-2 py-0.5 text-[10px] uppercase tracking-wider ring-1 ring-inset ${
        live
          ? "bg-emerald-500/10 text-emerald-300 ring-emerald-500/30"
          : "bg-neutral-800/60 text-neutral-400 ring-neutral-700"
      }`}
    >
      <span
        className={`h-1.5 w-1.5 rounded-full ${live ? "bg-emerald-400" : "bg-neutral-500"}`}
      />
      {live ? "live api" : "fixture data"}
    </span>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-md border border-dashed border-neutral-800 px-4 py-8 text-center text-[12px] text-neutral-600">
      {children}
    </div>
  );
}

export function RankDelta({ change }: { change: number | null }) {
  if (change === null || change === 0) {
    return <span className="text-[11px] tabular-nums text-neutral-600">—</span>;
  }
  const up = change > 0;
  return (
    <span
      title={up ? `Up ${change} places` : `Down ${Math.abs(change)} places`}
      className={`inline-flex items-center gap-0.5 text-[11px] tabular-nums ${
        up ? "text-emerald-400" : "text-rose-400"
      }`}
    >
      <svg width="8" height="8" viewBox="0 0 8 8" aria-hidden="true">
        <path
          d={up ? "M4 0 L8 8 L0 8 Z" : "M4 8 L0 0 L8 0 Z"}
          fill="currentColor"
        />
      </svg>
      {Math.abs(change)}
    </span>
  );
}
