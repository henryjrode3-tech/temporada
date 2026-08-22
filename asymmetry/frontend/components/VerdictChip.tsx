import { VERDICT_LABEL } from "@/lib/format";
import type { Verdict } from "@/lib/types";

const STYLES: Record<Verdict, string> = {
  TOP_OPPORTUNITY: "bg-emerald-500/10 text-emerald-300 ring-emerald-500/30",
  INVESTIGATE: "bg-cyan-500/10 text-cyan-300 ring-cyan-500/30",
  WATCH: "bg-sky-500/10 text-sky-300 ring-sky-500/30",
  INTERESTING: "bg-violet-500/10 text-violet-300 ring-violet-500/30",
  HIGH_RISK: "bg-orange-500/10 text-orange-300 ring-orange-500/30",
  THESIS_WEAKENING: "bg-amber-500/10 text-amber-300 ring-amber-500/30",
  THESIS_INVALIDATED: "bg-rose-500/10 text-rose-300 ring-rose-500/30",
  REJECTED: "bg-neutral-700/30 text-neutral-400 ring-neutral-600/40",
};

export function VerdictChip({
  verdict,
  size = "md",
}: {
  verdict: Verdict;
  size?: "sm" | "md";
}) {
  const pad = size === "sm" ? "px-1.5 py-0.5 text-[10px]" : "px-2 py-0.5 text-[11px]";
  return (
    <span
      className={`inline-flex shrink-0 items-center rounded font-medium uppercase tracking-wider ring-1 ring-inset ${pad} ${STYLES[verdict]}`}
    >
      {VERDICT_LABEL[verdict]}
    </span>
  );
}

export const VERDICT_DOT: Record<Verdict, string> = {
  TOP_OPPORTUNITY: "bg-emerald-400",
  INVESTIGATE: "bg-cyan-400",
  WATCH: "bg-sky-400",
  INTERESTING: "bg-violet-400",
  HIGH_RISK: "bg-orange-400",
  THESIS_WEAKENING: "bg-amber-400",
  THESIS_INVALIDATED: "bg-rose-400",
  REJECTED: "bg-neutral-500",
};
