import { formatPct } from "@/lib/format";
import { Estimate } from "./Estimate";

export function Pct({
  value,
  dp,
  signed = false,
  estimate = false,
  tone = "neutral",
  className = "",
}: {
  value: number | null | undefined;
  dp?: number;
  signed?: boolean;
  estimate?: boolean;
  /** "signed" colours positives green and negatives red. */
  tone?: "neutral" | "signed";
  className?: string;
}) {
  const toneClass =
    tone === "signed" && typeof value === "number"
      ? value > 0
        ? "text-emerald-400"
        : value < 0
          ? "text-rose-400"
          : "text-neutral-400"
      : "";
  const body = (
    <span className={`tabular-nums ${toneClass} ${className}`}>
      {formatPct(value, { dp, signed })}
    </span>
  );
  return estimate ? <Estimate>{body}</Estimate> : body;
}
