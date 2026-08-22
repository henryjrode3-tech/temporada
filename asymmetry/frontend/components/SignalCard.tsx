import Link from "next/link";
import { formatNumber, formatPct, relativeAge } from "@/lib/format";
import type { Signal, SignalStrength } from "@/lib/types";

export const STRENGTH_STYLE: Record<
  SignalStrength,
  { chip: string; rail: string }
> = {
  extreme: {
    chip: "bg-amber-500/15 text-amber-300 ring-amber-500/40",
    rail: "bg-amber-400",
  },
  strong: {
    chip: "bg-emerald-500/10 text-emerald-300 ring-emerald-500/30",
    rail: "bg-emerald-400",
  },
  moderate: {
    chip: "bg-cyan-500/10 text-cyan-300 ring-cyan-500/30",
    rail: "bg-cyan-400",
  },
  weak: {
    chip: "bg-neutral-700/40 text-neutral-400 ring-neutral-600/40",
    rail: "bg-neutral-600",
  },
};

function fmtValue(n: number): string {
  if (Math.abs(n) < 1 && n !== 0) return n.toFixed(2);
  if (Math.abs(n) >= 1000) return formatNumber(n);
  return formatNumber(n, Number.isInteger(n) ? 0 : 1);
}

export function SignalCard({
  signal,
  candidateName,
  candidateId,
  ticker,
  compact = false,
}: {
  signal: Signal;
  candidateName?: string | null;
  candidateId?: string | null;
  ticker?: string | null;
  compact?: boolean;
}) {
  const style = STRENGTH_STYLE[signal.strength];
  return (
    <div className="relative overflow-hidden rounded-md border border-neutral-800 bg-neutral-900/50 pl-3">
      <div className={`absolute left-0 top-0 h-full w-[3px] ${style.rail}`} />
      <div className="p-3">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <span
            className={`inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wider ring-1 ring-inset ${style.chip}`}
          >
            {signal.strength}
          </span>
          <span className="font-mono text-[11px] text-neutral-300">
            {signal.signal_type}
          </span>
          {!signal.is_significant ? (
            <span className="rounded bg-neutral-800 px-1.5 py-0.5 text-[10px] text-neutral-500">
              below significance
            </span>
          ) : null}
          <span className="ml-auto text-[11px] tabular-nums text-neutral-500">
            {relativeAge(signal.detected_at)}
          </span>
        </div>

        {candidateName ? (
          <div className="mt-1.5 text-[12px]">
            {candidateId ? (
              <Link
                href={`/opportunities/${candidateId}`}
                className="text-neutral-200 underline-offset-2 hover:text-amber-300 hover:underline"
              >
                {candidateName}
              </Link>
            ) : (
              <span className="text-neutral-200">{candidateName}</span>
            )}
            {ticker ? (
              <span className="ml-1.5 font-mono text-[11px] text-neutral-500">
                {ticker}
              </span>
            ) : null}
          </div>
        ) : null}

        {!compact ? (
          <p className="mt-1.5 text-[13px] leading-relaxed text-neutral-400">
            {signal.description}
          </p>
        ) : null}

        <div className="mt-2 flex flex-wrap items-baseline gap-x-4 gap-y-1 text-[11px] text-neutral-500">
          <span>
            <span className="text-neutral-600">now </span>
            <span className="tabular-nums text-neutral-300">
              {fmtValue(signal.current_value)}
            </span>
          </span>
          <span>
            <span className="text-neutral-600">baseline </span>
            <span className="tabular-nums text-neutral-400">
              {fmtValue(signal.baseline_value)}
            </span>
          </span>
          <span>
            <span className="text-neutral-600">Δ </span>
            <span
              className={`tabular-nums ${
                signal.pct_change >= 0 ? "text-emerald-400" : "text-rose-400"
              }`}
            >
              {formatPct(signal.pct_change, { signed: true })}
            </span>
          </span>
          <span>
            <span className="text-neutral-600">z </span>
            <span className="tabular-nums text-neutral-300">
              {signal.z_score.toFixed(2)}
            </span>
          </span>
          <span className="text-neutral-600">{signal.window_label}</span>
        </div>
      </div>
    </div>
  );
}
