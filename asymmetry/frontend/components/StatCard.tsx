import type { ReactNode } from "react";

export function StatCard({
  label,
  value,
  hint,
  accent = false,
}: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  accent?: boolean;
}) {
  return (
    <div className="rounded-md border border-neutral-800 bg-neutral-900/60 px-3 py-2.5">
      <div className="text-[10px] uppercase tracking-wider text-neutral-500">
        {label}
      </div>
      <div
        className={`mt-0.5 text-xl font-semibold tabular-nums ${
          accent ? "text-amber-300" : "text-neutral-100"
        }`}
      >
        {value}
      </div>
      {hint ? (
        <div className="mt-0.5 text-[11px] leading-snug text-neutral-500">
          {hint}
        </div>
      ) : null}
    </div>
  );
}
