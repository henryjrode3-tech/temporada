/**
 * A 0-100 score rendered as a labelled figure with a thin proportional bar.
 * `tone` decides whether high is good (default) or bad (risk, red flags).
 */
export function ScoreBadge({
  label,
  value,
  tone = "good",
  size = "md",
  suffix,
}: {
  label: string;
  value: number | null | undefined;
  tone?: "good" | "bad" | "neutral" | "accent";
  size?: "sm" | "md" | "lg";
  suffix?: string;
}) {
  const v = typeof value === "number" ? Math.max(0, Math.min(100, value)) : null;
  const bar =
    tone === "bad"
      ? v === null
        ? "bg-neutral-700"
        : v >= 70
          ? "bg-rose-500"
          : v >= 40
            ? "bg-orange-500"
            : "bg-neutral-500"
      : tone === "accent"
        ? "bg-amber-400"
        : tone === "neutral"
          ? "bg-neutral-400"
          : v === null
            ? "bg-neutral-700"
            : v >= 70
              ? "bg-emerald-400"
              : v >= 45
                ? "bg-cyan-400"
                : "bg-neutral-500";

  const text =
    size === "lg"
      ? "text-2xl"
      : size === "sm"
        ? "text-sm"
        : "text-lg";

  return (
    <div className="min-w-0">
      <div className="truncate text-[10px] uppercase tracking-wider text-neutral-500">
        {label}
      </div>
      <div className={`${text} font-semibold tabular-nums text-neutral-100`}>
        {v === null ? "—" : v.toFixed(v % 1 === 0 ? 0 : 1)}
        {suffix ? (
          <span className="ml-0.5 text-[11px] font-normal text-neutral-500">
            {suffix}
          </span>
        ) : null}
      </div>
      <div className="mt-1 h-1 w-full overflow-hidden rounded-full bg-neutral-800">
        <div
          className={`h-full rounded-full ${bar}`}
          style={{ width: `${v ?? 0}%` }}
        />
      </div>
    </div>
  );
}
